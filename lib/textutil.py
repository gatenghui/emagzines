# -*- coding: utf-8 -*-
"""HTML → Markdown / 纯文本，以及各种清洗工具。"""
from __future__ import annotations

import html as html_mod
import re
import unicodedata

from bs4 import BeautifulSoup, NavigableString, Tag

# 文章正文里要整块丢掉的垃圾
# 注意：选择器宁可窄不要宽。曾经用 [class*=paywall] 把 New Yorker 的正文整块删掉
# （它的正文容器本身带 paywall 字样），所以这里全部限定到具体的按钮/提示块。
JUNK_SELECTORS = [
    "script", "style", "noscript", "iframe", "form", "button", "svg",
    "footer", "nav", "aside",
    ".ad", ".ads", ".advertisement", "[data-ad]", "[data-ads]",
    "[class*='advert-']", "[class*='ad-slot']", "[id*='div-gpt-ad']",
    "[class*='newsletter-signup']", "[class*='subscribe-now']",
    "[class*='subscribe-form']", "[class*='subscription-cta']",
    "[class*='paywall-cta']", "[class*='paywall-message']",
    "[class*='paywall-overlay']", "[class*='paywall-prompt']",
    "[data-testid*='paywall']", "[class*='regwall']",
    "[class*='social-share']", "[class*='share-tools']", "[class*='share-bar']",
    "[class*='read-next']", "[class*='recirc']", "[class*='related-articles']",
    "[class*='-comments']",
]

JUNK_TEXT = {
    "save this story", "save this storysave this story", "advertisement",
    "listen to this article", "share", "facebook", "twitter", "email",
}

# 正文首尾常见的噪音行（按整行匹配，去掉）
NOISE_LINE_PATTERNS = [
    r"^save this story$",
    r"^advertisement$",
    r"^listen to this article.*$",
    r"^share this (story|article)$",
    r"^photograph by .{0,80}$",
    r"^illustration by .{0,80}$",
    r"^read more:?$",
    r"^sign up for .{0,80}$",
    r"^\s*$",
]


def soup_of(raw: bytes | str) -> BeautifulSoup:
    if isinstance(raw, bytes):
        return BeautifulSoup(raw, "lxml")
    return BeautifulSoup(raw, "lxml")


def strip_junk(node: Tag) -> None:
    for sel in JUNK_SELECTORS:
        try:
            for el in node.select(sel):
                el.decompose()
        except Exception:
            continue


def normalize_inline(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return text


def clean_text(text: str) -> str:
    """压缩空行、去掉孤立控制符。"""
    text = normalize_inline(text)
    lines = [ln.rstrip() for ln in text.split("\n")]
    out, blank = [], 0
    for ln in lines:
        if not ln.strip():
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(ln)
    return "\n".join(out).strip()


def _inline_md(node, base_url: str = "") -> str:
    """把一个块级元素内部的 inline 内容转成 md 文本。"""
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(normalize_inline(str(child)))
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name.lower()
        if name == "br":
            parts.append("  \n")
        elif name in ("em", "i", "cite"):
            inner = _inline_md(child, base_url).strip()
            parts.append(f"*{inner}*" if inner else "")
        elif name in ("strong", "b"):
            inner = _inline_md(child, base_url).strip()
            parts.append(f"**{inner}**" if inner else "")
        elif name == "code":
            inner = child.get_text()
            parts.append(f"`{inner}`")
        elif name == "a":
            inner = _inline_md(child, base_url).strip()
            href = child.get("href") or ""
            if href.startswith("/") and base_url:
                from urllib.parse import urljoin
                href = urljoin(base_url, href)
            if inner and href and not href.startswith("javascript"):
                parts.append(f"[{inner}]({href})")
            else:
                parts.append(inner)
        elif name == "img":
            continue
        elif name in ("sup", "sub"):
            inner = _inline_md(child, base_url).strip()
            parts.append(f"^{inner}^" if inner else "")
        elif name == "span":
            parts.append(_inline_md(child, base_url))
        else:
            parts.append(_inline_md(child, base_url))
    return "".join(parts)


def html_to_md(node: Tag, base_url: str = "", drop_captions: bool = False) -> str:
    """递归把正文节点转 Markdown。"""
    out: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            t = normalize_inline(str(child))
            if t.strip():
                out.append(t.strip())
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name.lower()
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = min(int(name[1]) + 1, 6)  # 文章标题已经占 #，正文层级下移
            txt = _inline_md(child, base_url).strip()
            if txt:
                out.append(f"\n{'#' * level} {txt}\n")
        elif name == "p":
            txt = _inline_md(child, base_url).strip()
            if txt:
                out.append(f"{txt}\n")
        elif name == "blockquote":
            txt = html_to_md(child, base_url).strip()
            if txt:
                quoted = "\n".join("> " + ln for ln in txt.splitlines())
                out.append(f"{quoted}\n")
        elif name in ("ul", "ol"):
            items = []
            for i, li in enumerate(child.find_all("li", recursive=False), 1):
                txt = _inline_md(li, base_url).strip()
                if txt:
                    items.append(f"{i}. {txt}" if name == "ol" else f"- {txt}")
            if items:
                out.append("\n".join(items) + "\n")
        elif name == "figure":
            cap = child.find("figcaption")
            if cap and not drop_captions:
                txt = _inline_md(cap, base_url).strip()
                if txt:
                    out.append(f"*{txt}*\n")
        elif name == "hr":
            out.append("\n---\n")
        elif name in ("pre",):
            out.append("```\n" + child.get_text() + "\n```\n")
        elif name == "table":
            rows = []
            for tr in child.find_all("tr"):
                cells = [_inline_md(td, base_url).strip() for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append("| " + " | ".join(cells) + " |")
            if rows:
                out.append("\n".join(rows) + "\n")
        elif name in ("div", "section", "article", "main", "span", "header", "body", "li"):
            inner = html_to_md(child, base_url, drop_captions)
            if inner.strip():
                out.append(inner.strip() + "\n")
        else:
            txt = _inline_md(child, base_url).strip()
            if txt:
                out.append(f"{txt}\n")
    return clean_text("\n".join(out))


def html_to_text(node: Tag) -> str:
    txt = node.get_text("\n", strip=True)
    return clean_text(normalize_inline(txt))


def looks_like_junk(text: str) -> bool:
    t = text.strip().lower()
    return t in JUNK_TEXT or len(t) < 3


def slugify(title: str, maxlen: int = 60) -> str:
    t = unicodedata.normalize("NFKD", title or "")
    t = t.encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return (t or "article")[:maxlen]


def trim_noise(md: str) -> str:
    """去掉正文首尾的“Save this story / Photograph by / Advertisement”等噪音行。"""
    if not md:
        return ""
    lines = md.splitlines()
    pats = [re.compile(p, re.I) for p in NOISE_LINE_PATTERNS]

    def noisy(ln: str) -> bool:
        s = ln.strip()
        if not s:
            return True
        if s.replace("*", "").strip().lower() in JUNK_TEXT:
            return True
        return any(p.match(s) for p in pats)

    start, end = 0, len(lines) - 1
    while start <= end and noisy(lines[start]):
        start += 1
    while end >= start and noisy(lines[end]):
        end -= 1
    return clean_text("\n".join(lines[start:end + 1]))


def strip_html(raw: str) -> str:
    if not raw:
        return ""
    return html_mod.unescape(re.sub(r"<[^>]+>", " ", raw)).strip()
