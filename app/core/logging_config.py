"""Merkezi loglama yapılandırması.

LOG_LEVEL .env değişkenine göre yapılandırılır.
Tüm modüller buradaki logger'ları kullanır.
"""

import logging.config
import sys
from typing import Dict, Any

from app.core.config import settings


def _build_config() -> Dict[str, Any]:
    """Logging dictConfig sözlüğünü oluşturup döndürür."""
    log_level = settings.LOG_LEVEL.upper()
    if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        log_level = "INFO"

    return {
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
            "access": {
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
            "console_access": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "access",
                "level": "INFO",
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
            # Uvicorn access logs — timestamp'li formatter kullan
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console_access"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": log_level,
                "handlers": ["console_access"],
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


def setup_logging() -> None:
    """Python logging yapılandırmasını kur.

    LOG_LEVEL değerine göre seviye belirlenir.
    Tüm log'lar stdout'a basılır (Docker dostu).
    """
    config = _build_config()
    logging.config.dictConfig(config)


def get_logging_config() -> Dict[str, Any]:
    """Logging config dict'ini döndürür (uvicorn.run(log_config=...) için)."""
    return _build_config()