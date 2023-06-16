"""
MIT License

Copyright (c) 2022 DLCHAMP

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

--------------------------------------
Disnake Basic Help Command - 0.3.3
--------------------------------------

Usage:
General help embed includes a description that can be set by setting a `.description` attribute in your bot instance
(ex: bot.description = "My bot description"  or  do not do this and no help embed description will appear

Message and User context commands do not inherently have a description, so these can be set easily by including
{'desc': "Command description"} in the `extras=` kwarg argument 

( ex: @commands.message_command(name="profile", extras={"desc": "View the user's Discord profile"}) )

"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

import disnake
from disnake.ext import commands

from timeclock import components

DESCRIPTION = None
MAX_EMBED_FIELD_CHAR_COUNT = 700
MAX_EMBED_FIELDS = 3
EMBED_BREAK = "\n\n"


@dataclass
class Argument:
    """
    Represents a slash command argument.

    Attributes
    ----------
    name : str
        The name of the argument.
    required : bool
        Indicates if the argument is required.
    description : str
        A brief description of the argument.
    """

    name: str
    required: bool
    description: str


@dataclass
class Command:
    """
    Represents a base command for the bot's API.

    Attributes
    ----------
    id : int
        The command's unique identifier.
    name : str
        The name of the command.
    description : str
        A brief description of the command.
    requires_admin : bool
        Indicates if the command requires admin privileges.
    """

    id: int
    name: str
    description: str
    permission_checks: List[str] = field(default_factory=list)
    role_checks: List[disnake.Role] = field(default_factory=list)

    @property
    def mention(self) -> str:
        """Returns the command as a mention string if it is of type `SlashCommand`
        otherwise it returns a markdown formatted `self.name`
        """
        if isinstance(self, SlashCommand):
            return f"</{self.name}:{self.id}>"
        return f"**{self.name}**"


@dataclass
class SlashCommand(Command):
    """
    Represents a slash command.

    Attributes
    ----------
    args : Optional[List[Argument]]
        A list of arguments for the slash command. Defaults to None.
    """

    args: Optional[List[Argument]] = None
    type: str = "Slash Command"


@dataclass
class UserCommand(Command):
    """
    Represents a user context command.
    """

    type: str = "User Command"


@dataclass
class MessageCommand(Command):
    """
    Represents a message context command.
    """

    type: str = "Message Command"


class Help(commands.Cog):
    """
    A cog class that adds a help command to provide information about all bot slash commands, message commands, user commands,
    and subcommands, along with each command's arguments, if applicable.

    Parameters
    ----------
    bot : `commands.InteractionBot`
        The bot instance to which the cog is added.
    """

    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    @commands.slash_command(name="help")
    async def help_command(
        self, inter: disnake.GuildCommandInteraction, command: Optional[str] = None
    ) -> None:
        """
        Display helpful information about bot's commands.

        Parameters
        ----------
        inter : `disnake.GuildCommandInteraction`
            The command interaction instance.
        command : `Optional[str]`
            The name of a specific command to get information about. Defaults to None.
        """

        all_commands = self._walk_app_commands(inter.guild)

        if command:
            specific_command = self._get_command_named(command, all_commands)
            embed = self._create_command_detail_embed(specific_command)
            await inter.response.send_message(
                embed=embed, components=components.TrashButton(inter.author.id)
            )
            return

        embeds = self._create_help_embed(all_commands)

        if len(embeds) == 1:
            await inter.response.send_message(
                embed=embeds[0], components=components.TrashButton(inter.author.id)
            )
            return

        await inter.response.send_message(
            embed=embeds[0], view=components.Pagination(embeds, inter.author)
        )

    def _get_command_named(
        self, name: str, commands: List[Union[SlashCommand, MessageCommand, UserCommand]]
    ) -> Union[SlashCommand, UserCommand, MessageCommand]:
        """
        Retrieve a single command from the provided list of commands by its name.

        Parameters
        ----------
        name : `str`
            The name of the command to retrieve.
        commands : `List[Union[SlashCommand, MessageCommand, UserCommand]]`
            A list of commands to search through.

        Returns
        -------
        `Union[SlashCommand, UserCommand, MessageCommand]`
            The matched command object or None if not found.
        """

        return next((command for command in commands if name == command.name), None)

    def _parse_checks(
        self,
        command: Union[disnake.APISlashCommand, disnake.APIMessageCommand, disnake.APIUserCommand],
        guild: disnake.Guild,
    ) -> Tuple[List[str], List[disnake.Role]]:
        """
        Parse the checks associated with a command and extract registered permissions and roles
        required to run the command.

        It supports slash commands, message commands, and user commands.

        Parameters
        ----------
        command : `Union[disnake.APISlashCommand, disnake.APIMessageCommand, disnake.APIUserCommand]`
            The command object to parse checks from.
        guild : `disnake.Guild`
            The guild in which the help command was called.

        Returns
        -------
        `Tuple[List[str], List[disnake.Role]]`
            A tuple containing a list of permission names and a list of roles.
            The permission names list contains the names of required permissions,
            and the roles list contains the roles required to execute the command.

        Notes
        -----
        This is an internal method and should not be called directly.
        """

        perm_checks = []
        role_checks = []

        command_type_to_check = {
            disnake.APISlashCommand: self.bot.get_slash_command,
            disnake.APIMessageCommand: self.bot.get_message_command,
            disnake.APIUserCommand: self.bot.get_user_command,
        }

        _command = command_type_to_check.get(type(command))

        if _command is not None:
            checks = _command(command.name).checks

            for check in checks:
                name = check.__qualname__.split(".")[0]
                if "bot" in name:
                    continue

                if not check.__closure__:
                    continue

                closure = check.__closure__[0]
                args = (
                    closure.cell_contents
                    if len(closure.cell_contents) > 1
                    else (closure.cell_contents,)
                )

                if name in ("has_role", "has_any_role"):
                    for arg in args:
                        role = disnake.utils.get(guild.roles, name=arg) or guild.get_role(arg)
                        if role:
                            role_checks.append(role)

                elif name in ("has_permissions", "has_guild_permissions"):
                    perm_checks.extend(
                        [p.replace("_", " ").title() for p, v in closure.cell_contents.items() if v]
                    )

        return perm_checks, role_checks

    def _walk_app_commands(
        self, guild: disnake.Guild
    ) -> List[Union[SlashCommand, MessageCommand, UserCommand]]:
        """
        Retrieve all application commands (slash, message, and user context) for the bot in the specified guild.

        This function combines both global and guild-specific commands, and processes each command type
        to create a list of SlashCommand, MessageCommand, and UserCommand instances.

        Parameters
        ----------
        guild : `disnake.Guild`
            The guild for which to retrieve application commands.

        Returns
        -------
        `List[Union[SlashCommand, MessageCommand, UserCommand]]`
            A list of SlashCommand, MessageCommand, and UserCommand instances representing all application commands
            in the specified guild.

        Notes
        -----
        This is an internal method and should not be called directly.
        """

        all_commands = (
            self.bot.global_application_commands + self.bot.get_guild_application_commands(guild.id)
        )

        def _handle_slash_command(command: disnake.APISlashCommand) -> List[SlashCommand]:
            args = self._get_command_args(command)
            checks = self._parse_checks(command, guild)
            sub_commands = self._get_sub_commands(command, checks)

            return sub_commands or [
                SlashCommand(
                    id=command.id,
                    name=command.name,
                    description=command.description,
                    args=args,
                    permission_checks=checks[0],
                    role_checks=checks[1],
                )
            ]

        def _handle_message_command(command: disnake.APIMessageCommand) -> MessageCommand:
            invokable_command = self.bot.get_message_command(command.name)
            checks = self._parse_checks(command, guild)
            description = invokable_command.extras.get("desc")

            return MessageCommand(
                id=command.id,
                name=command.name,
                description=description,
                permission_checks=checks[0],
                role_checks=checks[1],
            )

        def _handle_user_command(command: disnake.APIUserCommand) -> UserCommand:
            invokable_command = self.bot.get_user_command(command.name)
            checks = self._parse_checks(command, guild)
            description = invokable_command.extras.get("desc")

            return UserCommand(
                id=command.id,
                name=command.name,
                description=description,
                permission_checks=checks[0],
                role_checks=checks[1],
            )

        _commands = []
        for command in all_commands:
            if command.name == "help":
                continue

            if command.type == disnake.ApplicationCommandType.chat_input:
                _commands.extend(_handle_slash_command(command))
            elif command.type == disnake.ApplicationCommandType.message:
                _commands.append(_handle_message_command(command))
            else:
                _commands.append(_handle_user_command(command))

        return _commands

    def _get_sub_commands(
        self,
        command: disnake.APISlashCommand,
        checks: Tuple[List[Optional[str]], List[Optional[str]]],
    ) -> List[SlashCommand]:
        """
        Get and return the parent command's subcommands as a list of SlashCommand objects.

        Parameters
        ----------
        command : `disnake.APISlashCommand`
            The parent command for which to retrieve subcommands.

        Returns
        -------
        `List[SlashCommand]`
            A list of SlashCommand objects representing the subcommands of the parent command.

        Notes
        -----
        This is an internal method and should not be called directly.
        """
        sub_commands = []

        for option in command.options:
            if option.type in (
                disnake.OptionType.sub_command,
                disnake.OptionType.sub_command_group,
            ):
                args = self._get_command_args(option)

                sub_commands.append(
                    SlashCommand(
                        id=command.id,
                        name=f"{command.name} {option.name}",
                        description=option.description,
                        args=args,
                        permission_checks=checks[0],
                        role_checks=checks[1],
                    )
                )

        return sub_commands

    def _get_command_args(self, command: disnake.APISlashCommand) -> List[Argument]:
        """
        Get and return the command's arguments as a list of `Argument` objects.

        Parameters
        ----------
        command : `disnake.APISlashCommand`
            The command for which to retrieve arguments.

        Returns
        -------
        `List[Argument]`
            A list of `Argument` objects representing the arguments of the command.

        Notes
        -----
        This is an internal method and should not be called directly.
        """

        args = []
        for option in command.options:
            if option.type not in (
                disnake.OptionType.sub_command,
                disnake.OptionType.sub_command_group,
            ):
                args.append(
                    Argument(
                        name=option.name, description=option.description, required=option.required
                    )
                )

        return args

    def _format_args_as_string(self, arg: Argument) -> str:
        """
        Formats an `Argument` name with `[]` if required or
        `()` if the argument is optional.

        Parameters
        ----------
        arg : `Argument`
            The argument to format.

        Returns
        -------
        `str`
            The formatted string representing the argument.

        """

        if arg.required:
            return f"[{arg.name}]"

        return f"({arg.name})"

    def _create_command_detail_embed(
        self, command: Union[SlashCommand, UserCommand, MessageCommand]
    ) -> disnake.Embed:
        """
        Create a command detail embed for a given command.

        Parameters
        ----------
        command : `Union[SlashCommand, UserCommand, MessageCommand]`
            The command for which to create the embed.

        Returns
        -------
        `disnake.Embed`
            The command detail embed.

        Notes
        -----
        This is an internal method and should not be called directly.
        """

        embed = disnake.Embed(
            title=f"{command.type} Details",
            description=f"{command.mention}\n*{command.description}*\n\n",
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)

        if isinstance(command, SlashCommand):
            embed.set_footer(text="[ required arguments ] | ( optional arguments )")

        if command.permission_checks:
            permissions = ", ".join(
                p.replace("_", " ").title() for p in command.permission_checks if p
            )
            embed.description += f"**Required Permissions:**\n{permissions}\n"

        if command.role_checks:
            roles = ", ".join(r.mention for r in command.role_checks if r)
            embed.description += f"**Required Roles:**\n{roles}"

        if isinstance(command, SlashCommand):
            if command.args:
                args = [
                    f"**{self._format_args_as_string(arg)}**: *{arg.description or ''}*"
                    for arg in command.args
                ]
                embed.add_field(name="Parameters", value="\n".join(args), inline=True)
            else:
                embed.add_field(name="\u200b", value="Command has no arguments")

        return embed

    def _create_help_embed(
        self, commands: List[Union[SlashCommand, UserCommand, MessageCommand]]
    ) -> List[disnake.Embed]:
        command_sections = self._organize_commands(commands)

        embeds = []
        for name, command_lines in command_sections.items():
            if command_lines:
                base_embed = self._create_base_embed(name)
                chunked_section_content = self._chunk_section_content(command_lines)
                embeds.extend(self._create_section_embeds(base_embed, chunked_section_content))
        return embeds

    def _create_base_embed(self, section_name) -> disnake.Embed:
        base_embed = disnake.Embed(
            title=f"{self.bot.user.display_name} Command Help - {section_name}",
            description=getattr(self.bot, "description", DESCRIPTION),
        )
        base_embed.set_thumbnail(
            url=self.bot.user.avatar.url
            if self.bot.user.avatar
            else self.bot.user.default_avatar.url
        )
        return base_embed

    def _organize_commands(
        self, commands: List[Union[SlashCommand, UserCommand, MessageCommand]]
    ) -> dict:
        command_sections = {
            "Slash Commands": [],
            "User Context Commands": [],
            "Message Context Commands": [],
        }

        for command in commands:
            command_line = f"{command.mention}\n*{command.description}*\n\n"
            if isinstance(command, SlashCommand):
                command_sections["Slash Commands"].append(command_line)
            elif isinstance(command, UserCommand):
                command_sections["User Context Commands"].append(command_line)
            elif isinstance(command, MessageCommand):
                command_sections["Message Context Commands"].append(command_line)

        return command_sections

    def _chunk_section_content(self, command_lines: List[str]) -> List[str]:
        section_content = "".join(command_lines)
        section_chunks = section_content.split(EMBED_BREAK)

        chunked_section_content = []
        temp_content = ""
        for chunk in section_chunks:
            if len(temp_content) + len(chunk) <= MAX_EMBED_FIELD_CHAR_COUNT:
                temp_content += chunk + EMBED_BREAK
            else:
                chunked_section_content.append(temp_content)
                temp_content = chunk + EMBED_BREAK
        chunked_section_content.append(temp_content)

        return chunked_section_content

    def _create_section_embeds(
        self, base_embed: disnake.Embed, section_content: List[str]
    ) -> List[disnake.Embed]:
        embeds = []
        for i, content in enumerate(section_content):
            if i % MAX_EMBED_FIELDS == 0:
                embed = copy.deepcopy(base_embed)
                embeds.append(embed)
            embed.add_field(name=f"\u200b", value=content, inline=False)
        return embeds

    @help_command.autocomplete("command")
    async def command_autocomplete(
        self, inter: disnake.GuildCommandInteraction, string: str
    ) -> List[str]:
        """
        Autocomplete for command option in help command.

        Parameters
        ----------
        inter : `disnake.GuildCommandInteraction`
            The command interaction instance.
        string : `str`
            The string to be matched with commands.

        Returns
        -------
        `List[str]`
            A list of matched command names.
        """
        commands = self._walk_app_commands(inter.guild)
        return [c.name for c in commands if string.lower() in c.name.lower()][:25]


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(Help(bot))
