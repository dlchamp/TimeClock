import os
from datetime import datetime
from sys import version as sys_version
from typing import Sequence, overload

import disnake
from disnake import __version__ as disnake_version
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

from timeclock import __version__ as bot_version
from timeclock import log
from timeclock.constants import Database
from timeclock.database.guild import Guild
from timeclock.database.member import Member
from timeclock.database.role import Role
from timeclock.database.time import Time

__all__ = ("TimeClockBot",)

logger = log.get_logger(__name__)


class TimeClockBot(commands.InteractionBot):
    """Base bot instance"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.db_engine = engine = create_async_engine(Database.sql_bind)
        self.db_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

    @property
    def db(self) -> async_sessionmaker[AsyncSession]:
        return self.db_session

    async def on_ready(self) -> None:
        logger.info(
            "----------------------------------------------------------------------\n"
            f'Bot started at: {datetime.now().strftime("%m/%d/%Y - %H:%M:%S")}\n'
            f"System Version: {sys_version}\n"
            f"Disnake Version: {disnake_version}\n"
            f"Bot Version: {bot_version}\n"
            f"Connected to Discord as {self.user} ({self.user.id})\n"
            "----------------------------------------------------------------------\n"
        )

    def load_extensions(self) -> None:
        """Load all extensions available on 'cogs'"""

        for item in os.listdir("timeclock/cogs/"):
            if "__" in item:
                continue

            extension = f"timeclock.cogs.{item[:-3]}"
            self.load_extension(extension)
            logger.info(f"Extension loaded: {extension}")

    async def ensure_guild(
        self,
        guild_id: int,
        *,
        message_id: int | None = None,
        channel_id: int | None = None,
        embed: disnake.Embed | None = None,
        session: AsyncSession | None = None,
    ) -> Guild:
        session = session or self.db()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:

            results = await session.execute(select(Guild).where(Guild.id == guild_id))
            guild = results.scalar_one_or_none()

            if not guild:
                guild = Guild(
                    id=guild_id, message_id=message_id, channel_id=channel_id, embed=embed
                )
                session.add(guild)
            else:
                guild.message_id = message_id if message_id else guild.message_id
                guild.channel_id = channel_id if channel_id else guild.channel_id
                guild.embed = embed if embed else guild.embed

            await trans.commit()
            return guild

    async def get_guild_roles(
        self, guild_id: int, *, is_mod: bool | None = None, can_punch: bool | None = None
    ) -> Sequence[Role]:
        session = self.db()

        stmt = select(Role).where(Role.guild_id == guild_id)

        if is_mod is not None:
            stmt = stmt.where(Role.is_mod == is_mod)
        if can_punch is not None:
            stmt = stmt.where(Role.can_punch == can_punch)

        async with session.begin():
            result = await session.execute(stmt)
            return result.scalars().all()

    async def add_role(
        self,
        role_id: int,
        guild_id: int,
        *,
        can_punch: bool | None = None,
        is_mod: bool | None = None,
    ) -> Role:
        session = self.db()

        async with session.begin() as trans:
            await self.ensure_guild(guild_id, session=session)

            result = await session.execute(select(Role).where(Role.id == role_id))
            role = result.scalar_one_or_none()

            if not role:
                role = Role(id=role_id, guild_id=guild_id, can_punch=can_punch, is_mod=is_mod)
                session.add(role)

            else:
                role.can_punch = can_punch if can_punch is not None else role.can_punch
                role.is_mod = is_mod if is_mod is not None else role.is_mod

            await trans.commit()

            return role

    async def delete_role(self, role_id: int) -> None:
        session = self.db()

        async with session.begin() as trans:

            result = await session.execute(select(Role).where(Role.id == role_id))
            role = result.scalar_one_or_none()

            if not role:
                return

            await session.delete(role)
            await trans.commit()

    async def ensure_member(self, guild_id: int, member_id: int, session: AsyncSession) -> Member:
        result = await session.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()

        if not member:
            member = Member(id=member_id, guild_id=guild_id)
            session.add(member)
            await session.flush()
            await session.refresh(member)

        return member

    async def add_punch(self, guild_id: int, member_id: int, timestamp) -> Member:
        session = self.db()

        async with session.begin():
            member = await self.ensure_member(guild_id, member_id, session=session)
            times = member.times

            if not times or not member.on_duty:
                member.on_duty = True
                member.times.append(Time(punch_in=timestamp))
            else:
                member.on_duty = False
                member.times[-1].punch_out = timestamp

            await session.flush()
            await session.refresh(member)

        return member

    @overload
    async def get_members(self, guild_id: int, *, member_id: None = None) -> Sequence[Member]: ...

    @overload
    async def get_members(self, guild_id: int, *, member_id: int) -> Member | None: ...

    async def get_members(
        self, guild_id: int, *, member_id: int | None = None
    ) -> Sequence[Member] | Member | None:
        session = self.db()

        stmt = select(Member).where(Member.guild_id == guild_id)
        if member_id:
            stmt = stmt.where(Member.id == member_id)

        async with session.begin():
            result = await session.execute(stmt)

            if member_id:
                return result.scalar_one_or_none()

            return result.scalars().all()
