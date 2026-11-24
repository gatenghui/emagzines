# -*- coding: utf-8 -*-
"""PDF 生成：优先 calibre ebook-convert，没装就用 Chrome/Edge 无头打印。"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import log

CALIBRE_CANDIDATES = [
    r"C:\Program Files\Calibre2\ebook-convert.exe",
    r"C:\Program Files (x86)\Calibre2\ebook-convert.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Calibre2\ebook-convert.exe"),
    r"D:\Program Files\Calibre2\ebook-convert.exe",
    "/Applications/calibre.app/Contents/MacOS/ebook-convert",
    "/usr/bin/ebook-convert",
    "/usr/local/bin/ebook-convert",
]

CHROMIUM_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
]

PRINT_CSS = """
@page { size: A4; margin: 18mm 16mm 16mm 16mm; }
@page :first { margin: 0; }
* { box-sizing: border-box; }
body { font-family: Georgia, "Times New Roman", "Songti SC", serif;
       font-size: 10.8pt; line-height: 1.62; color: #111; margin: 0; }
.cover { page-break-after: always; height: 297mm; width: 210mm;
         display: flex; flex-direction: column; justify-content: center;
         background: #111; color: #fff; padding: 26mm 20mm; }
.cover img { max-width: 100%; max-height: 200mm; object-fit: contain; margin-bottom: 14mm; }
.cover .mast { font-size: 34pt; font-weight: 700; letter-spacing: .04em;
               text-transform: uppercase; line-height: 1.08; }
.cover .issue { margin-top: 6mm; font-size: 15pt; opacity: .9; }
.cover .note { margin-top: 12mm; font-size: 8.5pt; opacity: .55; }
h1.doc { font-size: 20pt; margin: 0 0 6mm; border-bottom: 2px solid #111; padding-bottom: 3mm; }
.toc { page-break-after: always; }
.toc h2 { font-size: 15pt; margin: 0 0 5mm; }
.toc ol { padding-left: 7mm; }
.toc li { margin: 0 0 2.6mm; font-size: 10.5pt; }
.toc .sec { color: #666; font-size: 9pt; }
article { page-break-before: always; }
article h2.atitle { font-size: 15.5pt; line-height: 1.25; margin: 0 0 2mm; }
article .meta { font-size: 8.6pt; color: #666; margin: 0 0 5mm;
                border-bottom: 1px solid #ddd; padding-bottom: 2mm; }
article p { margin: 0 0 3.2mm; text-align: justify; hyphens: auto; }
article h3 { font-size: 11.6pt; margin: 5mm 0 2mm; }
article blockquote { margin: 3mm 0 3mm 4mm; padding-left: 4mm;
                     border-left: 2.5pt solid #ccc; color: #333; }
article figure { margin: 3mm 0; }
article img { max-width: 100%; }
article figcaption { font-size: 8.4pt; color: #666; }
.missing { background: #fff5f5; border-left: 3pt solid #d33; padding: 3mm; font-size: 9.4pt; color: #a00; }
footer { font-size: 8pt; color: #999; }
"""


def find_calibre() -> str | None:
    p = shutil.which("ebook-convert")
    if p:
        return p
    for c in CALIBRE_CANDIDATES:
        if c and Path(c).exists():
            return c
    return None


def find_chromium() -> str | None:
    for c in CHROMIUM_CANDIDATES:
        if c and Path(c).exists():
            return c
    for name in ("chrome", "msedge", "chromium"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                            errors="replace")
        return cp.returncode, (cp.stdout or "") + (cp.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "timeout"
    except Exception as e:
        return -2, str(e)


def _valid_pdf(p: Path) -> bool:
    try:
        if not p.exists() or p.stat().st_size < 2000:
            return False
        with open(p, "rb") as f:
            return f.read(5).startswith(b"%PDF")
    except Exception:
        return False


def render_pdf(html_path: Path, pdf_path: Path, engine: str = "auto",
               epub_path: Path | None = None) -> tuple[bool, str]:
    """返回 (成功, 使用引擎描述)。"""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.unlink(missing_ok=True)

    cal = find_calibre()
    if engine in ("auto", "calibre") and cal:
        if epub_path and Path(epub_path).exists():
            code, out = _run([cal, str(epub_path), str(pdf_path)])
            if code == 0 and _valid_pdf(pdf_path):
                return True, f"calibre ({Path(cal).name})"
            log.warn("  calibre 转 PDF 失败(code=%s)，改用浏览器打印: %s", code,
                     out.strip().splitlines()[-1] if out.strip() else "")
        elif engine == "calibre":
            log.warn("  calibre 模式下没有 EPUB，改用浏览器打印")

    chrom = find_chromium()
    if not chrom:
        log.error("  找不到 Chrome/Edge，也无法用 calibre 生成 PDF")
        return False, "none"

    tmp_profile = pdf_path.parent / "_chrome_profile"
    cmd = [
        chrom,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--virtual-time-budget=12000",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--user-data-dir={tmp_profile}",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    code, out = _run(cmd, timeout=420)
    if not _valid_pdf(pdf_path):
        # 老版本 Chrome 用的头
        cmd[cmd.index("--headless=new")] = "--headless"
        code, out = _run(cmd, timeout=420)
    ok = _valid_pdf(pdf_path)
    shutil.rmtree(tmp_profile, ignore_errors=True)
    if not ok:
        tail = (out or "").strip().splitlines()[-3:]
        log.error("  浏览器打印 PDF 失败: %s", " | ".join(tail))
        return False, Path(chrom).name
    return True, Path(chrom).stem


def build_print_html(dest: Path, *, masthead: str, issue_label: str, cover: Path | None,
                     articles: list[dict], note: str = "") -> Path:
    """把所有文章拼成一个可打印 HTML。"""
    import html as _h

    def esc(s):
        return _h.escape(s or "", quote=True)

    parts: list[str] = []
    parts.append("<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">")
    parts.append(f"<title>{esc(masthead)} — {esc(issue_label)}</title>")
    parts.append(f"<style>{PRINT_CSS}</style></head><body>")

    # 封面页
    parts.append('<section class="cover">')
    if cover and Path(cover).exists():
        parts.append(f'<img src="{Path(cover).resolve().as_uri()}" alt="cover">')
    parts.append(f'<div class="mast">{esc(masthead)}</div>')
    parts.append(f'<div class="issue">{esc(issue_label)}</div>')
    if note:
        parts.append(f'<div class="note">{esc(note)}</div>')
    parts.append("</section>")

    # 目录
    parts.append('<section class="toc"><h2>Contents</h2><ol>')
    for i, a in enumerate(articles, 1):
        sec = f' <span class="sec">— {esc(a.get("section",""))}</span>' if a.get("section") else ""
        parts.append(f'<li><a href="#a{i}">{esc(a["title"])}</a>{sec}</li>')
    parts.append("</ol></section>")

    # 正文
    for i, a in enumerate(articles, 1):
        meta_bits = [b for b in (a.get("section"), a.get("byline"), a.get("url")) if b]
        meta = " · ".join(esc(b) for b in meta_bits)
        parts.append(f'<article id="a{i}">')
        parts.append(f'<h2 class="atitle">{esc(a["title"])}</h2>')
        parts.append(f'<div class="meta">{meta}</div>')
        if a.get("partial"):
            parts.append('<div class="missing">该站点全文受限（付费/反爬），此处为可获取的摘要。</div>')
        body = a.get("html") or ""
        if not body:
            body = f"<p>{esc(a.get('summary',''))}</p>"
        parts.append(body)
        parts.append("</article>")

    parts.append("</body></html>")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("".join(parts), encoding="utf-8")
    return dest
