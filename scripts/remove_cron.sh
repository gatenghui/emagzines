#!/usr/bin/env bash
# 删除 cron 里的 eMagzines 任务
set -e
crontab -l 2>/dev/null | grep -v "eMagzines" > /tmp/emagzines_cron.$$ || true
crontab /tmp/emagzines_cron.$$
rm -f /tmp/emagzines_cron.$$
echo "[OK] 已删除 cron 中的 eMagzines 任务"
