# -*- coding: utf-8 -*-
"""TIME：RSS 直接给全文（content:encoded），无需逐篇抓页面，最稳的一条线。"""
from __future__ import annotations

import re
from datetime import datetime

import requests

from lib import http, log
from lib.textutil import html_to_md, html_to_text, soup_of, strip_junk

from .base import (Article, Issue, absolute, fragment_html, human_date_win,
                   parse_date, parse_feed)

MAG_ID = "time"


def _body_from_content(html: str) -> tuple[object, str, str]:
    """content:encoded 本身就是一个完整正文片段。"""
    if not html:
        return None, "", ""
    soup = soup_of(html)
    body = soup.find("body") or soup
    strip_junk(body)
    md = html_to_md(body)
    txt = html_to_text(body)
    return body, md, txt


def fetch(session: requests.Session, cfg: dict, limit: int = 25,
          date_override: str | None = None) -> Issue:
    r = http.get(session, cfg["feed"], tries=3)
    if r is None:
        raise RuntimeError("TIME：RSS 抓取失败")
    feed = parse_feed(r.content)
    items = [it for it in feed["items"] if it["link"]]
    log.info("  [time] RSS %d 条", len(items))
    if not items:
        raise RuntimeError("TIME：RSS 里没有条目")

    for it in items:
        dt = parse_date(it["pub"])
        it["dt"] = dt
        it["date"] = dt.astimezone().strftime("%Y-%m-%d") if dt else date_override

    items.sort(key=lambda x: x["dt"].timestamp() if x.get("dt") else 0, reverse=True)
    if date_override:
        target = date_override
    else:
        target = items[0].get("date") or datetime.now().strftime("%Y-%m-%d")

    picked = items[:limit] if limit else items

    issue = Issue(
        mag_id=MAG_ID,
        name=cfg["name"],
        folder=cfg["folder"],
        issue_date=target,
        issue_label=f"Week of {human_date_win(target)}",
        source=cfg["feed"],
        brand_color=cfg.get("brand_color", "#E90606"),
        cover_mode=cfg.get("cover_mode", "page"),
    )

    for it in picked:
        url = it["link"]
        art = Article(
            title=it["title"],
            url=url,
            section=(it.get("categories") or [""])[0],
            byline=it.get("creator") or "",
            published=(it["dt"].astimezone().isoformat(timespec="seconds") if it.get("dt") else ""),
            summary=re.sub(r"<[^>]+>", "", it.get("description") or "").strip(),
            image=(it.get("images") or [""])[0],
        )
        node, md, txt = _body_from_content(it.get("content") or "")
        if node is not None and len(txt) > 400:
            art.md = md
            art.html = fragment_html(node)
            art.partial = False
        else:
            art.md = art.summary
            art.partial = True
        issue.articles.append(art)

    issue.cover_url = next((a.image for a in issue.articles if a.image), "")
    partials = sum(1 for a in issue.articles if a.partial)
    if partials:
        issue.notes.append(f"{partials} 篇只有摘要（RSS 未带全文）。")
    return issue
