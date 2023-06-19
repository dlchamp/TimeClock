import os


class Client:
    token: str = os.getenv("TOKEN")


class Database:
    sql_bind = os.getenv("SQL_BIND")


import disnake


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
