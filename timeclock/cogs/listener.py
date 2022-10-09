from datetime import datetime

import disnake
from disnake.ext import commands

from timeclock import db_model as model
from timeclock import query
from timeclock.bot import TimeClockBot


class Listeners(commands.Cog):
    """Add an event listener for button clicks"""

    def __init__(self, bot: TimeClockBot) -> None:
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def punch_in_out_click(self, interaction: disnake.MessageInteraction) -> None:
        """A button click event listeners specifically listening for users that click on
        the punch in/out button"""

        if interaction.component.custom_id != "punch":
            return

        member = interaction.author
        allowed = await self.punch_allowed(interaction.author)

        if not allowed:
            return await interaction.response.send_message(
                "You don't have a role that is allowed to punch in/out", ephemeral=True
            )

        timestamp = datetime.timestamp(disnake.utils.utcnow())
        db_member = await query.add_member_punch_event(
            interaction.guild.id, member.id, timestamp
        )

        embed = self.create_punch_embed(member, db_member, timestamp)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    def create_punch_embed(
        self, member: disnake.Member, db_member: model.Member, timestamp: float
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
            event: model.Time = [time for time in db_member.times][-1]
            embed.description = f"You clocked out at {disnake.utils.format_dt(timestamp, 't')} after clocking in {disnake.utils.format_dt(event.punch_in, 'R')}"

        return embed

    async def punch_allowed(self, member: disnake.Member) -> bool:
        """Check if the member is allowed to punch in or not"""

        allowed_roles = await query.fetch_guild_roles(member.guild.id, can_punch=True)
        if allowed_roles == []:
            return True

        allowed_role_ids = [role.id for role in allowed_roles]
        if any(role.id in allowed_role_ids for role in member.roles):
            return True

        return False


def setup(bot: TimeClockBot) -> None:
    bot.add_cog(Listeners(bot))
