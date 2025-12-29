from __future__ import annotations

import logging


def setup_logger(
    level: str = "INFO", name: str = "yardmaster", fmt: str | None = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt or "%(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
