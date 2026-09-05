import logging
import sys

from app.core.settings import settings

_CONFIGURED = False


def configure_logging() -> None:
    """
    Gives the application's own loggers a handler.

    Uvicorn configures handlers for its own loggers but leaves the
    root logger bare, so anything the app logs below WARNING is
    discarded. Without this, console emails never appear.
    """
    global _CONFIGURED

    if _CONFIGURED:
        return

    logger = logging.getLogger("app")
    logger.setLevel(settings.LOG_LEVEL.upper())
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(levelname)s:    %(message)s")
        )
        logger.addHandler(handler)

    _CONFIGURED = True
