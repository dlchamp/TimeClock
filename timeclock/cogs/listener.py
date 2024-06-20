from datetime import datetime
from typing import Union

import disnake
from disnake.ext import commands

from timeclock import log
from timeclock.bot import TimeClockBot
from timeclock.database import Guild, Member

logger = log.get_logger(__name__)


class Listeners(commands.Cog):
    """Add an event listener for button clicks"""

    def __init__(self, bot: TimeClockBot) -> None:
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def handle_trash_button(self, inter: disnake.MessageInteraction) -> None:
        """Delete a message if the user has permission to do so"""

        if not "trash" in inter.component.custom_id:
            return

        roles = await self.bot.guild_cache.get_roles(inter.guild.id, is_mod=True)
        mod_role_ids = [role.id for role in roles]

        if (
            not str(inter.author.id) in inter.component.custom_id
            and not inter.channel.permissions_for(inter.author).manage_messages
            and not any(role.id in mod_role_ids for role in inter.author.roles)
        ):
            await inter.response.send_message(
                "You are not the person that requested this message.", ephemeral=True
            )
            return

        await inter.response.defer()
        await inter.delete_original_response()

    @commands.Cog.listener("on_button_click")
    async def punch_in_out_click(self, inter: disnake.MessageInteraction) -> None:
        """A button click event listeners specifically listening for users that click on
        the punch in/out button"""

        if inter.component.custom_id != "punch":
            return

        allowed = await self.punch_allowed(inter.author)

        if not allowed:
            return await inter.response.send_message(
                "You don't have a role that is allowed to punch in/out", ephemeral=True
            )

        timestamp = datetime.timestamp(disnake.utils.utcnow())
        member = await self.bot.member_cache.add_punch_event(
            inter.guild.id, inter.author.id, timestamp
        )
        logger

        embed = self.create_punch_embed(inter.author, member, timestamp)

        await inter.response.send_message(embed=embed, ephemeral=True, delete_after=5)

    def create_punch_embed(
        self, member: disnake.Member, db_member: Member, timestamp: float
    ) -> disnake.Embed:
        embed = disnake.Embed()
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar.url if member.display_avatar else None,
        )

        # member just clocked in
        if db_member.on_duty:
            embed.description = f"You clocked in at {disnake.utils.format_dt(timestamp, 't')}"

        # member clocked out
        else:
            # get most recent clock in event time
            event = [time for time in db_member.times][-1]
            embed.description = f"You clocked out at {disnake.utils.format_dt(timestamp, 't')} after clocking in {disnake.utils.format_dt(event.punch_in, 'R')}"

        return embed

    async def punch_allowed(self, member: disnake.Member) -> bool:
        """Check if the member is allowed to punch in or not"""

        allowed_roles = await self.bot.guild_cache.get_roles(member.guild.id, is_mod=True)
        if allowed_roles == []:
            return True

        allowed_role_ids = [role.id for role in allowed_roles]
        if any(role.id in allowed_role_ids for role in member.roles):
            return True

        return False

    @commands.Cog.listener("on_raw_message_delete")
    @commands.Cog.listener("on_raw_bulk_message_delete")
    async def handle_message_delete(
        self, payload: Union[disnake.RawBulkMessageDeleteEvent, disnake.RawMessageDeleteEvent]
    ) -> None:
        """If any messages are deleted that contain the configured message ID for an embed,
        the message, channel, and embeds that have been configured are removed."""

        if isinstance(payload, disnake.RawBulkMessageDeleteEvent):
            message_ids = payload.message_ids

        else:
            message_ids = [payload.message_id]

        if payload.guild_id is None:
            return

        guild = await self.bot.guild_cache.get_guild(payload.guild_id)

        if not guild or guild.message_id is None:
            return

        for message_id in message_ids:
            if message_id == guild.message_id:
                logger.info(f"Config message `{message_id}` deleted in `{payload.guild_id}`")
                await self.bot.guild_cache.update_guild(
                    payload.guild_id, message_id=message_id, channel_id=None
                )
                break


def setup(bot: TimeClockBot) -> None:
    bot.add_cog(Listeners(bot))
