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
    _embed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    roles: Mapped[List[Role]] = relationship("Role", lazy="joined")

    @property
    def embed(self) -> disnake.Embed | None:
        if self._embed is None:
            return

        embed_dict = json.loads(self._embed)
        return disnake.Embed.from_dict(embed_dict)

    @embed.setter
    def embed(self, embed: disnake.Embed) -> None:
        embed_dict = embed.to_dict()
        self._embed = json.dumps(embed_dict)
