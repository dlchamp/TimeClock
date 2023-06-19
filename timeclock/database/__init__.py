from sqlalchemy.ext.asyncio import AsyncEngine

from .base import Base
from .guild import Guild
from .member import Member
from .role import Role
from .time import Time

__all__ = (
    "Base",
    "Guild",
    "Member",
    "Role",
    "Time",
)


async def create_database(engine: AsyncEngine, base: Base = Base) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.drop_all)
        await conn.run_sync(base.metadata.create_all)
    await engine.dispose()
