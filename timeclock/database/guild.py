from __future__ import annotations

import json
from typing import List, Optional

import disnake
from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .role import Role


class Guild(Base):
    __tablename__ = "guild"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    embed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    roles: Mapped[List[Role]] = relationship("Role", lazy="joined")

    def get_embed(self) -> Optional[disnake.Embed]:
        if self.embed:
            return disnake.Embed.from_dict(json.loads(self.embed))
