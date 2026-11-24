# -*- coding: utf-8 -*-
"""The Economist：以官方 RSS 定「最新一期」，全文受 Cloudflare/付费墙限制时降级为摘要。

取「一期」的规则：
  正刊每周同一天集中上线，覆盖绝大多数栏目；所以按「栏目数 → 篇数」给最近 8 天打分，
  分数最高的那天就是本期正刊日期（特刊如 the world ahead 只有少数栏目，不会被误选）。
全文获取：
  1) 直连文章页（大部分网络会被 Cloudflare 403）；
  2) 配了 cookies/te.txt（浏览器导出的 cf_clearance + 订阅 cookie）时可直连；
  3) 配了 reader_proxy（如自建的 https://r.jina.ai/）时走阅读器代理。
  以上都不通时，保留 RSS 摘要并把该篇标记为 partial。
"""
from __future__ import annotations

import re
from datetime import datetime

import requests

from lib import http, log
from lib.textutil import soup_of, trim_noise

from .base import (Article, Issue, absolute, date_from_url, extract_body,
                   fragment_html, human_date_win, og_image, parse_date, parse_feed,
                   pick_edition_date)

MAG_ID = "te"
SECTION_MAP = {
    "the-world-this-week": "The world this week",
    "leaders": "Leaders",
    "letters": "Letters",
    "briefing": "Briefing",
    "united-states": "United States",
    "the-americas": "The Americas",
    "asia": "Asia",
    "china": "China",
    "middle-east-and-africa": "Middle East & Africa",
    "europe": "Europe",
    "britain": "Britain",
    "international": "International",
    "business": "Business",
    "finance-and-economics": "Finance & economics",
    "science-and-technology": "Science & technology",
    "culture": "Culture",
    "economic-and-financial-indicators": "Economic & financial indicators",
    "obituary": "Obituary",
    "graphic-detail": "Graphic detail",
    "by-invitation": "By invitation",
    "1843": "1843",
    "podcasts": "Podcasts",
    "interactive": "Interactive",
    "the-world-ahead": "The world ahead",
}

# 排序权重：正刊阅读顺序
SECTION_ORDER = [
    "Leaders", "The world this week", "Briefing", "United States", "The Americas",
    "Asia", "China", "Middle East & Africa", "Europe", "Britain", "International",
    "Business", "Finance & economics", "Science & technology", "Culture",
    "Economic & financial indicators", "Obituary", "Graphic detail", "1843",
    "By invitation", "Podcasts", "Interactive", "The world ahead",
]


def section_from_url(url: str) -> str:
    m = re.search(r"economist\.com/([^/]+)/\d{4}/", url)
    if not m:
        return ""
    slug = m.group(1)
    return SECTION_MAP.get(slug, slug.replace("-", " ").title())


def _sort_key(art: Article):
    try:
        return (SECTION_ORDER.index(art.section), art.title)
    except ValueError:
        return (len(SECTION_ORDER), art.title)


def collect_items(session: requests.Session, cfg: dict) -> list[dict]:
    urls = [cfg["feed"]] + list(cfg.get("extra_feeds") or [])
    items: list[dict] = []
    seen = set()
    for fu in urls:
        r = http.get(session, fu, tries=3)
        if r is None:
            log.warn("  [te] 订阅源取不到: %s", fu)
            continue
        try:
            feed = parse_feed(r.content)
        except Exception as e:
            log.warn("  [te] 订阅源解析失败 %s: %s", fu, e)
            continue
        log.info("  [te] %s → %d 条", fu.split("//")[-1][:46], len(feed["items"]))
        for it in feed["items"]:
            link = it["link"]
            if not link or link in seen:
                continue
            seen.add(link)
            it["date"] = date_from_url(link)
            it["section"] = section_from_url(link)
            items.append(it)
    return items


def _page_text(session, url: str, cfg: dict):
    """取文章页 HTML；支持 reader_proxy（阅读器代理前缀，如 https://r.jina.ai/）兜底。"""
    r = http.get(session, url, tries=1, allow_status=(200,))
    if r is not None:
        return r.content, "direct"
    proxy = (cfg.get("reader_proxy") or "").strip()
    if proxy:
        purl = proxy.rstrip("/") + "/" + url
        rr = http.get(session, purl, tries=1, allow_status=(200,))
        if rr is not None:
            log.info("  [te] 直连被拒，改用 reader_proxy")
            return rr.content, "proxy"
    return None, "fail"


def fetch(session: requests.Session, cfg: dict, limit: int = 25,
          date_override: str | None = None) -> Issue:
    items = collect_items(session, cfg)
    if not items:
        raise RuntimeError("The Economist：一个 RSS 源都没抓到")

    dated = [it for it in items if it.get("date")]
    if date_override:
        target = date_override
    else:
        target = pick_edition_date(dated) or datetime.now().strftime("%Y-%m-%d")

    picked = [it for it in dated if it["date"] == target]
    if not picked:
        target = max((it["date"] for it in dated), default=target)
        picked = [it for it in dated if it["date"] == target]
    if not picked:
        picked = items

    # 去重（同一篇可能同时出现在 latest 和栏目源里）
    seen_title, uniq = set(), []
    for it in picked:
        key = it["title"].strip().lower()
        if key in seen_title:
            continue
        seen_title.add(key)
        uniq.append(it)

    issue = Issue(
        mag_id=MAG_ID,
        name=cfg["name"],
        folder=cfg["folder"],
        issue_date=target,
        issue_label=human_date_win(target),
        source=cfg["feed"],
        brand_color=cfg.get("brand_color", "#E3120B"),
        cover_mode=cfg.get("cover_mode", "generated"),
    )

    ok_pages = 0
    for it in uniq:
        url = it["link"]
        art = Article(
            title=it["title"],
            url=url,
            section=it.get("section") or "",
            byline=it.get("creator") or "",
            published=(parse_date(it["pub"]).isoformat(timespec="seconds")
                       if parse_date(it["pub"]) else ""),
            summary=re.sub(r"<[^>]+>", "", it.get("description") or "").strip(),
            image=(it.get("images") or [""])[0],
        )
        raw, how = _page_text(session, url, cfg)
        got_full = False
        if raw:
            soup = soup_of(raw)
            node, md, txt = extract_body(soup, url)
            if node is not None and len(txt) > 800:
                art.md = trim_noise(md)
                art.html = fragment_html(node)
                art.partial = False
                got_full = True
                ok_pages += 1
                if not art.image:
                    art.image = og_image(soup, url)
                rub = soup.select_one("meta[property='article:section']")
                if rub and rub.get("content") and rub["content"].lower() not in ("tags", ""):
                    art.section = rub["content"]
        if not got_full:
            art.md = art.summary
            art.partial = True
        issue.articles.append(art)

    issue.articles.sort(key=_sort_key)
    if limit:
        issue.articles = issue.articles[:limit]

    if ok_pages == 0:
        issue.notes.append(
            "The Economist 网页有 Cloudflare 校验，本次只拿到 RSS 摘要。"
            "解决方式：把浏览器导出的 cookies.txt 放到 cookies/te.txt，"
            "或在 config.yaml 里给 te 配 reader_proxy。"
        )
    elif ok_pages < len(issue.articles):
        issue.notes.append(f"部分文章（{len(issue.articles) - ok_pages} 篇）只能取到摘要。")

    issue.cover_url = next((absolute(it["images"][0], it["link"])
                            for it in uniq if it.get("images")), "")
    return issue
