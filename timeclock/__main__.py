import asyncio
import os
import signal
import sys

import disnake
from loguru import logger

try:
    import dotenv
except ModuleNotFoundError:
    pass

else:
    if dotenv.find_dotenv():
        print("Found .env file, loading environment variables from it.")
        dotenv.load_dotenv(override=True)


from timeclock import db_model as model
from timeclock.bot import TimeClockBot
from timeclock.config import Config

_intents = disnake.Intents.none()
_intents.guilds = True
_intents.members = True


async def main() -> None:
    """Create and run the bot"""

    await check_database()

    bot: TimeClockBot = TimeClockBot(intents=_intents, reload=True, sync_commands_debug=False)

    try:
        bot.load_extensions()
    except Exception:
        await bot.close()
        raise

    logger.info("Bot is starting...")

    if os.name != "nt":

        loop = asyncio.get_event_loop()

        future = asyncio.ensure_future(bot.start(Config.token or ""), loop=loop)
        loop.add_signal_handler(signal.SIGINT, lambda: future.cancel())
        loop.add_signal_handler(signal.SIGTERM, lambda: future.cancel())

        try:
            await future
        except asyncio.CancelledError:

            logger.warning("Kill command was sent to the bot. Closing bot and event loop")
            if not bot.is_closed():
                await bot.close()
    else:
        await bot.start(Config.token or "")


async def check_database():
    """Creates the database file and tables if the file does not exist"""
    logger.info("Checking for database file at `timeclock/database/data.sqlite3`")
    file_path = "timeclock/database/"
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    if not os.path.exists(file_path + "data.sqlite3"):
        logger.info("Database not found.  Initializing a new database")
        await model.create_db()
        logger.info("Database initialized")
        return

    logger.info("Database initialized at `timeclock/database/data.sqlite3`")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
