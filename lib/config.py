# -*- coding: utf-8 -*-
"""配置加载。"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


class Config:
    def __init__(self, path: Path | str = CONFIG_PATH):
        self.path = Path(path)
        with open(self.path, "r", encoding="utf-8") as f:
            self.raw = yaml.safe_load(f) or {}
        self.global_ = self.raw.get("global", {}) or {}
        self.magazines = self.raw.get("magazines", {}) or {}
        self.cookies_cfg = self.raw.get("cookies", {}) or {}
        self.schedule = self.raw.get("schedule", {}) or {}

    # ---- 路径 ----
    @property
    def root(self) -> Path:
        return ROOT

    @property
    def output_dir(self) -> Path:
        p = Path(self.global_.get("output_dir", "library"))
        return p if p.is_absolute() else ROOT / p

    @property
    def log_dir(self) -> Path:
        d = self.log_dir_name
        return Path(d) if os.path.isabs(d) else ROOT / d

    @property
    def log_dir_name(self) -> str:
        return str(self.global_.get("log_dir", "logs"))

    # ---- 行为开关 ----
    def get(self, key, default=None):
        return self.global_.get(key, default)

    @property
    def max_articles(self) -> int:
        return int(self.global_.get("max_articles", 25) or 0)

    @property
    def per_article_md(self) -> bool:
        return bool(self.global_.get("per_article_md", True))

    @property
    def inline_images(self) -> bool:
        return bool(self.global_.get("inline_images", False))

    @property
    def timeout(self) -> int:
        return int(self.global_.get("timeout", 45))

    @property
    def retries(self) -> int:
        return int(self.global_.get("retries", 3))

    @property
    def best_effort(self) -> bool:
        return bool(self.global_.get("best_effort", True))

    @property
    def pdf_engine(self) -> str:
        return str(self.global_.get("pdf_engine", "auto")).lower()

    @property
    def epub_engine(self) -> str:
        return str(self.global_.get("epub_engine", "builtin")).lower()

    @property
    def write_meta(self) -> bool:
        return bool(self.global_.get("write_meta", True))

    # ---- 期刊 ----
    def mag(self, mag_id: str) -> dict:
        cfg = dict(self.magazines.get(mag_id) or {})
        cfg.setdefault("enabled", True)
        cfg.setdefault("name", mag_id)
        cfg.setdefault("folder", mag_id)
        cfg.setdefault("brand_color", "#333333")
        cfg.setdefault("cover_mode", "generated")
        cfg.setdefault("extra_feeds", [])
        cfg.setdefault("fulltext_in_feed", False)
        return cfg

    def enabled_mags(self) -> list[str]:
        return [k for k in ("te", "ny", "time") if self.mag(k).get("enabled", True)]

    def cookie_path(self, mag_id: str) -> Path | None:
        rel = self.cookies_cfg.get(mag_id)
        if not rel:
            return None
        p = Path(rel)
        if not p.is_absolute():
            p = ROOT / p
        return p if p.exists() else None


CONFIG: Config | None = None


def load_config(path: Path | str = CONFIG_PATH) -> Config:
    global CONFIG
    CONFIG = Config(path)
    return CONFIG
