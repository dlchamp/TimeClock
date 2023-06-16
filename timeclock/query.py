import datetime
import json
from typing import List, Optional

import disnake
from sqlalchemy import delete
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from timeclock import db_model as model
from timeclock.db_model import async_session

__all__ = (
    "add_guild",
    "update_guild_config",
    "fetch_guild_config",
    "fetch_all_member_times",
    "fetch_member_times",
    "add_member_punch_event",
    "fetch_guild_roles",
    "add_role",
    "remove_role",
    "remove_config_message",
)


async def add_guild(guild_id: int) -> None:
    """Adds a new guild to the database

    Parameters
    ----------
    guild_id: :type:`int`
        Guild's Discord ID (row ID)
    """
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(model.Guild).where(model.Guild.id == guild_id))
            guild: model.Guild = result.scalars().first()

            if guild:
                return

            session.add(model.Guild(id=guild_id))

            await session.commit()


async def update_guild_config(
    guild_id: int,
    embed: disnake.Embed,
    message_id: Optional[int] = None,
    channel_id: Optional[int] = None,
) -> None:
    """Updates the guild's embed and associated message ID

    Parameters
    ----------
    guild_id: :type:`int`
        Guild's Discord ID (row ID)
    embed: :type:`disnake.Embed`
        Updated embed
    message_id: :type:`int`
        Message ID for the embed message
    channel_id: :type:`int`
        Channel ID where the message is
    """

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(model.Guild).where(model.Guild.id == guild_id))
            guild: model.Guild = result.scalars().first()

            if guild is None:
                session.add(
                    model.Guild(
                        id=guild_id,
                        message_id=message_id,
                        channel_id=channel_id,
                        embed=json.dumps(embed.to_dict()),
                    )
                )

            else:
                if message_id:
                    guild.message_id = message_id
                if channel_id:
                    guild.channel_id = channel_id

                guild.embed = json.dumps(embed.to_dict())

            await session.commit()


async def fetch_guild_config(guild_id: int) -> model.Guild:
    """
    Fetches the guild's current config from the database

    Parameters
    ----------
    guild_id: :type:`int`
        Guild's Discord ID (row ID)
    """
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(model.Guild).where(model.Guild.id == guild_id))
            return result.scalars().first()


async def fetch_all_member_times(
    guild_id: int, history_days: Optional[int] = 7
) -> List[model.Member]:
    """
    Fetches all times for member in this guild up to the historical days passed. Defaults to 7 days,
    max is 30 days

    Parameters
    ----------
    guild_id: :type:`int`
        Guild's Discord ID (row ID)
    historical_days: :type:`int`
        The number of historical days to fetch, defaults to 7, max 30
    """

    if history_days > 31:
        history_days = 31

    start_date_timestamp = datetime.datetime.timestamp(
        disnake.utils.utcnow() - datetime.timedelta(days=history_days)
    )

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(model.Member)
                .where(model.Member.guild_id == guild_id)
                .options(selectinload(model.Member.times))
            )
            members = result.scalars().all()

            if members != []:
                for member in members:
                    time = [time for time in member.times if time.punch_in >= start_date_timestamp]
                    member.times = time

                return members


async def fetch_member_times(
    guild_id: int, member_id: int, history_days: Optional[int] = 7
) -> model.Member:
    """Fetch a member and their times up to {history_days} data

    Parameters
    ----------
    guild_id: :type:`int`
        Guild's Discord ID (row ID)
    member_id: :type:`int`
        Member's Discord ID
    historical_days: :type:`int`
        The number of historical days to fetch, defaults to 7, max 30
    """
    if history_days > 31:
        history_days = 31

    start_date_timestamp = datetime.datetime.timestamp(
        disnake.utils.utcnow() - datetime.timedelta(days=history_days)
    )

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(model.Member)
                .where(model.Member.guild_id == guild_id)
                .where(model.Member.id == member_id)
                .options(selectinload(model.Member.times))
            )
            member = result.scalars().first()

            if member is None:
                return

            member.times = [time for time in member.times if time.punch_in >= start_date_timestamp]
            member.times.sort(key=lambda t: t.punch_in, reverse=False)
            return member


async def add_member_punch_event(guild_id: int, member_id: int, timestamp: float) -> model.Member:
    """Add a new punch event for the member.  Will punch out if in, or in if out,
    returns the updated member object

    Parameters
    ----------
    guild_id: :type:`int`
        Guild's Discord ID (row ID)
    member_id: :type:`int`
        Member's Discord ID
    timestamp: :type:`float`
        The utc unix timestamp of the punch event
    """

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(model.Member)
                .where(model.Member.id == member_id)
                .where(model.Member.guild_id == guild_id)
                .options(selectinload(model.Member.times))
            )

            member: model.Member = result.scalars().first()

            if member is None:
                member = model.Member(
                    id=member_id,
                    guild_id=guild_id,
                    on_duty=True,
                    times=[model.Time(punch_in=timestamp)],
                )
                session.add(member)

            else:
                on_duty = member.on_duty

                # member is not on duty, last event was a punch out
                # so we just add a new punch time
                if not on_duty:
                    session.add(model.Time(member_id=member_id, punch_in=timestamp))
                    member.on_duty = True

                # member is on duty, so this event would be a punch out event
                # get the most recent time event and update the punch_out time
                else:
                    time = member.times[-1]
                    time.punch_out = timestamp
                    member.on_duty = False

            await session.commit()

        return member


async def fetch_guild_roles(
    guild_id: int, *, is_mod: Optional[bool] = False, can_punch: Optional[bool] = False
) -> List[model.Role]:
    """Fetch roles from the guild and return database role items

    Parameters
    ----------
    guild_id: :type:`int`
        Guild's Discord ID (row ID)
    """
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(model.Role).where(model.Role.guild_id == guild_id)
            )
            roles = [role for role in result.scalars()]

            if can_punch:
                return [role for role in roles if role.can_punch == True]

            if is_mod:
                return [role for role in roles if role.is_mod == True]

            return roles


async def add_role(
    guild_id: int,
    role_id: int,
    is_mod: Optional[bool] = False,
    can_punch: Optional[bool] = False,
) -> None:
    """
    Adds a new role to the guild's roles

    Parameters
    -----------
    guild_id: :type:`int`
        Guild's Discord ID (row ID)
    role_id: :type:`int`
        Role's Discord ID
    is_mod: :type:`bool`
        Role is a mod
    can_punch: :type:`bool`
        Role can punch
    """

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(model.Role)
                .where(model.Role.guild_id == guild_id)
                .where(model.Role.id == role_id)
            )

            role: model.Role = result.scalars().first()
            if role:
                role.is_mod = is_mod
                role.can_punch = can_punch

            else:
                session.add(
                    model.Role(
                        id=role_id,
                        guild_id=guild_id,
                        is_mod=is_mod,
                        can_punch=can_punch,
                    )
                )

            await session.commit()


async def remove_role(role_id: int) -> None:
    """Remove the row where row ID is role_id

    Parameters
    ----------
    role_id: :type:`int`
        The role ID to be removed
    """
    async with async_session() as session:
        async with session.begin():
            await session.execute(delete(model.Role).where(model.Role.id == role_id))

            await session.commit()


async def remove_config_message(guild_id: int, message_id: int) -> None:
    """Removes the punch configured message from the database"""

    async with async_session() as session:
        result = await session.execute(select(model.Guild).where(model.Guild.guild_id == guild_id))
        guild = result.scalar_one_or_none()

        if not guild:
            return

        guild.channel_id = None
        guild.embed = None
        guild.message_id = None

        await session.commit()
