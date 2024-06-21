import datetime

import disnake
from sqlalchemy import BigInteger, Boolean, Column
from sqlalchemy.orm import Mapped, relationship

from .base import Base
from .time import Time


class Member(Base):
    """
    Member Class representing each guild member.

    Attributes
    ----------
    id : Mapped[int]
        ID of the guild member.
    guild_id : Mapped[int]
        ID of the guild the member belongs to.
    on_duty : Mapped[bool]
        Whether the member is on duty.
    times : Mapped[List['Time']]
        List of Time objects associated with the member.
    """

    __tablename__ = "member"

    id: Mapped[int] = Column(BigInteger, primary_key=True)
    guild_id: Mapped[int] = Column(BigInteger, nullable=False)
    on_duty: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    times: Mapped[list[Time]] = relationship("Time", lazy="subquery")

    @property
    def status(self) -> str:
        """Return member's duty status.

        Returns
        -------
        str
            String indicating member's duty status.
        """
        return "🟢 - On Duty" if self.on_duty else "🔴 - Off Duty"

    def limit_history(self, limit: int = 7) -> list[Time]:
        """Return a list of Time instances from the last {limit} days.

        Parameters
        ----------
        limit : int, optional
            Number of days to consider, by default 7.

        Returns
        -------
        List['Time']
            List of Time instances.
        """
        limit_date = datetime.datetime.now() - datetime.timedelta(days=limit)
        return [
            time
            for time in self.times
            if datetime.datetime.fromtimestamp(time.punch_in) >= limit_date
        ]

    def as_string(self, guild: disnake.Guild) -> str:
        """Return a string representation of the member and their on-duty status.

        Parameters
        ----------
        guild : disnake.Guild
            Guild to which the member belongs.

        Returns
        -------
        str
            String representation of member status.
        """
        status = "🟢" if self.on_duty else "🔴"
        return f"{status} {guild.get_member(self.id).display_name} - {self.calculate_total_time()}"

    def calculate_total_time(self, limit: int = 7) -> str:
        """Calculate and return a string of the total clocked in time over the past {limit} days.

        Parameters
        ----------
        limit : int, optional
            Number of days to consider for time calculation, by default 7.

        Returns
        -------
        str
            Formatted string indicating total clocked in time.
        """
        total_seconds = sum(
            time.as_seconds() for time in self.limit_history(limit) if time.punch_in is not None
        )

        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, rem = divmod(rem, 60)
        seconds, rem = divmod(rem, 60)

        return (
            f"{int(days)} days, {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"
        )

    def create_timesheet_embed(self, name: str, history: int = 7) -> disnake.Embed:
        """Create and return a disnake.Embed instance for the member's times.

        Parameters
        ----------
        name : str
            Name of the member.
        history : int, optional
            Number of days to consider for timesheet, by default 7.

        Returns
        -------
        disnake.Embed
            Embed containing the member's times.
        """
        total = self.calculate_total_time(history)
        timesheet = "\n".join(time.as_string() for time in self.limit_history(history))

        embed = disnake.Embed(
            title=f"Timesheet for {name}",
            description=f"Total On Duty time for last {history} days\n{total}\n\n{timesheet}",
        )
        embed.set_footer(text=self.status)

        return embed
