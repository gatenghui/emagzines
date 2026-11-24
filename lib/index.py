# -*- coding: utf-8 -*-
"""生成 library/INDEX.md 总索引。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def build_index(output_dir: Path, records: list[dict] | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    for meta_path in sorted(output_dir.glob("*/*/meta.json")):
        try:
            m = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        d = meta_path.parent
        files = m.get("files") or {}
        rows.append({
            "mag_id": m.get("mag_id", ""),
            "magazine": m.get("magazine", ""),
            "issue_date": m.get("issue_date", ""),
            "label": m.get("issue_label", ""),
            "count": m.get("count", 0),
            "fulltext": m.get("fulltext", 0),
            "dir": d,
            "epub": files.get("epub"),
            "pdf": files.get("pdf"),
            "md": files.get("md"),
            "generated": m.get("generated_at", ""),
        })

    # 本次刚生成的也补进来（meta 未开时）
    if records:
        have = {(r["mag_id"], r["issue_date"]) for r in rows}
        for r in records:
            if (r["mag_id"], r["issue_date"]) in have:
                continue
            rows.append({
                "mag_id": r["mag_id"], "magazine": r["name"],
                "issue_date": r["issue_date"], "label": r["issue_label"],
                "count": r["count"], "fulltext": r["fulltext"], "dir": r["dir"],
                "epub": r["epub"].name if r.get("epub") else None,
                "pdf": r["pdf"].name if r.get("pdf") else None,
                "md": r["md"].name if r.get("md") else None,
                "generated": datetime.now().isoformat(timespec="seconds"),
            })

    rows.sort(key=lambda x: (x["magazine"], x["issue_date"]), reverse=True)

    lines = [
        "# 本地期刊索引",
        "",
        f"最后更新：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')}　"
        f"｜ 共 {len(rows)} 期",
        "",
        "| 期刊 | 期号 | 篇数 | 全文 | PDF | Markdown | EPUB | 目录 |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]

    def rel(p, base: Path) -> str:
        if not p:
            return "×"
        try:
            return f"[{Path(p).name}]({Path(p).relative_to(base).as_posix()})"
        except Exception:
            return str(p)

    for r in rows:
        lines.append(
            f"| {r['magazine']} | {r['issue_date']}<br/>{r['label']} | {r['count']} | "
            f"{r['fulltext']} | {rel(r['epub'] and str(r['dir'] / r['epub']), output_dir)} | "
            f"{rel(r['md'] and str(r['dir'] / r['md']), output_dir)} | "
            f"{rel(r['pdf'] and str(r['dir'] / r['pdf']), output_dir)} | "
            f"{r['dir'].name} |"
        )

    lines += [
        "",
        "> 由 `main.py` 自动生成；重新生成索引：`python main.py --index`。",
        "",
    ]

    out = output_dir / "INDEX.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
