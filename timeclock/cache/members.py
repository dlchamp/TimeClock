from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import subqueryload

from timeclock.database import Member, Time


class MemberCache:
    """Represents a cached member."""

    def __init__(self, session: async_sessionmaker[AsyncSession]) -> None:
        self.session = session
        self._cache: dict[int, Member] = {}

    def _add_member(self, member: Member) -> None:
        """Add or update a member in cache."""
        self._cache[member.id] = member

    def _remove_member(self, member_id: int) -> None:
        """Removes a member from cache."""
        if member_id in self._cache:
            self._cache.pop(member_id)

    def _get_member(self, member_id: int) -> Optional[Member]:
        """Get a Member from the cache"""
        return self._cache.get(member_id)

    def _get_members(self, guild_id: int) -> List[Member]:
        """Gets all members for a guild from cache

        Parameters
        ----------
        guild_id: int
            ID for which will return all members where member.guild_id matches
        """

        members = self._cache.values()
        if guild_id is None:
            return members

        return [m for m in members if m.guild_id == guild_id]

    def _add_members(self, members: List[Member]) -> None:
        """Adds multiple members to cache"""
        self._cache.update({member.id: member for member in members})

    async def add_member(self, member: Member) -> None:
        """Adds a member to the database and cache."""
        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            session.add(member)
            await trans.commit()

        self._add_member(member)

    async def remove_member(self, member: Member) -> None:
        """Remove a member from the database and cache."""
        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            await session.delete(member)
            await trans.commit()

        self._remove_member(member.id)

    async def update_member(
        self,
        member_id: int,
        *,
        on_duty: Optional[bool] = None,
    ) -> None:
        """Updates an existing member."""

        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Member).where(Member.id == member_id).options(subqueryload(Member.times))
            )
            member = result.scalar_one_or_none()

            if not member:
                raise ValueError(
                    f"Unable to update member - Member not found with ID `{member_id}`"
                )

            member.on_duty = member.on_duty if on_duty is None else on_duty
            await trans.commit()

        self._add_member(member)

    async def add_punch_event(self, guild_id: id, member_id: int, timestamp: float) -> Member:
        """Adds a new time to the database and updates the cached member."""

        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Member).where(Member.id == member_id).options(subqueryload(Member.times))
            )
            member = result.scalar_one_or_none()

            if not member:
                _member = Member(
                    id=member_id,
                    guild_id=guild_id,
                    on_duty=True,
                    times=[Time(punch_in=timestamp)],
                )

                session.add(_member)

            else:
                if not member.on_duty:
                    session.add(Time(member_id=member_id, punch_in=timestamp))
                    member.on_duty = True

                else:
                    time = member.times[-1]
                    time.punch_out = timestamp
                    member.on_duty = False

            await session.flush()
            await session.refresh(member or _member)

        self._add_member(member or _member)
        return member or _member

    async def remove_time(self, member_id: int, time_id: int) -> None:
        """Removes a time from the database and updates the cached member."""
        session = self.session()
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Member).where(Member.id == member_id).options(subqueryload(Member.times))
            )
            member = result.scalar_one_or_none()

            if not member:
                return

            time = next((time for time in member.times if time.id == time_id), None)
            if time:
                await session.delete(time)
                await session.flush()
                await session.refresh

    async def get_member(self, member_id: int) -> Optional[Member]:
        """Tries to get member from cache, queries database if not found in cache

        Parameters
        ----------
        member_id: int
            ID for the member to get
        """
        member = self._get_member(member_id)

        if member is None:
            session = self.session()
            async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
                result = await session.execute(
                    select(Member).where(Member.id == member_id).options(subqueryload(Member.times))
                )
                member = result.scalar_one_or_none()

                if member is None:
                    return

                self._add_member(member)

        return self._get_member(member_id)

    async def get_members(self, guild_id: Optional[int] = None) -> List[Member]:
        """
        Gets all of the members associated with a guild. If guild_id is None,
        gets all members.

        Parameters
        ----------
        guild_id : Optional[int]
            ID for the guild to fetch members for. If None, fetches all members.
        """

        members = self._get_members(guild_id)
        query = select(Member).options(subqueryload(Member.times))

        if guild_id is not None:
            query = query.where(Member.guild_id == guild_id)

        if not members:
            session = self.session()
            async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
                result = await session.execute(query)
                members = result.scalars().all()

                if not members:
                    return []

                self._add_members(members)

        return self._get_members(guild_id)
