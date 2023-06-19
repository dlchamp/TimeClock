import os
from datetime import datetime
from sys import version as sys_version

from disnake import __version__ as disnake_version
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from timeclock import __version__ as bot_version
from timeclock import cache, log
from timeclock.constants import Database

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

        self.guild_cache: cache.GuildCache = cache.GuildCache(self.db_session)
        self.member_cache: cache.MemberCache = cache.MemberCache(self.db_session)

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
