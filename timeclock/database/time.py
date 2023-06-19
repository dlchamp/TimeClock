import datetime
from typing import TYPE_CHECKING, Optional, Tuple

import disnake
from sqlalchemy import BigInteger, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Time(Base):
    __tablename__ = "time"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("member.id"))
    punch_in: Mapped[float] = mapped_column(Float, nullable=False)
    punch_out: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)

    def _as_datetime(self) -> Tuple[datetime.datetime, datetime.datetime]:
        """Converts `self.punch_in` and `self.punch_out` to datetime objects.
        If `self.punch_out` is None, `datetime.datetime.now()` is used"""
        punch_in = datetime.datetime.fromtimestamp(self.punch_in)
        if self.punch_out is None:
            punch_out = datetime.datetime.now()
        else:
            punch_out = datetime.datetime.fromtimestamp(self.punch_out)

        return (punch_in, punch_out)

    def _get_diff(self) -> str:
        seconds = self.as_seconds()

        hours, rem = divmod(seconds, 3600)
        minutes, rem = divmod(rem, 60)
        seconds, rem = divmod(rem, 60)

        return f"{int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"

    def as_seconds(self) -> float:
        """
        Returns difference between punch_out and punch_in as seconds.
        If punch out is None (member is still punched in) uses `datetime.datetime.now()`
        instead
        """
        punch_in, punch_out = self._as_datetime()
        return (punch_out - punch_in).total_seconds()

    def as_string(self) -> str:
        if self.punch_out is None:
            _out = "-"
        else:
            _out = disnake.utils.format_dt(self.punch_out, "t")

        _in = disnake.utils.format_dt(self.punch_in, "t")

        diff = self._get_diff()

        return f"In: {_in} | Out: {_out} | Total: {diff}"
