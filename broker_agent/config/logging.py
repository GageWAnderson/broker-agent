"""
Logging configuration for the broker_agent application.
"""

import logging
import logging.config
import os
from pathlib import Path
from typing import Any

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Default log level
DEFAULT_LOG_LEVEL = "INFO"


def get_log_level(default_level: str = DEFAULT_LOG_LEVEL) -> str:
    """
    Get the log level from environment or use the default.

    Args:
        default_level: The default log level to use if not specified in environment

    Returns:
        The log level string
    """
    return os.environ.get("LOG_LEVEL", default_level).upper()


def get_log_config(
    log_level: str | None = None, log_file: str | Path | None = None
) -> dict[str, Any]:
    """
    Get logging configuration dictionary.

    Args:
        log_level: Override for log level
        log_file: Optional path to log file

    Returns:
        Dict configuration for logging.config
    """
    level = log_level.upper() if log_level else get_log_level()

    handlers = ["console"]
    if log_file:
        handlers.append("file")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": DEFAULT_LOG_FORMAT,
                "datefmt": DEFAULT_DATE_FORMAT,
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s",
                "datefmt": DEFAULT_DATE_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": handlers,
                "level": level,
                "propagate": True,
            },
            "broker_agent": {
                "handlers": handlers,
                "level": level,
                "propagate": False,
            },
            # Third-party libraries can have their own log levels
            "playwright": {
                "handlers": handlers,
                "level": "WARNING",
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": handlers,
                "level": "WARNING",
                "propagate": False,
            },
        },
    }

    # Add file handler if log file is specified
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "level": level,
            "formatter": "detailed",
            "filename": str(log_file),
            "encoding": "utf8",
        }

    return config


def configure_logging(
    log_level: str | None = None, log_file: str | Path | None = None
) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Override for log level
        log_file: Optional path to log file
    """
    config = get_log_config(log_level, log_file)
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: The name of the logger

    Returns:
        A configured logger
    """
    return logging.getLogger(name)
