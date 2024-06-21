from typing import Self

import disnake
from sqlalchemy import BigInteger, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guild.id"))
    is_mod: Mapped[bool] = mapped_column(Boolean, nullable=False)
    can_punch: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def __eq__(self, other: Self | disnake.Role) -> bool:
        return other.id == self.id
