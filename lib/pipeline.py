# -*- coding: utf-8 -*-
"""把一期内容落盘：cover / md / articles / epub / pdf / meta.json。"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from . import cover as cover_mod
from . import epub as epub_mod
from . import log
from . import pdf as pdf_mod
from .config import Config
from .textutil import slugify

MAG_AUTHOR = "Local eMagzines"


def anchor(index: int, title: str) -> str:
    """Markdown 内部锚点：序号 + 标题 slug，保证不重名。"""
    return f"{index}-{slugify(title, 45)}"


def _kb(p: Path | None) -> str:
    if not p or not Path(p).exists():
        return "-"
    n = Path(p).stat().st_size
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1048576:.1f} MB"


def build_markdown(issue) -> str:
    lines: list[str] = []
    full = sum(1 for a in issue.articles if not a.partial)
    lines.append("---")
    lines.append(f"title: \"{issue.name} — {issue.issue_label}\"")
    lines.append(f"magazine: \"{issue.name}\"")
    lines.append(f"mag_id: {issue.mag_id}")
    lines.append(f"issue_date: {issue.issue_date}")
    lines.append(f"issue_label: \"{issue.issue_label}\"")
    lines.append(f"generated: \"{datetime.now().astimezone().isoformat(timespec='seconds')}\"")
    lines.append(f"article_count: {len(issue.articles)}")
    lines.append(f"fulltext_count: {full}")
    lines.append(f"source: \"{issue.source}\"")
    lines.append("---")
    lines.append("")
    lines.append(f"# {issue.name} — {issue.issue_label}")
    lines.append("")
    lines.append(f"> 期号日期：`{issue.issue_date}` ｜ 收录 {len(issue.articles)} 篇"
                 f"（全文 {full} / 摘要 {len(issue.articles) - full}）")
    if issue.notes:
        for n in issue.notes:
            lines.append(f"> - {n}")
    lines.append("")
    lines.append("## 目录")
    lines.append("")
    for i, a in enumerate(issue.articles, 1):
        sec = f" · {a.section}" if a.section else ""
        tag = "（摘要）" if a.partial else ""
        lines.append(f"{i}. [{a.title}](#{anchor(i, a.title)}){sec}{tag}")
    lines.append("")
    lines.append("---")
    lines.append("")
    for i, a in enumerate(issue.articles, 1):
        lines.append(f'<a id="{anchor(i, a.title)}"></a>')
        lines.append("")
        lines.append(f"## {i}. {a.title}")
        lines.append("")
        meta = []
        if a.section:
            meta.append(f"**{a.section}**")
        if a.byline:
            meta.append(f"*{a.byline}*")
        if a.published:
            meta.append(a.published)
        meta.append(f"[原文]({a.url})")
        lines.append(" · ".join(meta))
        lines.append("")
        if a.partial:
            lines.append("> ⚠️ 该篇只能取到摘要（站点付费墙 / 反爬）。")
            lines.append("")
        body = (a.md or a.summary or "").strip()
        lines.append(body if body else "_（本篇正文为空）_")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def emit_issue(issue, cfg: Config, session, *, want_pdf=True, want_epub=True,
               want_md=True) -> dict:
    out_root = cfg.output_dir
    target = out_root / issue.folder / issue.issue_date
    if target.exists():
        # 保留旧文件，除非本次重新生成
        log.info("  → 目标目录已存在，重新生成: %s", target)
    target.mkdir(parents=True, exist_ok=True)

    stem = f"{issue.folder}-{issue.issue_date}"

    # ---- 封面 ----
    cover_path = target / "cover.jpg"
    got = None
    cover_mode = issue.cover_mode or "page"
    if issue.cover_url and cover_mode != "generated":
        got = cover_mod.download_cover(session, issue.cover_url, cover_path)
    if not got:
        cover_mod.generate_cover(cover_path, issue.name, issue.issue_label, issue.brand_color)
    log.info("  封面: %s", cover_path.name)

    # ---- Markdown ----
    md_path = None
    if want_md:
        md_path = target / f"{stem}.md"
        md_path.write_text(build_markdown(issue), encoding="utf-8")
        log.info("  Markdown: %s (%s)", md_path.name, _kb(md_path))
        if cfg.per_article_md:
            adir = target / "articles"
            if adir.exists():
                shutil.rmtree(adir, ignore_errors=True)
            adir.mkdir(parents=True, exist_ok=True)
            for i, a in enumerate(issue.articles, 1):
                fn = f"{i:02d}-{slugify(a.title, 50)}.md"
                head = (f"---\ntitle: \"{a.title}\"\nsection: \"{a.section}\"\n"
                        f"byline: \"{a.byline}\"\nurl: {a.url}\npartial: {str(a.partial).lower()}\n---\n\n"
                        f"# {a.title}\n\n")
                (adir / fn).write_text(head + (a.md or a.summary or ""), encoding="utf-8")

    # ---- EPUB ----
    epub_path = None
    if want_epub:
        epub_path = target / f"{stem}.epub"
        arts = []
        for a in issue.articles:
            head = (f'<h1 class="art">{_esc(a.title)}</h1>'
                    f'<p class="meta">{_esc(" · ".join([x for x in (a.section, a.byline, a.url) if x]))}</p>')
            body = a.html or f"<p>{_esc(a.summary)}</p>"
            if a.partial:
                body = '<p class="meta">（站点限制，本篇为摘要）</p>' + body
            arts.append({"title": a.title, "html": head + body})
        epub_mod.build_epub(epub_path, f"{issue.name} — {issue.issue_label}", MAG_AUTHOR,
                            issue.issue_label, arts, cover_jpg=cover_path)
        log.info("  EPUB: %s (%s)", epub_path.name, _kb(epub_path))

    # ---- PDF ----
    pdf_path = None
    if want_pdf:
        pdf_path = target / f"{stem}.pdf"
        html_path = target / f"{stem}.print.html"
        arts = [{
            "title": a.title, "section": a.section, "byline": a.byline, "url": a.url,
            "html": a.html, "summary": a.summary, "partial": a.partial,
        } for a in issue.articles]
        note = f"{len(issue.articles)} articles · {issue.issue_date}"
        pdf_mod.build_print_html(html_path, masthead=issue.name, issue_label=issue.issue_label,
                                 cover=cover_path, articles=arts, note=note)
        ok, engine = pdf_mod.render_pdf(html_path, pdf_path, cfg.pdf_engine, epub_path)
        if ok:
            log.info("  PDF: %s (%s) via %s", pdf_path.name, _kb(pdf_path), engine)
            html_path.unlink(missing_ok=True)
        else:
            log.error("  PDF 生成失败（打印用 HTML 保留在 %s）", html_path.name)

    # ---- meta ----
    meta = {
        "mag_id": issue.mag_id,
        "magazine": issue.name,
        "issue_date": issue.issue_date,
        "issue_label": issue.issue_label,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": issue.source,
        "cover_url": issue.cover_url,
        "notes": issue.notes,
        "count": len(issue.articles),
        "fulltext": sum(1 for a in issue.articles if not a.partial),
        "files": {
            "epub": epub_path.name if epub_path and epub_path.exists() else None,
            "pdf": pdf_path.name if pdf_path and pdf_path.exists() else None,
            "md": md_path.name if md_path and md_path.exists() else None,
            "cover": cover_path.name if cover_path.exists() else None,
        },
        "articles": [{
            "title": a.title, "url": a.url, "section": a.section, "byline": a.byline,
            "partial": a.partial, "words": a.words,
        } for a in issue.articles],
    }
    if cfg.write_meta:
        (target / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "mag_id": issue.mag_id,
        "name": issue.name,
        "folder": issue.folder,
        "issue_date": issue.issue_date,
        "issue_label": issue.issue_label,
        "dir": target,
        "count": len(issue.articles),
        "fulltext": meta["fulltext"],
        "epub": epub_path,
        "pdf": pdf_path,
        "md": md_path,
        "cover": cover_path,
    }


def _esc(s: str) -> str:
    import html
    return html.escape(s or "", quote=False)
