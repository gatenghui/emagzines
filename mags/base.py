# -*- coding: utf-8 -*-
"""期刊抓取的公共部分：数据结构、RSS 解析、正文抽取。"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import NavigableString, Tag

from lib import log
from lib.textutil import (clean_text, html_to_md, html_to_text, normalize_inline,
                          soup_of, strip_junk, trim_noise)

NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "media": "http://search.yahoo.com/mrss/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "atom": "http://www.w3.org/2005/Atom",
}

# 正文容器的候选选择器（按优先级）
BODY_SELECTORS = [
    "div[data-attribute-verso-pattern='article-body']",
    "div[data-attribute-verso-pattern='body']",
    "div.article__body-text",
    "div[class*='article-body']",
    "div[class*='article__body']",
    "div[class*='story-body']",
    "div[class*='ArticleBody']",
    "section[class*='article-body']",
    "div[class*='post-content']",
    "article",
    "main",
]

PAYWALL_MARKERS = [
    "to continue reading", "subscribe to continue", "this article is for subscribers",
    "already a subscriber", "sign in to read", "unlock this article",
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class Article:
    title: str
    url: str
    section: str = ""
    byline: str = ""
    published: str = ""
    summary: str = ""
    md: str = ""
    html: str = ""
    partial: bool = False
    image: str = ""

    @property
    def words(self) -> int:
        return len((self.md or self.summary or "").split())


@dataclass
class Issue:
    mag_id: str
    name: str
    folder: str
    issue_date: str                 # YYYY-MM-DD
    issue_label: str                # 显示用
    articles: list[Article] = field(default_factory=list)
    cover_url: str = ""
    source: str = ""
    notes: list[str] = field(default_factory=list)
    brand_color: str = "#333333"
    cover_mode: str = "page"        # page = 用站点封面图；generated = 本地排版生成

    @property
    def fulltext_ratio(self) -> float:
        if not self.articles:
            return 0.0
        full = sum(1 for a in self.articles if not a.partial)
        return full / len(self.articles)


def parse_date(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt)
        except Exception:
            continue
    return None


def parse_feed(raw: bytes | str) -> dict:
    """解析 RSS/Atom，返回 {title, link, items:[...]}"""
    root = ET.fromstring(raw)
    ch = root.find("channel")
    result = {"title": "", "link": "", "items": []}
    if ch is not None:
        result["title"] = (ch.findtext("title") or "").strip()
        result["link"] = (ch.findtext("link") or "").strip()
        entries = ch.findall("item")
    else:
        # Atom
        if root.tag.endswith("feed"):
            result["title"] = (root.findtext("atom:title", namespaces=NS) or "").strip()
            entries = root.findall("atom:entry", NS)
        else:
            entries = []

    for it in entries:
        title = (it.findtext("title") or it.findtext("atom:title", namespaces=NS) or "").strip()
        link = (it.findtext("link") or "").strip()
        if not link:
            for ln in it.findall("atom:link", NS):
                if ln.get("rel") in (None, "alternate"):
                    link = ln.get("href") or ""
                    break
        pub = (it.findtext("pubDate") or it.findtext("atom:updated", namespaces=NS)
               or it.findtext("dc:date", namespaces=NS) or "").strip()
        desc = (it.findtext("description") or it.findtext("atom:summary", namespaces=NS) or "").strip()
        ce = it.find("content:encoded", NS)
        content = (ce.text or "") if ce is not None else ""
        cats = [c.text.strip() for c in it.findall("category") if (c.text or "").strip()]
        creator = (it.findtext("dc:creator", default="", namespaces=NS)
                   or it.findtext("atom:author/atom:name", default="", namespaces=NS) or "").strip()
        imgs = []
        for m in it.findall("media:content", NS):
            u = m.get("url")
            if u:
                imgs.append(u)
        for m in it.findall("media:thumbnail", NS):
            u = m.get("url")
            if u:
                imgs.append(u)
        result["items"].append({
            "title": _unescape(title),
            "link": link.strip(),
            "pub": pub,
            "description": desc,
            "content": content,
            "categories": cats,
            "images": imgs,
            "creator": _unescape(creator),
        })
    return result


def _unescape(s: str) -> str:
    import html as h
    s = h.unescape(s or "")
    return re.sub(r"<!\[CDATA\[|\]\]>", "", s).strip()


def date_from_url(url: str) -> str | None:
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})(?:/|$)", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"/(\d{4})(\d{2})(\d{2})(?:/|$)", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def human_date_win(iso: str) -> str:
    try:
        dt = datetime.strptime(iso, "%Y-%m-%d")
        return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
    except Exception:
        return iso


def extract_body(soup, base_url: str) -> tuple[Tag | None, str, str]:
    """返回 (清洗后的正文节点, markdown, text)。"""
    best = None
    best_len = 0
    for sel in BODY_SELECTORS:
        try:
            nodes = soup.select(sel)
        except Exception:
            continue
        for n in nodes:
            txt = n.get_text(" ", strip=True)
            if len(txt) > best_len:
                best, best_len = n, len(txt)
        if best is not None and best_len > 1200:
            break
    if best is None:
        return None, "", ""
    strip_junk(best)
    md = trim_noise(html_to_md(best, base_url))
    txt = html_to_text(best)
    return best, md, txt


def pick_edition_date(items: list[dict], today: str | None = None,
                      window_days: int = 8) -> str | None:
    """在最近 window_days 天里挑「更像一期正刊」的日期。

    经济学人每周出刊，正刊同一天会集中上线几十篇并覆盖所有栏目；
    特刊（the world ahead）或零星更新只覆盖少数栏目。
    打分顺序：该日期覆盖的栏目数 → 篇数 → 日期新旧。
    """
    from collections import defaultdict
    from datetime import date, timedelta

    dates = [it.get("date") for it in items if it.get("date")]
    if not dates:
        return None
    today_d = date.fromisoformat(today) if today else date.today()
    horizon = (today_d - timedelta(days=window_days)).isoformat()

    secs: dict[str, set] = defaultdict(set)
    cnt: dict[str, int] = defaultdict(int)
    for it in items:
        d = it.get("date")
        if not d or d < horizon:
            continue
        secs[d].add(it.get("section") or "-")
        cnt[d] += 1

    if not cnt:
        return max(dates)
    return max(cnt, key=lambda d: (len(secs[d]), cnt[d], d))


def fragment_html(node: Tag | None, inline_images: bool = False) -> str:
    """把正文节点序列化成 EPUB/PDF 可用的 HTML 片段。"""
    if node is None:
        return ""
    clone = soup_of(str(node))
    # 移除标题重复（正文里如果又出现 h1 同名标题，去掉）
    for el in clone.select("h1"):
        el.decompose()
    if not inline_images:
        for el in clone.select("img, picture, source, video, audio, iframe"):
            el.decompose()
    for el in clone.select("figcaption"):
        txt = el.get_text(" ", strip=True)
        if len(txt) < 3:
            el.decompose()
    body = clone.find("body")
    out = "".join(str(c) for c in (body.children if body else clone.children))
    return sanitize_fragment(out)


VOID_TAGS = ("br", "hr", "img", "input", "meta", "link", "source", "area", "col")


def sanitize_fragment(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S | re.I)
    for t in VOID_TAGS:
        html = re.sub(rf"<{t}\b([^>]*?)/?>", rf"<{t}\1/>", html, flags=re.I)
    html = re.sub(r"\s(viewbox|srcset|loading|decoding|data-[\w-]+)=\"[^\"]*\"", "", html, flags=re.I)
    return html.strip()


def absolute(url: str, base: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    return urljoin(base, url)


def og_image(soup, page_url: str) -> str:
    for sel, attr in (("meta[property='og:image']", "content"),
                      ("meta[name='twitter:image']", "content"),
                      ("meta[property='og:image:secure_url']", "content")):
        el = soup.select_one(sel)
        if el and el.get(attr):
            return absolute(el.get(attr), page_url)
    return ""
