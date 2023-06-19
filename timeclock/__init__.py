from timeclock import log

logger = log.get_logger(__name__)


try:
    import dotenv
except ModuleNotFoundError:
    pass

else:
    import dotenv

    dotenv.load_dotenv(override=True)
    logger.info(f"Environment variables loaded from .env file")


__all__ = ()

__version__ = "0.2.5"
