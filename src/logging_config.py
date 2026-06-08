"""
Configuração centralizada de logging para o projeto CODEBA.

Usa logging.config.dictConfig para evitar duplicação de basicConfig
entre múltiplos módulos.
"""

import logging
import logging.config
import os

from src.config import LOG_DIR, LOG_LEVEL


def setup_logging() -> None:
    """Configura o logging do projeto uma única vez."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "app.log")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
        },
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "filename": log_file,
                "encoding": "utf-8",
                "formatter": "standard",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
            },
        },
        "root": {
            "level": LOG_LEVEL,
            "handlers": ["file", "console"],
        },
    }

    logging.config.dictConfig(config)
