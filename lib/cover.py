# -*- coding: utf-8 -*-
"""封面：优先用真实封面图，抓不到就用 PIL 生成一张杂志风封面。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import log

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\georgiab.ttf",
    r"C:\Windows\Fonts\timesbd.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\seguibl.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
]
FONT_SANS = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for p in (FONT_CANDIDATES if bold else FONT_SANS):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size)
    except Exception:
        return ImageFont.load_default()


def _hex(color: str, default=(20, 20, 20)) -> tuple[int, int, int]:
    c = (color or "").lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    try:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except Exception:
        return default


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def generate_cover(dest: Path, magazine: str, issue_label: str, brand_color: str = "#E3120B",
                   size=(1200, 1600)) -> Path:
    """生成一张纯排版封面（无网络依赖）。"""
    W, H = size
    bg = _hex(brand_color)
    # 深色品牌色（黑）时用浅色底，避免全黑看不出字
    dark = sum(bg) < 160
    bg = (250, 248, 244) if dark else bg
    fg = bg if not dark else _hex(brand_color)
    if not dark:
        fg = (255, 255, 255)
    else:
        fg = tuple(max(0, 255 - v) for v in bg)

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    margin = int(W * 0.09)
    # 顶部细线
    d.rectangle([margin, margin, W - margin, margin + 6], fill=fg)

    f_mast = _font(int(H * 0.085))
    f_sub = _font(int(H * 0.030))
    f_date = _font(int(H * 0.036))
    f_note = _font(int(H * 0.022), bold=False)

    # 刊名（自动换行）
    mast_lines = _wrap(d, magazine.upper(), f_mast, W - 2 * margin)
    y = int(H * 0.14)
    for ln in mast_lines:
        d.text((margin, y), ln, font=f_mast, fill=fg)
        y += int(f_mast.size * 1.12)

    y += int(H * 0.02)
    d.rectangle([margin, y, W - margin, y + 4], fill=fg)
    y += int(H * 0.05)

    # 期号
    for ln in _wrap(d, issue_label, f_date, W - 2 * margin):
        d.text((margin, y), ln, font=f_date, fill=fg)
        y += int(f_date.size * 1.35)

    # 底部说明
    d.text((margin, H - margin - int(H * 0.035)),
           "Local archive copy · for personal reading",
           font=f_note, fill=fg)

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=90)
    log.debug("生成封面 %s", dest)
    return dest


def download_cover(session, url: str, dest: Path) -> Path | None:
    if not url:
        return None
    try:
        r = session.get(url, timeout=30)
        if r.status_code != 200 or len(r.content) < 2000:
            return None
        tmp = dest.with_suffix(".src")
        tmp.write_bytes(r.content)
        img = Image.open(tmp)
        img = img.convert("RGB")
        # 统一封面比例
        img.thumbnail((1400, 1400))
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, "JPEG", quality=88)
        tmp.unlink(missing_ok=True)
        return dest
    except Exception as e:
        log.debug("封面下载失败 %s: %s", url, e)
        return None
