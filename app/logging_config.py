"""Logging setup. Modules log via logging.getLogger(__name__) under "app"."""

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Attach a single stdout handler to the "app" logger (idempotent)."""
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    logger = logging.getLogger("app")
    logger.setLevel(numeric_level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
    logger.propagate = False
