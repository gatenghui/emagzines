#!/usr/bin/env bash
# 查看 cron 定时任务 + 最近抓取结果
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "=== cron 中的 eMagzines 任务 ==="
crontab -l 2>/dev/null | grep "eMagzines" || echo "（未设置）"
echo
echo "=== 本地库最近一期 ==="
if [ -d "$ROOT/library" ]; then
  for d in "$ROOT/library"/*/; do
    [ -d "$d" ] || continue
    latest=$(ls -1 "$d" 2>/dev/null | sort -r | head -1)
    [ -n "$latest" ] && echo "$(basename "$d")  $latest  $(ls -1 "$d$latest" | wc -l) 个文件"
  done
else
  echo "（library 目录还不存在）"
fi
echo
echo "=== 最近日志 ==="
LOG=$(ls -1t "$ROOT"/logs/emagzines-*.log 2>/dev/null | head -1)
[ -n "$LOG" ] && tail -n 20 "$LOG" || echo "（还没有日志）"
