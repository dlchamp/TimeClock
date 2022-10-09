import json
from typing import List, Optional

import disnake
from disnake.ext import commands

from timeclock import components
from timeclock import db_model as model
from timeclock import query, utils
from timeclock.bot import TimeClockBot


class Admin(commands.Cog):
    """Add admin commands to the bot"""

    def __init__(self, bot: TimeClockBot) -> None:
        self.bot = bot

    async def cog_slash_command_check(self, inter: disnake.AppCmdInter) -> bool:
        """Performs a check for every command within this cog.  If returns True,
        command is invoked, else command.CheckFailed is raise"""
        roles = await query.fetch_guild_roles(inter.guild.id, is_mod=True)
        role_ids = [role.id for role in roles]

        return inter.author.guild_permissions.administrator or any(
            role.id in role_ids for role in inter.author.roles
        )

    async def cog_slash_command_error(
        self, inter: disnake.AppCmdInter, error: Exception
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
    async def config(self, interaction: disnake.AppCmdInter):
        pass

    @config.sub_command(name="edit_embed")
    @commands.guild_only()
    async def config_edit_embed(
        self,
        interaction: disnake.AppCmdInter,
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
        """

        # make sure I can send messages within this channel
        if not interaction.channel.permissions_for(interaction.guild.me).send_messages:
            return await interaction.response.send_message(
                f"Please fix my permissions so that I can send messages in this channel",
                ephemeral=True,
            )

        db_guild: model.Guild = await query.fetch_guild_config(interaction.guild.id)
        if db_guild is None:
            embed = utils.default_embed()
            message = None
        else:
            embed = disnake.Embed.from_dict(json.loads(db_guild.embed))
            channel = interaction.guild.get_channel(db_guild.channel_id)
            message = channel.get_partial_message(db_guild.message_id)

        embed.set_image(url=image.proxy_url if image and not clear_images else None)
        embed.set_thumbnail(
            url=thumbnail.proxy_url if thumbnail and not clear_images else None
        )

        view = components.EditEmbedButtons(message)
        await interaction.response.send_message(
            "Here is your currently configured embed. Use the buttons to below to edit, save, or cancel these changes\n"
            "If you wish to add an image or thumbnail, please [Cancel] and attach them with the optional command arguments.\n\n"
            "If this is the first time running this command, or the previous message was deleted, make sure you're using this command within the channel where you wish to post the 'Punch' embed.",
            embed=embed,
            ephemeral=True,
            view=view,
        )

    @config.sub_command(name="add_role")
    async def config_add_mod_role(
        self,
        interaction: disnake.AppCmdInter,
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
        await query.add_role(interaction.guild.id, role.id, is_mod, can_punch)
        await interaction.response.send_message(
            f"{role.mention} has been configured in **{interaction.guild.name}** with the following permissions:\n"
            f"Mod: **{is_mod}**\nCan Punch: **{can_punch}**",
            ephemeral=True,
        )

    @config.sub_command("remove_role")
    async def config_remove_role(self, interaction: disnake.AppCmdInter, role: str):
        """
        Remove a role from the config. This role will be removed from the database

        Parameters
        ----------
        role: :type:`str`
            The name of the role you wish to remove
        """
        if role == "No roles have been configured":
            return await interaction.response.send_message(
                "No roles have been configured for this guild", ephemeral=True
            )

        role = disnake.utils.get(interaction.guild.roles, name=role.split(" (")[0])

        if role is None:
            return await interaction.response.send_message(
                f"{role.split(' (')[0]} does not exist within **{interaction.guild.name}**"
            )

        await query.remove_role(role.id)

        await interaction.response.send_message(
            f"{role.mention} was removed from **{interaction.guild.name}'s configuration.",
            ephemeral=True,
        )

    @config_remove_role.autocomplete("role")
    async def remove_role_autocomplete(
        self, interaction: disnake.AppCmdInter, string: str
    ) -> List[str]:
        """
        Provides options to the user for selecting a role to remove from the database

        Parameters
        ----------
        string: :type:`str`
            The argument string as provided from discord via user input
        """
        roles = await query.fetch_guild_roles(interaction.guild.id)
        if roles is None or roles == []:
            return ["No roles have been configured"]

        roles = [
            f"{interaction.guild.get_role(role.id).name} (Mod: {role.is_mod} | Can Punch: {role.can_punch}"
            for role in roles
        ]

        return [role for role in roles if string.lower() in role.lower()]


def setup(bot: TimeClockBot) -> None:
    bot.add_cog(Admin(bot))
