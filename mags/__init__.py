# -*- coding: utf-8 -*-
"""期刊抓取模块。"""
from . import economist, newyorker, time as time_mod

FETCHERS = {
    "te": economist.fetch,
    "ny": newyorker.fetch,
    "time": time_mod.fetch,
}

__all__ = ["FETCHERS", "economist", "newyorker", "time_mod"]
