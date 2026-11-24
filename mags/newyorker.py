# -*- coding: utf-8 -*-
"""The New Yorker：RSS 标题里直接带期号（例如 November 30 & December 7, 2026），
文章页可正常取全文。"""
from __future__ import annotations

import re
from datetime import datetime

import requests

from lib import http, log
from lib.textutil import soup_of, trim_noise

from .base import (Article, Issue, PAYWALL_MARKERS, absolute, date_from_url,
                   extract_body, fragment_html, human_date_win, og_image,
                   parse_date, parse_feed)

MAG_ID = "ny"


def _issue_label_from_feed_title(title: str, fallback_date: str) -> str:
    t = (title or "").strip()
    m = re.search(r"The New Yorker\s+(.+)$", t)
    if m:
        return m.group(1).strip()
    return human_date_win(fallback_date)


def fetch(session: requests.Session, cfg: dict, limit: int = 25,
          date_override: str | None = None) -> Issue:
    r = http.get(session, cfg["feed"], tries=3)
    if r is None:
        raise RuntimeError("The New Yorker：杂志 RSS 抓取失败")
    feed = parse_feed(r.content)
    items = feed["items"]
    log.info("  [ny] 当前期号: %s（%d 条）", feed.get("title", "?"), len(items))

    mag_items = [it for it in items if "/magazine/" in it["link"]]
    for it in mag_items:
        it["date"] = date_from_url(it["link"])

    dated = [it for it in mag_items if it.get("date")]
    if date_override:
        target = date_override
    elif dated:
        target = max(it["date"] for it in dated)
    else:
        target = datetime.now().strftime("%Y-%m-%d")

    picked = [it for it in dated if it["date"] == target] or mag_items
    if limit:
        picked = picked[:limit]

    label = _issue_label_from_feed_title(feed.get("title", ""), target)
    issue = Issue(
        mag_id=MAG_ID,
        name=cfg["name"],
        folder=cfg["folder"],
        issue_date=target,
        issue_label=label,
        source=cfg["feed"],
        brand_color=cfg.get("brand_color", "#0E0E0E"),
        cover_mode=cfg.get("cover_mode", "page"),
    )

    cover_found = ""
    for it in picked:
        url = it["link"]
        cat = (it.get("categories") or [""])[0]
        if cat.lower().startswith("magazine / "):
            cat = cat.split(" / ", 1)[1]
        art = Article(
            title=it["title"],
            url=url,
            section=cat,
            byline=it.get("creator") or "",
            published=(parse_date(it["pub"]).isoformat(timespec="seconds")
                       if parse_date(it["pub"]) else ""),
            summary=re.sub(r"<[^>]+>", "", it.get("description") or "").strip(),
            image=(it.get("images") or [""])[0],
        )
        rr = http.get(session, url, tries=2)
        if rr is not None:
            soup = soup_of(rr.content)
            node, md, txt = extract_body(soup, url)
            low = txt.lower()
            # 只有「正文明显偏短」时才当作付费墙，避免把页脚里的 "already a subscriber" 误判
            paywalled = len(txt) < 2000 and any(mk in low for mk in PAYWALL_MARKERS)
            if node is not None and len(txt) > 600 and not paywalled:
                art.md = trim_noise(md)
                art.html = fragment_html(node)
                art.partial = False
            else:
                art.md = trim_noise(md) or art.summary
                art.html = fragment_html(node) if node is not None else ""
                art.partial = True
            if not art.image:
                art.image = og_image(soup, url)
            if not cover_found:
                cover_found = og_image(soup, url)
            sec_meta = soup.select_one("meta[property='article:section']")
            if sec_meta and sec_meta.get("content") and sec_meta["content"].lower() not in ("tags", ""):
                art.section = sec_meta["content"]
            if not art.byline:
                b = soup.select_one("meta[name='author']") or soup.select_one(
                    "a[class*='contributor']")
                if b is not None:
                    art.byline = (b.get("content") if b.name == "meta" else b.get_text(" ", strip=True)) or ""
        else:
            art.md = art.summary
            art.partial = True
        issue.articles.append(art)

    if not cover_found:
        cover_found = next((a.image for a in issue.articles if a.image), "")
    issue.cover_url = cover_found
    partials = sum(1 for a in issue.articles if a.partial)
    if partials:
        issue.notes.append(f"{partials}/{len(issue.articles)} 篇文章受订阅墙限制，只保留可获取的部分。")
    return issue
