from typing import List, Optional

import disnake
from disnake.ext import commands

from timeclock import components
from timeclock.bot import TimeClockBot
from timeclock.database import Member


class TimeClock(commands.Cog):
    """Add timeclock commands"""

    def __init__(self, bot: TimeClockBot) -> None:
        self.bot = bot

    async def check_member_permissions(self, inter: disnake.GuildCommandInteraction) -> bool:
        """Checks if the member contains any of the mod_roles or has the administrator permissions
        for the guild"""
        mod_roles = await self.bot.get_guild_roles(inter.guild.id, is_mod=True)
        permissions = disnake.Permissions(manage_roles=True)

        return (
            any(role in mod_roles for role in inter.author.roles)
            or inter.author.permissions >= permissions
        )

    def calculate_time_totals(self, seconds: float) -> str:
        """
        Returns the total total formatted as a string
        {days} days, {hours} hours, {minutes} minutes, {seconds} seconds
        """
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, rem = divmod(rem, 60)
        seconds, rem = divmod(rem, 60)

        return (
            f"{int(days)} days, {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"
        )

    def create_all_member_timesheet_embed(
        self, guild: disnake.Guild, members: List[Member], limit: int
    ) -> List[disnake.Embed]:
        """
        Creates and returns a list of embeds that display all members with punch time, their
        current on_duty status, and total on duty time. The content is split into multiple embeds
        if the description exceeds 1000 characters. Embeds after the first one have a title like
        title="Member Time Totals (continued)".

        Parameters
        ----------
        guild: disnake.Guild
            The guild for which the embed is being created
        members: List[Member]
            List of members to be added to the embed output
        limit: int
            The limit for the number of days for which data should be included

        Returns
        -------
        List[disnake.Embed]
            The list of created embeds
        """

        def create_embed(title, description):
            embed = disnake.Embed(title=title, description=description)
            embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
            embed.set_footer(text="🟢 On Duty | 🔴 Off Duty")
            return embed

        total_time = 0
        for member in members:
            total_time += sum(time.as_seconds() for time in member.limit_history(limit))

        total_time_as_string = self.calculate_time_totals(total_time)
        descriptions = [
            f"**Total On Duty time for the last {limit} days**\n{total_time_as_string}\n\n"
        ]
        current_description = descriptions[0]

        for member in members:
            line = f"{member.as_string(guild)}\n"
            if len(current_description + line) > 1000:
                descriptions.append(line)
                current_description = descriptions[-1]  # Change to the last description in the list
            else:
                current_description += line
                descriptions[-1] = current_description  # Update the last description in the list

        embeds = [
            create_embed("Member Time Totals" if i == 0 else "Member Time Totals (continued)", desc)
            for i, desc in enumerate(descriptions)
        ]
        return embeds

    @commands.slash_command(name="timesheet")
    async def timesheet(
        self,
        inter: disnake.GuildCommandInteraction,
        history: int = commands.Param(ge=1, le=31, default=7),
        all_members: Optional[bool] = False,
        member: Optional[disnake.Member] = None,
    ) -> None:
        """View your timesheet (Only admins are allowed to pass a specific member)

        Parameters
        ----------
        history: :type:`str`
            How many days of history to show (Default is 7, Max 31)
        all_members: :type:`Optional[bool]]`
            (Mod only) Set to True to get all members (Cannot be used with member)
        member: :type:`Optional[disnake.Member]`
            Specify a member to view their timesheet (Cannot be used with all_members)

        """
        await inter.response.defer()

        # check if member argument is being passed, check author permissions
        if all_members or member:
            if all_members and member:
                await inter.delete_original_response()
                return await inter.followup.send(
                    "If `all_members` is set to True, you cannot include a specific member",
                    ephemeral=True,
                )

            if not await self.check_member_permissions(inter):
                await inter.delete_original_response()
                return await inter.followup.send(
                    "You do not have permissions to view other member timesheets",
                    ephemeral=True,
                )

            if all_members:
                all_members = await self.bot.get_members(inter.guild.id)

                if not all_members:
                    await inter.delete_original_response()
                    return await inter.followup.send(
                        "No members have clocked in yet!", ephemeral=True
                    )

                embeds = self.create_all_member_timesheet_embed(inter.guild, all_members, history)
                if len(embeds) == 1:
                    await inter.followup.send(
                        embed=embeds[0], components=components.TrashButton(inter.author.id)
                    )
                    return

                await inter.followup.send(
                    embed=embeds[0], view=components.Pagination(embeds, inter.author)
                )
                return

        member = member or inter.author
        tc_member = await self.bot.get_members(inter.guild.id, member_id=member.id)

        if not tc_member:
            await inter.delete_original_response()
            return await inter.followup.send(
                f"There is no timesheet associated with {member.display_name}.",
                ephemeral=True,
            )

        embed = tc_member.create_timesheet_embed(member.name, history=history)
        await inter.followup.send(embed=embed, components=components.TrashButton(inter.author.id))


def setup(bot: TimeClockBot) -> None:
    bot.add_cog(TimeClock(bot))
