import os


class Config:

    # bot token, this should be pulled from the environment variables
    # should not need to change this
    token = os.getenv("TOKEN")

    # roles that will be allowed ot clock in and out.  If no roles are configured here
    # all members will be able to clock in and out
    # this is a list of role ids `roles = [123456789, 321654987, 456987321]`
    roles = []

    # admin roles or moderator roles are the roles that are allowed to view
    # specific member timesheets if no roles are configured here, only members
    # with the Administrator permissions will be able to use this command
    # this is a list of role ids `roles = [123456789, 321654987, 456987321]`
    mod_role_ids = []
