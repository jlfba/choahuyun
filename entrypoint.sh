#!/bin/bash
set -e

case "${1:-web}" in
  web)
    echo "启动网页服务..."
    exec python web/backend/main.py
    ;;
  scheduler)
    echo "启动定时抓取调度器..."
    exec python scheduler.py
    ;;
  scrape)
    echo "执行一次性抓取: ${2:-全部}"
    exec python auto_scrape.py "$2"
    ;;
  daily)
    echo "执行每日任务..."
    exec python daily_task.py
    ;;
  *)
    echo "用法:"
    echo "  web         # 启动网页（默认）"
    echo "  scheduler   # 启动定时抓取"
    echo "  scrape      # 一次性抓取全部"
    echo "  scrape 2026-07-15  # 抓指定日期"
    echo "  daily       # 执行每日任务"
    ;;
esac
