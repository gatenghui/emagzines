# -*- coding: utf-8 -*-
"""HTTP 会话：UA、重试、cookies（Netscape / JSON 两种格式都能读）。"""
from __future__ import annotations

import http.cookiejar
import json
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import log

UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

BASE_HEADERS = {
    "User-Agent": UA_DESKTOP,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def _load_netscape(lines: list[str]) -> http.cookiejar.CookieJar:
    jar = http.cookiejar.CookieJar()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            # "#HttpOnly_" 前缀行也是 cookie，去掉前缀再看
            if line.startswith("#HttpOnly_"):
                line = line[len("#HttpOnly_"):]
            else:
                continue
        parts = line.split("\t")
        if len(parts) != 7:
            continue
        domain, flag, path, secure, expires, name, value = parts
        try:
            exp = int(float(expires)) if expires else None
        except ValueError:
            exp = None
        jar.set_cookie(
            http.cookiejar.Cookie(
                version=0, name=name, value=value, port=None, port_specified=False,
                domain=domain, domain_specified=True, domain_initial_dot=domain.startswith("."),
                path=path or "/", path_specified=True,
                secure=(secure.upper() == "TRUE"),
                expires=exp, discard=False, comment=None, comment_url=None,
                rest={"HttpOnly": None}, rfc2109=False,
            )
        )
    return jar


def make_session(cookie_path: Path | None = None, timeout: int = 45, retries: int = 3) -> requests.Session:
    s = requests.Session()
    s.headers.update(BASE_HEADERS)
    retry = Retry(
        total=max(1, retries),
        connect=max(1, retries),
        read=max(1, retries),
        backoff_factor=1.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.request_timeout = timeout  # type: ignore[attr-defined]

    if cookie_path and Path(cookie_path).exists():
        try:
            raw = Path(cookie_path).read_text(encoding="utf-8", errors="ignore")
            if raw.lstrip().startswith(("{", "[")):
                data = json.loads(raw)
                if isinstance(data, dict) and "cookies" in data:
                    data = data["cookies"]
                for c in data:
                    s.cookies.set(c.get("name"), c.get("value"),
                                  domain=c.get("domain", ""), path=c.get("path", "/"))
            else:
                jar = _load_netscape(raw.splitlines())
                for ck in jar:
                    s.cookies.set_cookie(ck)
            log.info("  载入 cookies: %s (%d 条)", cookie_path, len(s.cookies))
        except Exception as e:
            log.warn("  cookies 读取失败 %s: %s", cookie_path, e)
    return s


def get(session: requests.Session, url: str, *, tries: int = 3, timeout: int | None = None,
        headers: dict | None = None, allow_status=(200,)):
    """带重试的 GET，返回 Response（失败返回 None）。"""
    timeout = timeout or getattr(session, "request_timeout", 45)
    last = None
    for i in range(max(1, tries)):
        try:
            r = session.get(url, timeout=timeout, headers=headers)
            if r.status_code in allow_status:
                return r
            last = f"HTTP {r.status_code}"
            # 403/404 是硬拒绝，重试没意义
            if r.status_code in (401, 403, 404, 410):
                break
        except Exception as e:
            last = str(e)
        time.sleep(1.0 + i * 1.5)
    log.debug("GET 失败 %s -> %s", url, last)
    return None
