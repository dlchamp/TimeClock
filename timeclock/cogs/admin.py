import json
from typing import List, Optional

import disnake
from disnake.ext import commands
from thefuzz import process

from timeclock import components, constants, log
from timeclock.bot import TimeClockBot

logger = log.get_logger(__name__)


class Admin(commands.Cog):
    """Add admin commands to the bot"""

    def __init__(self, bot: TimeClockBot) -> None:
        self.bot = bot

    def check_channel_permissions(self, inter: disnake.GuildCommandInteraction) -> bool:
        """Check that the bot is able to view the channel, send messages, and read history
        so that it will be able to edit it's own message when user wishes to update embed"""
        req_perms = disnake.Permissions(
            send_messages=True, view_channel=True, read_message_history=True
        )
        return inter.app_permissions >= req_perms

    async def cog_slash_command_check(self, inter: disnake.GuildCommandInteraction) -> bool:
        """Performs a check for every command within this cog.  If returns True,
        command is invoked, else command.CheckFailed is raise"""
        roles = inter.author.roles
        mod_roles = await self.bot.get_guild_roles(inter.guild.id, is_mod=True)

        return (
            any(role in mod_roles for role in roles) or inter.author.guild_permissions.administrator
        )

    async def cog_slash_command_error(
        self, inter: disnake.GuildCommandInteraction, error: Exception
    ) -> None:
        """Called if any exception is raised for any command within this cog"""

        if isinstance(error, commands.CheckFailure):
            return await inter.response.send_message(
                f"It seems you do not have permission to use this command",
                ephemeral=True,
            )

        raise error

    @commands.slash_command(name="config")
    @commands.default_member_permissions(administrator=True)
    async def config(self, inter: disnake.GuildCommandInteraction):
        pass

    @config.sub_command(name="edit-embed")
    async def config_edit_embed(
        self,
        inter: disnake.GuildCommandInteraction,
        image: Optional[disnake.Attachment] = None,
        thumbnail: Optional[disnake.Attachment] = None,
        clear_images: Optional[bool] = False,
    ) -> None:
        """
        Create or edit the embed attached to the Punch button. Title and body editable via Modal

        Parameters
        ----------
        image: :type:`Optional[disnake.Attachment]`
            An image to be used as the large image within the embed
        thumbnail: :type:`Optional[disnake.Attachment]`
            An image to be used as the smaller image within the embed
        clear_images: Optional[bool]
            Set to True to remove all images from the Embed. Any included images will still be added
        """

        # make sure I can send messages within this channel
        if not self.check_channel_permissions(inter):
            logger.warning(
                f"Bot missing channel permissions in {inter.channel.name} ({inter.guild.name})"
            )
            return await inter.response.send_message(
                "Please make sure you have enabled the following permissions in this channel before using this command.\n"
                "`Send Messages`, `View Channel`, `Read Channel History`",
                ephemeral=True,
            )

        guild = await self.bot.ensure_guild(inter.guild.id)
        embed = guild.embed if guild and guild.embed else constants.default_embed()

        if guild and guild.channel_id:
            channel = inter.guild.get_channel(guild.channel_id)
            message = channel.get_partial_message(guild.message_id)
        else:
            channel = message = None

        if clear_images:
            embed.set_image(url=None)
            embed.set_thumbnail(url=None)

        if image:
            embed.set_image(url=image.proxy_url)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail.proxy_url)

        view = components.EditEmbedButtons(self.bot, message, embed, inter)
        await inter.response.send_message(
            "Here is your currently configured embed. Use the buttons to below to edit, save, or cancel these changes\n"
            "If you wish to add an image or thumbnail, please [Cancel] and attach them with the optional command arguments.\n\n"
            "If this is the first time running this command, or the previous message was deleted, make sure you're using this command within the channel where you wish to post the 'Punch' embed.",
            embed=embed,
            ephemeral=True,
            view=view,
        )

    @config.sub_command(name="view-roles")
    async def config_view_roles(self, inter: disnake.GuildCommandInteraction) -> None:
        """View roles and permissions you have configured to use with the bot"""
        await inter.response.defer()

        roles = await self.bot.get_guild_roles(inter.guild.id)
        if roles:
            description = "\n".join(
                f"{inter.guild.get_role(role.id).mention} | Is Mod: {role.is_mod} | Can Punch: {role.can_punch}"
                for role in roles
            )
        else:
            description = "No roles have been configured yet."

        embed = disnake.Embed(title="Configured Roles", description=description)
        await inter.edit_original_response(
            embed=embed, components=components.TrashButton(inter.author.id)
        )

    @config.sub_command(name="add-role")
    async def config_add_mod_role(
        self,
        inter: disnake.GuildCommandInteraction,
        role: disnake.Role,
        is_mod: Optional[bool] = False,
        can_punch: Optional[bool] = True,
    ) -> None:
        """
        Add or update permissions for a role. Mod roles can view other member timesheets

        Parameters
        ----------
        role: :type:`disnake.Role`
            Role you wish to add/update in the guild's role config
        is_mod: :type:`bool`
            Set this to True to make this new role a mod role
        can_punch: :type:`bool`
            If you wish to add a mod role that cannot punch, set this to False
        """
        if not inter.channel.permissions_for(inter.author).manage_roles:
            return await inter.response.send_message(
                "only server admins can add, update, or remove mod roles", ephemeral=True
            )

        db_role = await self.bot.add_role(
            role.id, inter.guild.id, can_punch=can_punch, is_mod=is_mod
        )
        await inter.response.send_message(
            f"{role.mention} has been configured with the following permissions:\n"
            f"Mod: **{db_role.is_mod}**\nCan Punch: **{db_role.can_punch}**",
            ephemeral=True,
        )

    @config.sub_command("remove-role")
    async def config_remove_role(self, inter: disnake.GuildCommandInteraction, role: str):
        """
        Remove a role from the config. This role will be removed from the database

        Parameters
        ----------
        role: :type:`str`
            The name of the role you wish to remove
        """

        if not inter.channel.permissions_for(inter.author).manage_roles:
            return await inter.response.send_message(
                "only server admins can add, update, or remove mod roles", ephemeral=True
            )

        if role == "No roles have been configured":
            return await inter.response.send_message(
                "No roles have been configured for this guild", ephemeral=True
            )

        try:
            role = int(role)
        except ValueError:
            return await inter.response.send_message(f"`{role}` is not valid", ephemeral=True)

        try:
            await self.bot.delete_role(role)
        except ValueError as e:
            await inter.response.send_message(e, ephemeral=True)
            return

        await inter.response.send_message(f"Role has been removed!", ephemeral=True)

    @config_remove_role.autocomplete("role")
    async def remove_role_autocomplete(
        self, inter: disnake.GuildCommandInteraction, string: str
    ) -> List[str]:
        """
        Provides options to the user for selecting a role to remove from the database

        Parameters
        ----------
        string: :type:`str`
            The argument string as provided from discord via user input
        """
        roles = await self.bot.get_guild_roles(inter.guild.id)
        if not roles:
            return ["No roles have been configured"]

        roles = [inter.guild.get_role(r.id) for r in roles]

        response = process.extract(string, {str(r.id): r.name for r in roles}, limit=25)
        return {r[0]: r[-1] for r in response}


def setup(bot: TimeClockBot) -> None:
    bot.add_cog(Admin(bot))
