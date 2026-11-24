# -*- coding: utf-8 -*-
"""日志：同时写控制台和 logs/emagzines-YYYYMMDD.log。"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

_LOGGER = None


def setup(log_dir: Path, quiet: bool = False) -> logging.Logger:
    global _LOGGER
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("emagzines")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")

    fh = logging.FileHandler(
        log_dir / f"emagzines-{datetime.now():%Y%m%d}.log", encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    if not quiet:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    _LOGGER = logger
    return logger


def get() -> logging.Logger:
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = setup(Path("logs"), quiet=False)
    return _LOGGER


def info(msg, *a):
    get().info(msg, *a)


def warn(msg, *a):
    get().warning(msg, *a)


def error(msg, *a):
    get().error(msg, *a)


def debug(msg, *a):
    get().debug(msg, *a)
