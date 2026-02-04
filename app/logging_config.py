"""Logging configuration for the RedCardGenerator application."""

import logging
import os
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
               Defaults to INFO or CARD_LOG_LEVEL env var.

    Returns:
        Configured logger instance.
    """
    log_level = level or os.environ.get("CARD_LOG_LEVEL", "INFO").upper()

    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        log_level = "INFO"

    # Create logger
    logger = logging.getLogger("redcard")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers on reload
    if logger.handlers:
        return logger

    # Console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    # Format: timestamp - level - module - message
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.info(f"Logging initialized at {log_level} level")
    return logger


# Create default logger instance
logger = setup_logging()


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a child logger with the given name.

    Args:
        name: Optional name for the child logger (e.g., "pdf_renderer").

    Returns:
        Logger instance.
    """
    if name:
        return logging.getLogger(f"redcard.{name}")
    return logging.getLogger("redcard")
