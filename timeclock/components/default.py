import disnake

__all__ = ("default_embed",)


def default_embed() -> disnake.Embed:
    """Create a default Embed for when the guild doesn't have one setup yet"""
    embed = disnake.Embed(title="Example Embed Title", description="Example embed description")
    return embed
