import disnake

__all__ = ("EditEmbed",)


class EditEmbed(disnake.ui.Modal):
    """Modal for editing the embed body"""

    def __init__(self, embed: disnake.Embed):
        components = [
            disnake.ui.TextInput(
                label="Title",
                value=embed.title,
                style=disnake.TextInputStyle.long,
                custom_id="title",
                max_length=250,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Body",
                value=embed.description,
                style=disnake.TextInputStyle.long,
                custom_id="body",
                max_length=3500,
                required=True,
            ),
        ]
        super().__init__(title="Edit Embed", components=components)

        self.embed = embed

    async def callback(self, interaction: disnake.ModalInteraction) -> None:
        """Callback for this modal"""

        title = interaction.text_values.get("title")
        body = interaction.text_values.get("body")

        embed = self.embed
        embed.title = title
        embed.description = body

        await interaction.response.edit_message(embed=embed)
