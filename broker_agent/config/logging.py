"""
Logging configuration for the broker_agent application.
"""

import logging
import logging.config
from pathlib import Path
from typing import Any

from broker_agent.config.settings import config as broker_agent_config

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Default log level
DEFAULT_LOG_LEVEL = "INFO"

# Color mapping for different log levels
LOG_COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
    "RESET": "\033[0m",  # Reset to default
}


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter to add colors to log messages based on their level.
    """

    def format(self, record):
        levelname = record.levelname
        if levelname in LOG_COLORS:
            record.levelname = (
                f"{LOG_COLORS[levelname]}{levelname}{LOG_COLORS['RESET']}"
            )
        return super().format(record)


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

    level = log_level.upper() if log_level else broker_agent_config.LOGGING_LEVEL

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
                "()": "broker_agent.config.logging.ColoredFormatter",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s",
                "datefmt": DEFAULT_DATE_FORMAT,
                "()": "broker_agent.config.logging.ColoredFormatter",
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
