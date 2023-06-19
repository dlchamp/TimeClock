import json
from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import subqueryload

from timeclock import log
from timeclock.database import Guild, Role

MISSING = object()

logger = log.get_logger(__name__)


class GuildCache:
    """Represents a cached guild"""

    def __init__(self, session: async_sessionmaker[AsyncSession]) -> None:
        self.session = session
        self._cache: dict[int, Guild] = {}

    def _add_guilds(self, guilds: List[Guild]) -> None:
        """Adds or updates multiple guild items in the cache"""
        self._cache.update({guild.id: guild for guild in guilds})

    def _add_guild(self, guild: Guild) -> None:
        """Add or update a guild in cache

        Parameters
        ----------
        guild: Guild
            A database guild model
        """
        self._cache[guild.id] = guild

    def _remove_guild(self, guild_id: int) -> None:
        """Removes a guild from cache

        Parameters
        ----------
        guild_id: int
            A database guild model's ID (same as disnake.Guild.id)
        """
        if guild_id in self._cache:
            self._cache.pop(guild_id)

    def _get_roles(
        self, guild_id: int, is_mod: bool = MISSING, can_punch: bool = MISSING
    ) -> List[Role]:
        """
        Return a list of roles from cache

        Parameters
        ----------
        guild_id: int
            ID the guild to get roles from
        is_mod: bool
            Whether or not the returned roles should be mods
        can_punch: bool
            Whether or not the returned roles should be able to punch
        """
        guild = self._cache.get(guild_id)
        if not guild:
            return []

        roles = guild.roles

        # If is_mod is not MISSING, filter by is_mod
        if is_mod is not MISSING:
            roles = [role for role in roles if role.is_mod == is_mod]

        # If can_punch is not MISSING, filter by can_punch
        if can_punch is not MISSING:
            roles = [role for role in roles if role.can_punch == can_punch]

        return roles

    def _get_guild(self, guild_id: int) -> Optional[Guild]:
        return self._cache.get(guild_id)

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        """Gets a cached guild if available. Fetches from DB if needed"""
        guild = self._get_guild(guild_id)

        if guild is None:
            logger.info(f"{guild_id} not found in cache. Fetching from DB then caching")
            session = self.session()
            async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
                result = await session.execute(
                    select(Guild).where(Guild.id == guild_id).options(subqueryload(Guild.roles))
                )
                guild = result.scalar_one_or_none()

                if guild is None:
                    return

                self._add_guild(guild)

        return self._get_guild(guild_id)

    async def add_guild(self, guild: Guild) -> None:
        """Adds a guild to the database and cache

        Parameters
        ----------
        guild: Guild
            A database guild model
        """
        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            session.add(guild)
            await trans.commit()

        self._add_guild(guild)
        logger.info(f"Guild `{guild.id}` has been cached")

    async def remove_guild(self, guild_id: int) -> None:
        """Remove a guild from the database and cache

        Parameters
        ----------
        guild: Guild
            A database guild model
        """
        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Guild).where(Guild.id == guild_id).options(subqueryload(Guild.roles))
            )
            guild = result.scalar_one_or_none()

            if guild is None:
                pass
            else:
                await session.delete(guild)

        self._remove_guild(guild)
        logger.info(f"Guild `{guild.id}` was removed")

    async def update_guild(
        self,
        guild_id: int,
        *,
        message_id: Any = MISSING,
        channel_id: Any = MISSING,
        embed: Optional[dict[str, Any]] = MISSING,
    ) -> None:
        """Updates an existing guild

        Parameters
        ----------
        guild_id: int
            ID for the db guild to update (same as disnake.Guild.id)
        message_id: Optional[int], default=MISSING
            ID for the timeclock message. If None, set the message_id to None.
            If MISSING, leave current value unchanged.
        channel_id: Optional[int], default=MISSING
            ID for the channel where timeclock message exists. If None, set the channel_id to None.
            If MISSING, leave current value unchanged.
        embed: Optional[dict[str, Any]]
            dict formatted Embed
        """

        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Guild).where(Guild.id == guild_id).options(subqueryload(Guild.roles))
            )
            guild = result.scalar_one_or_none()

            if not guild:
                session.add(
                    Guild(
                        id=guild_id,
                        message_id=None if message_id is MISSING else message_id,
                        channel_id=None if channel_id is MISSING else channel_id,
                        embed=None if embed is MISSING else embed,
                    )
                )
            else:
                if message_id is not MISSING:
                    guild.message_id = message_id
                if channel_id is not MISSING:
                    guild.channel_id = channel_id
                if embed is not MISSING:
                    guild.embed = json.dumps(embed)

            await session.flush()
            await session.refresh(guild)

        self._add_guild(guild)
        logger.info(f"Guild `{guild_id}` config was updated")

    async def add_role(
        self, guild_id: int, *, role_id: int, can_punch: bool = True, is_mod: bool = True
    ) -> None:
        """
        Adds a new role to the database and updates the cached guild.

        Parameters
        ----------
        guild_id : int
            The ID of the guild where the role is to be added.
        role_id : int
            The ID of the role to be added.
        can_punch : bool, optional
            Flag indicating whether the role can 'punch'. Defaults to True.
        is_mod : bool, optional
            Flag indicating whether the role is a moderator role. Defaults to True.
        """
        role = Role(id=role_id, guild_id=guild_id, is_mod=is_mod, can_punch=can_punch)

        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Guild).where(Guild.id == guild_id).options(subqueryload(Guild.roles))
            )
            guild = result.scalar_one_or_none()

            if not guild:
                guild = Guild(id=guild_id, roles=[role])
                session.add(guild)
                await session.flush()
            else:
                session.add(role)
            await session.flush()

            await session.refresh(guild)

        self._add_guild(guild)
        logger.info(f"Guild `{guild_id}` was updated in cache with a new role `{role_id}`")

    async def remove_role(self, guild_id: int, role_id: int) -> None:
        """Removes a role from the databse and updates the cached guild

        Parameters
        ----------
        guild_id: int
            ID for the guild that will be updated
        role_id: int
            ID for the Role to be removed
        """
        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Guild).where(Guild.id == guild_id).options(subqueryload(Guild.roles))
            )
            guild = result.scalar_one_or_none()

            if not guild:
                return

            role = next((role for role in guild.roles if role.id == role_id), None)
            if not role:
                raise ValueError(f"Could not find role by ID `{role_id}`")

            await session.delete(role)
            await session.flush()
            await session.refresh(guild)

            self._add_guild(guild)
            logger.info(f"Guild `{guild_id}` was updated in cache. Role `{role_id}` was removed")

    async def update_role(
        self,
        guild_id: int,
        role_id: int,
        *,
        is_mod: Optional[bool] = None,
        can_punch: Optional[bool] = None,
    ) -> None:
        """
        Updates a role and updates the cached guild

        Parameters
        ----------
        guild_id: int
            ID for the guild the role belongs to
        role_id: int
            ID for the role to be updated
        is_mod: Optional[bool]
            Whether or not the role is a mod role (Defaults to None)
        can_punch: Optional[bool]
            Whether or not the role is allowed to punch the timeclock (Defaults to None)
        """
        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Guild).where(Guild.id == guild_id).options(subqueryload(Guild.roles))
            )
            guild = result.scalar_one_or_none()

            if not guild:
                raise ValueError(
                    f"Unable to update role - Did not find associated guild by id `{guild_id}`"
                )

            role = next((role for role in guild.roles if role.id == role_id), None)
            if role is None:
                raise ValueError(f"Unable to update role - Did not find a role by id `{role_id}`")

            if is_mod is not None:
                role.is_mod = is_mod
            if can_punch is not None:
                role.can_punch = can_punch

            await session.flush()
            await session.refresh(guild)

        self._add_guild(guild)
        logger.info(f"Guild `{guild_id}` was updated in cache. Role {role_id}` was updated")

    async def get_roles(
        self, guild_id: int, *, is_mod: bool = MISSING, can_punch: bool = MISSING
    ) -> List[Role]:
        """
        Gets a list of roles for the guild. Tries cache, then db if cache not available.

        Parameters
        ----------
        guild_id : int
            ID for the guild whose roles to fetch.
        is_mod : bool, optional
            Whether or not to include only mod roles. If MISSING, will not filter on this attribute.
        can_punch : bool, optional
            Whether or not to include only roles that can 'punch'. If MISSING, will not filter on this attribute.
        """

        roles = self._get_roles(guild_id, is_mod, can_punch)

        if roles:
            logger.info(f"Using cached roles for guild `{guild_id}`")
            return roles

        logger.info(f"No cached roles in  `{guild_id}`. Caching roles from database")
        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Guild).where(Guild.id == guild_id).options(subqueryload(Guild.roles))
            )
            guild = result.scalar_one_or_none()

            if guild is None:
                logger.info(f"Guild `{guild_id}` has no roles configured yet.")
                return []

            self._add_guild(guild)

        return self._get_roles(guild_id, is_mod, can_punch)
