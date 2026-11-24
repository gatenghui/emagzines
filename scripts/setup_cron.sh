#!/usr/bin/env bash
# 设置每天自动抓取（Linux / macOS 的 cron）
# 用法：bash scripts/setup_cron.sh [HH:MM]
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIME="${1:-08:30}"
HOUR="${TIME%%:*}"
MIN="${TIME##*:}"
LOG="$ROOT/logs/cron.log"
mkdir -p "$ROOT/logs"

LINE="$MIN $HOUR * * * cd '$ROOT' && $(command -v python3 || command -v python) main.py --scheduled >> '$LOG' 2>&1"

# 去掉旧的同名任务
crontab -l 2>/dev/null | grep -v "eMagzines" > /tmp/emagzines_cron.$$ || true
echo "$LINE # eMagzines" >> /tmp/emagzines_cron.$$
crontab /tmp/emagzines_cron.$$
rm -f /tmp/emagzines_cron.$$

echo "[OK] cron 已设置：每天 $TIME"
echo "     $LINE"
echo "     查看：bash scripts/view_cron.sh"
echo "     删除：bash scripts/remove_cron.sh"
