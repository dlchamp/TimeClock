import logging
import logging.handlers
from pathlib import Path

import coloredlogs


class IgnoreSpecificMessage(logging.Filter):
    def filter(self, record) -> bool:
        warnings_to_ignore = (
            "PyNaCl is not installed, voice will NOT be supported",
            "Applied processor reduces input query to empty string, all comparisons will have score 0. [Query: '']",
        )
        return not any(warning in record.getMessage() for warning in warnings_to_ignore)


# setup logging format
format_string = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
formatter = logging.Formatter(format_string)

# set stdout logger to INFO
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addFilter(IgnoreSpecificMessage())

stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)


# setup logging file
log_file = Path(f"timeclock/logs/timeclock.log")
log_file.parent.mkdir(exist_ok=True)

# setup logger file handler
# starts a new log file each day at midnight, UTC
# keeps no more than 10 days worth of logs.
file_handler = logging.handlers.TimedRotatingFileHandler(
    log_file, "midnight", utc=True, backupCount=10, encoding="utf-8"
)

file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

coloredlogs.DEFAULT_LEVEL_STYLES = {
    "info": {"color": coloredlogs.DEFAULT_LEVEL_STYLES["info"]},
    "critical": {"color": 9},
    "warning": {"color": 11},
}

# Apply coloredlogs to the stdout handler
coloredlogs.install(level=logging.INFO, logger=logger, stream=stdout_handler.stream)


disnake_logger = logging.getLogger("disnake.client")
disnake_logger.setLevel(logging.WARNING)
disnake_logger.addFilter(IgnoreSpecificMessage())

fuzz_logger = logging.getLogger("thefuzz")
fuzz_logger.setLevel(logging.WARNING)
fuzz_logger.addFilter(IgnoreSpecificMessage())

logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("disnake").setLevel(logging.WARNING)


logger = logging.getLogger()
logger.info("Logging has been initialized")


def get_logger(*args, **kwargs) -> logging.Logger:
    return logging.getLogger(*args, **kwargs)
