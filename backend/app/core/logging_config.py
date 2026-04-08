import logging
import sys
from pydantic import BaseModel

class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "autograde"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(name)s | %(message)s"
    LOG_LEVEL: str = "INFO"

    # Logging config
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": sys.stderr,
        },
    }
    loggers: dict = {
        "autograde": {"handlers": ["default"], "level": LOG_LEVEL},
    }

def setup_logging():
    from logging.config import dictConfig
    dictConfig(LogConfig().dict())
