import os


class Config:

    # bot token, this should be pulled from the environment variables
    # should not need to change this
    token = os.getenv("TOKEN")
