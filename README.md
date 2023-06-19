# TimeClockBot 

## Description

A simple TimeClock discord bot that allows your staff to clock in and out with a simple button click.
Members can view their time sheets with up to 31 days of history.  Mods can view any member's time sheet, or view all members' current clock status and clocked in totals.


## Bot Commands
***Note:** Command arguments that appear between `[` `]` are considered optional, while arguments between `(` `)` are required*
&nbsp;
### Admin only commands
These commands are only useable by guild administrators or members that have a configured moderator role.
&nbsp;
- `/config edit-embed` - Create or update the embed message that the [Punch In/Out] button is attached.  On submission, you will be presented with an example embed. Edit the title and body by clicking the attached [Edit] button. [Save] when you are finished, or [Cancel] to cancel

    - `[image]` - Attach an image that will appear as a larger image at the bottom of the embed
    - `[thumbnail]` - Attach an image that will appear as a smaller image at the top-right of the embed
    - `[clear_images]` - Clear all images from the embed.  (If this is selected, any attached images will not be used)

- `/config add-role` - Add a new role to the guild's configuration stored within the database. With this command you can add moderator roles or specify roles that will be allowed to create punch events.  If no roles are configured, only Guild administrators will be able to moderate time sheets and use these admin commands and all members will be allowed to Punch In/Out
    - `(role)` - The role that will be added to the guild's configured roles
    - `[is_mod]` - Set to True if you wish for this role to be a moderator role (*Default is False*)
    - `[can_punch]` - Set to True if you wish for this role to be able to create punch events (*Default is True*)

- `/config remove-role` - Remove a role from the guild's configuration.  Any members that have been assigned this role will lost their abilities to moderate time sheets or create punch events, unless they have another role that has been configured
    - `(role)` - The role that will be removed from the guild's configured roles.

- `/config view-roles` - Displays all configured roles and their mod/can punch permissions that have been set


### General Commands
These commands are for general member use, however, some arguments are locked behind configured moderator roles, or guild administrators

- `/timesheet` - View your own time sheet, up to 31 days of history can be displayed
    - `[history]` - The amount of historical days to display (*Default is 7, Max is 31*)
    - `[all_members]` - A moderator or server admin only argument that will display all member time sheet totals
    - `[member]` - A moderator or server admin only argument that will display the target member's time sheet


## Self Hosting

### Dependencies

* Built on [Python3 - 3.10+](https://www.python.org/downloads/)
* Install dependencies with poetry (`poetry install`) otherwise use `pip install -r requirements.txt` 

### Getting Started

#### Setting up Discord Bot
1. Login to Discord web - https://discord.com
2. Navigate to Discord Developer Portal - https://discord.com/developers/applications
3. Click *New Application*
4. Give the Application a name and *Create*
5. Add image for Discord icon 
6. Go to Bot tab and click *Add Bot*
7. Keep the default settings for Public Bot - *checked* and Require OAuth2 Code Grant - *unchecked*
8. Add bot image if it did not pull the image from the Application
9. Copy Token and store it somewhere or go ahead and paste it into `.env.sample`
10. Make sure to enable Member intents in the Privileged section.
11. Go to OAuth2 tab
12. Under *Scopes* - Check Bot and applications.commands (needed for slash commands)
13. Under *Bot Permissions* - check Send messages, View Channels
14. Copy the generated link and Go to the URL in your browser - Invite Bot to your Discord server


#### Configure and Run
1. Download this repo and extract to a location
2. Open command and navigate inside of project directory
3. Open the `.env.sample` file in a text editor and paste in your copied token, save, and rename the `.env-sample` to `.env`
5. Create your virtual env `python -m venv venv` and then install the dependencies with `pip install -r requirements.txt`
6. If you wish to use poetry, simple run `poetry install` to create the environment with all dependencies installed
7. Run the bot with `python -m timeclock` or `poetry run python -m timeclock` if you used poetry 

If the bot does not run, make sure that you're in the project's root folder and not inside the `timeclock` directory.  If you run `ls` (or `dir` - Windows) and do not see the `timeclock` directory, you should back out (`cd ../`) until you do see it, then run the bot again.

