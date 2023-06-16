from datetime import datetime
from typing import List, Optional, Tuple

import disnake

from timeclock import db_model as model

__all__ = (
    "format_timedelta",
    "calculate_total",
    "create_total_timesheet_embed",
    "create_timesheet_embed",
    "default_embed",
    "format_timesheet",
)


def format_timedelta(_in: float, _out: float) -> str:
    """Format timedelta difference into a nice string

    Parameters
    ----------
    _in: :type:`float`
        Clock in timestamp
    _out: :type:`float
        Clock out timestamp
    """
    if _out is None:
        return "-"

    diff = datetime.fromtimestamp(_out) - datetime.fromtimestamp(_in)
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, remainder = divmod(remainder, 60)

    return f"{hours} hours, {minutes} minutes"


def calculate_total(times: list[model.Time]) -> str:
    diffs = []
    for time in times:
        if time.punch_in is None:
            continue

        diffs.append(
            (datetime.fromtimestamp(time.punch_out) - datetime.fromtimestamp(time.punch_in)).seconds
        )

    total_seconds = sum(diffs)

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, remainder = divmod(remainder, 60)
    seconds, remainder = divmod(remainder, 60)

    return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"


def create_total_timesheet_embed(
    guild: disnake.Guild, timesheet: str, total: str, history: Optional[int] = 7
) -> disnake.Embed:
    """Creates the embed to be displayed when ALL member time totals are being
    requested

    Parameters
    ----------
    guild: :type:`disnake.Guild`
        Guild object
    members: :type:`str`
        A newline joined list of member display names and calculated time totals
    total: :type:`str`
        A formatted string of total clock in time for all members
    history :type:`Optional[int]`
        Historical days to display
    """
    embed = disnake.Embed(
        title="Member Time Totals",
        description=f"Total On Duty time for the last {history} days\n{total}" or "\u200b",
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="\u200b", value=f"{timesheet}")
    embed.add_field(name="\u200b", value="\u200b")
    embed.set_footer(text="🟢 On Duty | 🔴 Off Duty")

    return embed


def create_timesheet_embed(
    member: disnake.Member,
    db_member: model.Member,
    history: Optional[int] = 7,
) -> disnake.Embed:
    """Create a timesheet embed for the user

    Parameters
    ----------
    member: :type:`disnake.Member`
        The member who's timesheet we are displaying, only using this for avatar values
    db_member: :type:`model.Member`
        The database member object
    history :type:`Optional[int]`
        Historical days to display
    """
    member_times = []
    for time in db_member.times:
        if time.punch_out is None:
            member_times.append(
                f"In: {disnake.utils.format_dt(time.punch_in,'t')} | Out: N/A | Total: {format_timedelta(time.punch_in, time.punch_out)}"
            )
        else:
            member_times.append(
                f"In: {disnake.utils.format_dt(time.punch_in,'t')} | Out: {disnake.utils.format_dt(time.punch_out,'t')} | Total: {format_timedelta(time.punch_in, time.punch_out)}"
            )

    times = "\n".join(member_times)
    total = calculate_total(db_member.times)

    embed = disnake.Embed(
        title=f"Timesheet for {member.display_name}",
        description=f"Total On Duty time for last {history} days\n{total}",
    )
    embed.add_field(name="\u200b", value=times)
    embed.add_field(name="\u200b", value="\u200b")

    if db_member.on_duty:
        embed.set_footer(text=f"🟢 - On Duty")
    else:
        embed.set_footer(text="🔴 - Off Duty")

    return embed


def default_embed():
    """Create and return a default embed"""
    embed = disnake.Embed(
        title="This is your embed title.",
        description="This is the embed body. Both the title and body can be edited via modal by clicking the edit button below",
    )

    return embed


def format_timesheet(guild: disnake.Guild, members: List[model.Member]) -> Tuple[str, str]:
    """Creates the formatted timesheet for the embed and the calculated total clock on time"""

    timesheet = []
    all_times = []

    for member in members:
        if member.on_duty:
            _member = f"🟢 {guild.get_member(int(member.id)).display_name}"
        else:
            _member = f"🔴 {guild.get_member(int(member.id)).display_name}"

        time_totals = calculate_total(member.times)
        timesheet.append(f"{_member} -- {time_totals}")

        all_times.extend(member.times)

    return "\n".join(timesheet), calculate_total(all_times)
