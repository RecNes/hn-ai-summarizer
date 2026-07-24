"""Merkezi loglama yapılandırması.

LOG_LEVEL .env değişkenine göre yapılandırılır.
Tüm modüller buradaki logger'ları kullanır.
"""

import logging.config
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Python logging yapılandırmasını kur.

    LOG_LEVEL değerine göre seviye belirlenir.
    Tüm log'lar stdout'a basılır (Docker dostu).
    """
    log_level = settings.LOG_LEVEL.upper()
    if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        log_level = "INFO"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": (
                    "[%(asctime)s] %(levelname)-7s %(name)s | "
                    "%(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": (
                    "[%(asctime)s] %(levelname)-7s %(name)s "
                    "(%(filename)s:%(lineno)d) | %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
                "level": log_level,
            },
            "console_detailed": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "detailed",
                "level": "DEBUG",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
        "loggers": {
            # Application loggers - all use root config
            "app": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # Third-party loggers - keep at WARNING to reduce noise
            "httpx": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "httpcore": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "openai": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "anthropic": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "arq": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "alembic": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "redis": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "urllib3": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)