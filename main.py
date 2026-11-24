# -*- coding: utf-8 -*-
"""eMagzines 本地版：抓三种期刊最新一期 → 本地 EPUB / PDF / Markdown。

用法：
    python main.py                     # 抓三种期刊最新一期
    python main.py --only te           # 只抓 The Economist
    python main.py --only te,ny        # 抓两本
    python main.py --date 2026-11-28 --only te   # 指定期号（能取到就用）
    python main.py --no-pdf            # 只出 md + epub
    python main.py --index             # 只重建索引
    python main.py --list              # 看本地库里有什么
    python main.py --open              # 抓完自动打开产物目录
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from lib import log  # noqa: E402
from lib.config import load_config  # noqa: E402
from lib import http as http_mod  # noqa: E402
from lib import index as index_mod  # noqa: E402
from lib import pipeline  # noqa: E402
from lib import pdf as pdf_mod  # noqa: E402
from mags import FETCHERS  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="抓取 The Economist / The New Yorker / TIME 最新一期")
    p.add_argument("--only", default="", help="只抓指定期刊，逗号分隔：te,ny,time")
    p.add_argument("--date", default="", help="指定期号日期 YYYY-MM-DD（可选）")
    p.add_argument("--limit", type=int, default=0, help="每期最多收多少篇（覆盖配置）")
    p.add_argument("--no-pdf", action="store_true", help="不生成 PDF")
    p.add_argument("--no-epub", action="store_true", help="不生成 EPUB")
    p.add_argument("--no-md", action="store_true", help="不生成 Markdown")
    p.add_argument("--index", action="store_true", help="只重建 INDEX.md")
    p.add_argument("--list", action="store_true", dest="list_local", help="列出本地已抓内容")
    p.add_argument("--open", action="store_true", help="结束后打开产物目录")
    p.add_argument("--scheduled", action="store_true", help="定时任务模式（日志更安静）")
    p.add_argument("--config", default="", help="指定配置文件路径")
    return p.parse_args(argv)


def cmd_list(cfg) -> int:
    out = cfg.output_dir
    if not out.exists():
        print("本地库还是空的，先跑一次 python main.py")
        return 0
    rows = sorted([d for d in out.glob("*/*") if d.is_dir()])
    if not rows:
        print("本地库还是空的，先跑一次 python main.py")
        return 0
    print(f"{'期刊目录':<22}{'期号':<12}{'文件'}")
    print("-" * 72)
    for d in rows:
        files = [f.name for f in d.iterdir() if f.is_file() and f.suffix in (".pdf", ".epub", ".md")]
        size = sum(f.stat().st_size for f in d.iterdir() if f.is_file()) / 1048576
        print(f"{d.parent.name:<22}{d.name:<12}{len(files)} 个文件 / {size:.1f} MB")
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    cfg = load_config(args.config or (BASE / "config.yaml"))
    logger = log.setup(cfg.log_dir, quiet=args.scheduled)

    if args.list_local:
        return cmd_list(cfg)
    if args.index:
        p = index_mod.build_index(cfg.output_dir)
        print(f"索引已更新: {p}")
        return 0

    log.info("=" * 62)
    log.info("eMagzines 本地抓取开始 %s", __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    cal = pdf_mod.find_calibre()
    chrom = pdf_mod.find_chromium()
    log.info("PDF 引擎: %s", f"calibre ({cal})" if cal else f"浏览器打印 ({chrom or '未找到'})")
    log.info("产物目录: %s", cfg.output_dir)

    mags = [m.strip() for m in args.only.split(",") if m.strip()] or cfg.enabled_mags()
    unknown = [m for m in mags if m not in FETCHERS]
    if unknown:
        log.error("未知期刊 id: %s（可选 te / ny / time）", ", ".join(unknown))
        return 2

    limit = args.limit or cfg.max_articles
    want_pdf = not args.no_pdf
    want_epub = not args.no_epub
    want_md = not args.no_md

    records, failures = [], []
    for mag_id in mags:
        mcfg = cfg.mag(mag_id)
        if not mcfg.get("enabled", True):
            log.info("[%s] 配置里已禁用，跳过", mag_id)
            continue
        log.info("")
        log.info("── %s ─────────────────────────────", mcfg["name"])
        session = http_mod.make_session(cfg.cookie_path(mag_id), cfg.timeout, cfg.retries)
        try:
            issue = FETCHERS[mag_id](session, mcfg, limit=limit,
                                     date_override=args.date or None)
            if not issue.articles:
                raise RuntimeError("没有抓到任何文章")
            log.info("  期号: %s ｜ 文章: %d ｜ 全文: %d",
                     issue.issue_label, len(issue.articles),
                     sum(1 for a in issue.articles if not a.partial))
            for n in issue.notes:
                log.warn("  提示: %s", n)
            rec = pipeline.emit_issue(issue, cfg, session, want_pdf=want_pdf,
                                      want_epub=want_epub, want_md=want_md)
            records.append(rec)
            log.info("  完成 → %s", rec["dir"])
        except Exception as e:
            failures.append((mag_id, str(e)))
            log.error("  [%s] 抓取失败: %s", mag_id, e)
            if not cfg.best_effort:
                break

    # 索引
    try:
        idx = index_mod.build_index(cfg.output_dir, records)
        log.info("")
        log.info("索引: %s", idx)
    except Exception as e:
        log.warn("索引生成失败: %s", e)

    # 汇总
    log.info("")
    log.info("=" * 62)
    for r in records:
        log.info("✓ %-16s %s  文章 %2d  全文 %2d  → %s",
                 r["name"], r["issue_date"], r["count"], r["fulltext"], r["dir"])
    for mid, err in failures:
        log.info("× %-16s %s", mid, err)
    if not records and not failures:
        log.warn("什么都没生成")

    if args.open and records:
        try:
            webbrowser.open(cfg.output_dir.as_uri())
        except Exception:
            pass

    if failures and not cfg.best_effort:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
