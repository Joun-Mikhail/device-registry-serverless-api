import logging
import os


def configure_logger(name: str) -> logging.Logger:
    """
    Return a module-level logger configured from the LOG_LEVEL environment variable.

    Defaults to INFO when LOG_LEVEL is absent or unrecognised.
    Set LOG_LEVEL=DEBUG in the SAM template or locally to increase verbosity.
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
