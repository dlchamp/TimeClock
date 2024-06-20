import os

import disnake

from timeclock import log

logger = log.get_logger(__name__)


try:
    import dotenv
except ModuleNotFoundError:
    pass

else:
    dotenv.load_dotenv(override=True)
    logger.info(f"Environment variables loaded from .env file")


class Client:
    token: str = os.getenv("TOKEN")


class Database:
    sql_bind = "sqlite+aiosqlite:///timeclock/database/data.sqlite3"


def default_embed():
    """Create and return a default embed"""
    embed = disnake.Embed(
        title="This is your embed title.",
        description=(
            "This is the embed body. Both the title and body can be edited "
            "via modal by clicking the edit button below"
        ),
    )

    return embed
