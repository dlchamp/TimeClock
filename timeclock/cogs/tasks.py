import disnake
from disnake.ext import commands, tasks
from sqlalchemy.future import select
from sqlalchemy.orm import subqueryload

from timeclock import log
from timeclock.bot import TimeClockBot
from timeclock.database import Guild, Member

logger = log.get_logger(__name__)


class BackgroundTasks(commands.Cog):
    def __init__(self, bot: TimeClockBot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.fill_cache.start()

    def cog_unload(self) -> None:
        self.fill_cache.stop()

    @tasks.loop(count=1)
    async def fill_cache(self) -> None:
        """Task that runs once when bot starts up to
        populate `MemberCache` and `GuildCache`
        """

        await self.bot.wait_until_ready()

        session = self.bot.db()
        async with session.begin() as trans:
            result = await session.execute(select(Guild).options(subqueryload(Guild.roles)))
            guilds = result.scalars().all()

            result = await session.execute(select(Member).options(subqueryload(Member.times)))
            members = result.scalars().all()

            logger.info(f"Caching {len(members)} members and their times")
            self.bot.member_cache._add_members(members)
            logger.info(f"Caching {len(guilds)} guild configs")
            self.bot.guild_cache._add_guilds(guilds)


def setup(bot: TimeClockBot) -> None:
    bot.add_cog(BackgroundTasks(bot))
