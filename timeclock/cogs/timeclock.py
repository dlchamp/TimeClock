from typing import Optional

import disnake
from disnake.ext import commands

from timeclock import query, utils
from timeclock.bot import TimeClockBot


class TimeClock(commands.Cog):
    """Add timeclock commands"""

    def __init__(self, bot: TimeClockBot) -> None:
        self.bot = bot

    async def check_member_permissions(self, interaction: disnake.AppCmdInter) -> bool:
        """Checks if the member contains any of the mod_roles or has the administrator permissions
        for the guild"""

        member = interaction.author
        if member.guild_permissions.administrator:
            return True

        mod_roles = await query.fetch_guild_roles(interaction.guild.id, is_mod=True)

        if mod_roles is None or mod_roles == []:
            return True

        mod_role_ids = [role.id for role in mod_roles]
        if any(role.id in mod_role_ids for role in member.roles):
            return True

        return False

    @commands.slash_command(name="timesheet")
    async def timesheet(
        self,
        interaction: disnake.AppCmdInter,
        history: Optional[int] = 7,
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
            Specify a member to view their timesheet (Cannot be used with options)

        """

        # check if member argument is being passed, check author permissions

        if all_members or member:
            if all_members and member:
                return await interaction.response.send_message(
                    "If `all_members` is set to True, you cannot include a specific member",
                    ephemeral=True,
                )

            allowed = await self.check_member_permissions(interaction)

            if not allowed:
                return await interaction.response.send_message(
                    "You do not have permissions to view other member timesheets",
                    ephemeral=True,
                )

            if all_members:
                all_members = await query.fetch_all_member_times(
                    interaction.guild.id, history_days=history
                )

                if all_members is None or all_members == []:
                    return await interaction.response.send_message(
                        "No members have clocked in yet!", ephemeral=True
                    )

                # format the timesheet and get totals
                timesheet, total = utils.format_timesheet(
                    interaction.guild, all_members
                )

                embed = utils.create_total_timesheet_embed(
                    interaction.guild, timesheet, total, history
                )

                return await interaction.response.send_message(
                    embed=embed, ephemeral=True
                )

        member = member or interaction.author

        db_member = await query.fetch_member_times(
            interaction.guild.id,
            member.id,
            history,
        )

        if db_member is None:
            return await interaction.response.send_message(
                f"There is no timesheet associated with {member.display_name}.",
                ephemeral=True,
            )

        embed = utils.create_timesheet_embed(member, db_member, history)

        await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot: TimeClockBot) -> None:
    bot.add_cog(TimeClock(bot))
