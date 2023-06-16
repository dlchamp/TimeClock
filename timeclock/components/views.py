import disnake

from timeclock import query

from .buttons import TrashButton
from .modal import EditEmbed

__all__ = (
    "Pagination",
    "EditEmbedButtons",
)


class Pagination(disnake.ui.View):
    def __init__(self, embeds: list[disnake.Embed], author: disnake.Member | disnake.User) -> None:
        super().__init__(timeout=None)
        self.author = author
        self.embeds = embeds
        self.index = 0
        self.add_item(TrashButton(author.id))

        self._update_state()

    def _update_state(self) -> None:
        self.first_page.disabled = self.prev_page.disabled = self.index == 0
        self.last_page.disabled = self.next_page.disabled = self.index == len(self.embeds) - 1
        self.page_num.label = f"[{self.index+1}/{len(self.embeds)}]"
        self.page_num.disabled = True

    async def inter_check(self, inter: disnake.MessageInteraction) -> bool:
        if "trash" in inter.component.custom_id:
            return False

        if self.author.id == inter.author.id:
            return True

        await inter.response.send_message(
            "Sorry. This is not your message to control", ephemeral=True
        )
        return False

    @disnake.ui.button(label="First Page", style=disnake.ButtonStyle.primary)
    async def first_page(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ) -> None:
        self.index = 0
        self._update_state()

        await inter.response.edit_message(embed=self.embeds[self.index], view=self)

    @disnake.ui.button(label="Previous", style=disnake.ButtonStyle.secondary)
    async def prev_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        self.index -= 1
        self._update_state()

        await inter.response.edit_message(embed=self.embeds[self.index], view=self)

    @disnake.ui.button(label="1", style=disnake.ButtonStyle.secondary, disabled=True)
    async def page_num(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        """Just a button that acts as a display to show current page/total pages. Not clickable"""

    @disnake.ui.button(label="Next", style=disnake.ButtonStyle.secondary)
    async def next_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.index += 1
        self._update_state()

        await inter.response.edit_message(embed=self.embeds[self.index], view=self)

    @disnake.ui.button(label="Last Page", style=disnake.ButtonStyle.primary)
    async def last_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.index = len(self.embeds) - 1
        self._update_state()

        await inter.response.edit_message(embed=self.embeds[self.index], view=self)


class EditEmbedButtons(disnake.ui.View):
    message: disnake.Message

    def __init__(self, message: int, embed: disnake.Embed, inter: disnake.GuildCommandInteraction):
        super().__init__(timeout=None)
        self.message = message
        self.embed = embed
        self.inter = inter

    async def send_embed_and_update_config(self, inter, embed):
        message = await inter.channel.send(
            embed=embed,
            components=[
                disnake.ui.Button(
                    label="Punch In/Out",
                    style=disnake.ButtonStyle.primary,
                    custom_id="punch",
                )
            ],
        )
        await query.update_guild_config(
            inter.guild.id,
            embed=embed,
            message_id=message.id,
            channel_id=message.channel.id,
        )
        return message

    @disnake.ui.button(label="Edit", style=disnake.ButtonStyle.primary)
    async def edit_embed(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ) -> None:
        """Callback for edit embed button"""

        modal = EditEmbed(self.embed)

        return await inter.response.send_modal(modal=modal)

    @disnake.ui.button(label="Save", style=disnake.ButtonStyle.success)
    async def save_embed(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ) -> None:
        """Callback for save embed button"""

        await inter.response.defer(with_message=True, ephemeral=True)

        embed = self.embed

        if self.message:
            try:
                message = await self.message.edit(content=None, embed=embed)
            except disnake.NotFound:
                message = await self.send_embed_and_update_config(inter, embed)
        else:
            message = await self.send_embed_and_update_config(inter, embed)

        await inter.edit_original_response(
            f"Your customization has been saved. You may close this message.\n[Click here]({message.jump_url}) to view!",
            view=self.clear_items(),
        )
        await self.inter.delete_original_response()

        self.stop()

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.danger)
    async def cancel_embed(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ) -> None:
        """Callback for cancel emebd button"""

        await inter.response.edit_message(
            "Customization has been cancelled.",
            embed=None,
            attachments=[],
            view=self.clear_items(),
        )
        self.stop()
