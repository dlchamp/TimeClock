import disnake

from timeclock import query

__all__ = (
    "default_embed",
    "EditEmbedButtons",
)


def default_embed() -> disnake.Embed:
    """Create a default Embed for when the guild doesn't have one setup yet"""
    embed = disnake.Embed(
        title="Example Embed Title", description="Example embed description"
    )
    return embed


class EditEmbed(disnake.ui.Modal):
    """Modal for editing the embed body"""

    embed: disnake.Embed

    def __init__(self):

        components = [
            disnake.ui.TextInput(
                label="Title",
                placeholder="Edit the title of your embed",
                style=disnake.TextInputStyle.long,
                custom_id="title",
                max_length=250,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Body",
                placeholder="Edit the body of your embed",
                style=disnake.TextInputStyle.long,
                custom_id="body",
                max_length=3500,
                required=True,
            ),
        ]
        super().__init__(title="Edit Embed", components=components)

    async def callback(self, interaction: disnake.ModalInteraction) -> None:
        """Callback for this modal"""

        title = interaction.text_values.get("title")
        body = interaction.text_values.get("body")

        embed = self.embed
        embed.title = title
        embed.description = body

        await interaction.response.edit_message(embed=embed)


class EditEmbedButtons(disnake.ui.View):

    message: disnake.Message

    def __init__(self, message: int):
        super().__init__(timeout=None)
        self.message = message

    @disnake.ui.button(label="Edit", style=disnake.ButtonStyle.primary)
    async def edit_embed(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ) -> None:
        """Callback for edit embed button"""

        modal = EditEmbed()
        modal.embed = interaction.message.embeds[0]

        return await interaction.response.send_modal(modal=modal)

    @disnake.ui.button(label="Save", style=disnake.ButtonStyle.success)
    async def save_embed(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ) -> None:
        """Callback for save embed button"""

        embed = interaction.message.embeds[0]

        await interaction.response.edit_message(
            "Your customization has been saved. You may close this message.",
            view=self.clear_items(),
        )
        self.stop()

        if self.message:
            try:
                await self.message.edit(content=None, embed=embed)
            except disnake.NotFound:
                pass
            else:
                return await query.update_guild_config(
                    interaction.guild.id, embed=embed
                )

        message = await interaction.channel.send(
            embed=embed,
            components=[
                disnake.ui.Button(
                    label="Punch In/Out",
                    style=disnake.ButtonStyle.primary,
                    custom_id="punch",
                )
            ],
        )

        # save the new embed if it was deleted or new guild config
        await query.update_guild_config(
            interaction.guild.id,
            embed=embed,
            message_id=message.id,
            channel_id=message.channel.id,
        )

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.danger)
    async def cancel_embed(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ) -> None:
        """Callback for cancel emebd button"""

        await interaction.response.edit_message(
            "Customization has been cancelled.",
            embed=None,
            attachments=[],
            view=self.clear_items(),
        )
        self.stop()
