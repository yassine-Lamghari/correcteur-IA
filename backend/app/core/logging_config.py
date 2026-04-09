import logging
import sys
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger

class LogConfig(BaseModel):
    """Structured Logging configuration to be set for the server"""

    LOGGER_NAME: str = "autograde"
    LOG_LEVEL: str = "INFO"

    # Logging config dictionary
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%SZ",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "json",
            "class": "logging.StreamHandler",
            "stream": sys.stderr,
        },
    }
    loggers: dict = {
        "autograde": {"handlers": ["default"], "level": LOG_LEVEL, "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
    }

def setup_logging():
    from logging.config import dictConfig
    dictConfig(LogConfig().dict())
