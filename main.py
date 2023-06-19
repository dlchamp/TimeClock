import asyncio
import os
import signal
import sys

import disnake

from timeclock import database, log
from timeclock.bot import TimeClockBot
from timeclock.constants import Client

logger = log.get_logger(__name__)

_intents = disnake.Intents.default()
_intents.members = True


async def main() -> None:
    """Create and run the bot"""

    bot: TimeClockBot = TimeClockBot(intents=_intents)
    await check_database(bot)

    try:
        bot.load_extensions()
    except Exception:
        await bot.close()
        raise

    logger.info("Bot is starting...")

    if os.name != "nt":
        loop = asyncio.get_event_loop()

        future = asyncio.ensure_future(bot.start(Client.token or ""), loop=loop)
        loop.add_signal_handler(signal.SIGINT, lambda: future.cancel())
        loop.add_signal_handler(signal.SIGTERM, lambda: future.cancel())

        try:
            await future
        except asyncio.CancelledError:
            logger.warning("Kill command was sent to the bot. Closing bot and event loop")
            if not bot.is_closed():
                await bot.close()
    else:
        await bot.start(Client.token or "")


async def check_database(bot: TimeClockBot):
    """Creates the database file and tables if the file does not exist"""
    logger.info("Checking for database file at `timeclock/database/data.sqlite3`")

    if not os.path.exists("timeclock/database/data.sqlite3"):
        logger.info("Database not found.  Initializing a new database")
        await database.create_database(bot.db_engine)
        logger.info("Database initialized")
        return

    logger.info("Database previously initialized at `timeclock/database/data.sqlite3`")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
