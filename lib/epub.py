# -*- coding: utf-8 -*-
"""极简 EPUB3 生成器：只依赖标准库 zipfile，不装任何额外包。"""
from __future__ import annotations

import html
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

CSS = """
body { font-family: Georgia, "Times New Roman", serif; line-height: 1.6; margin: 0 4%; }
h1.art { font-size: 1.5em; line-height: 1.25; margin: 1.4em 0 .3em; }
p.meta { color: #666; font-size: .85em; margin: 0 0 1em; }
p { margin: 0 0 .8em; text-align: justify; }
h2 { font-size: 1.15em; margin: 1.2em 0 .4em; }
h3 { font-size: 1.02em; margin: 1em 0 .3em; }
blockquote { margin: 1em 0 1em 1em; padding-left: .8em; border-left: 3px solid #ccc; color: #444; }
figure { margin: 1em 0; }
figcaption { font-size: .82em; color: #666; }
img { max-width: 100%; }
hr { border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }
.cover { text-align: center; margin: 0; padding: 0; }
.cover img { max-width: 100%; height: auto; }
nav ol { list-style: none; padding-left: 0; }
"""


def _esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def _xhtml(title: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
        'lang="en" xml:lang="en">\n<head>\n'
        f'<title>{_esc(title)}</title>\n'
        '<link rel="stylesheet" type="text/css" href="style.css"/>\n'
        '</head>\n<body>\n' + body + '\n</body>\n</html>\n'
    )


def build_epub(dest: Path, title: str, author: str, issue_label: str,
               articles: list[dict], cover_jpg: Path | None = None,
               language: str = "en") -> Path:
    """articles: [{title, section, byline, url, md, html}]"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    book_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"{title}|{issue_label}|{len(articles)}"))
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    files: list[tuple[str, str]] = []      # (id, href)
    manifest: list[str] = []
    spine: list[str] = []

    manifest.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
    manifest.append('<item id="css" href="style.css" media-type="text/css"/>')

    # 封面
    cover_page = None
    if cover_jpg and Path(cover_jpg).exists():
        manifest.append('<item id="cover-img" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>')
        manifest.append('<item id="coverpage" href="cover.xhtml" media-type="application/xhtml+xml"/>')
        spine.append('<itemref idref="coverpage"/>')
        cover_page = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            'lang="en" xml:lang="en">\n<head><title>Cover</title>'
            '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
            '<body><div class="cover"><img src="cover.jpg" alt="cover"/></div></body></html>\n'
        )

    # 目录页
    toc_items = []
    for i, a in enumerate(articles, 1):
        hid = f"a{i:03d}"
        href = f"{hid}.xhtml"
        manifest.append(f'<item id="{hid}" href="{href}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="{hid}"/>')
        toc_items.append(f'<li><a href="{href}">{_esc(a["title"])}</a></li>')
        files.append((href, a["html"]))

    nav_body = (
        f'<nav epub:type="toc" id="toc"><h1>{_esc(issue_label)}</h1><ol>' +
        "".join(toc_items) + '</ol></nav>\n' +
        f'<nav epub:type="landmarks" hidden="hidden"><ol>'
        f'<li><a epub:type="bodymatter" href="a001.xhtml">Start</a></li></ol></nav>'
    ) if articles else f'<nav epub:type="toc"><h1>{_esc(issue_label)}</h1><ol></ol></nav>'

    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="en">\n'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f'<dc:identifier id="bookid">{book_id}</dc:identifier>\n'
        f'<dc:title>{_esc(title)}</dc:title>\n'
        f'<dc:creator>{_esc(author)}</dc:creator>\n'
        f'<dc:language>{language}</dc:language>\n'
        f'<dc:description>{_esc(issue_label)}</dc:description>\n'
        f'<meta property="dcterms:modified">{modified}</meta>\n'
        '</metadata>\n<manifest>\n' + "\n".join(manifest) + '\n</manifest>\n'
        '<spine>\n' + "\n".join(spine) + '\n</spine>\n</package>\n'
    )

    container = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
        '</rootfiles></container>\n'
    )

    tmp = dest.with_suffix(".epub.tmp")
    with zipfile.ZipFile(tmp, "w") as z:
        # mimetype 必须第一个且不压缩
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", _xhtml(issue_label, nav_body), zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", CSS, zipfile.ZIP_DEFLATED)
        if cover_page:
            z.writestr("OEBPS/cover.xhtml", cover_page, zipfile.ZIP_DEFLATED)
            z.write(cover_jpg, "OEBPS/cover.jpg", zipfile.ZIP_STORED)
        for href, body in files:
            z.writestr(f"OEBPS/{href}", _xhtml(title, body), zipfile.ZIP_DEFLATED)

    tmp.replace(dest)
    return dest
