#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时抓取调度器 - 每天自动抓取前一天的数据并转写
用法: python scheduler.py
"""
import os, sys, time, subprocess, schedule
from pathlib import Path
from datetime import datetime, timedelta

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

WORK_DIR = Path(__file__).parent

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def job():
    """抓取前一天数据 + 转写 + 清洗"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    excel_path = WORK_DIR / "output" / f"通话记录_{yesterday}.xlsx"

    # 已有数据就跳过
    if excel_path.exists() and excel_path.stat().st_size > 1000:
        log(f"[SKIP] {yesterday} 数据已存在，跳过")
        return

    log("=" * 40)
    log(f"[START] 开始处理 {yesterday} 的数据...")

    try:
        result = subprocess.run(
            [sys.executable, str(WORK_DIR / "daily_task.py")],
            cwd=str(WORK_DIR),
            capture_output=True, text=True, timeout=7200,
        )
        if result.returncode == 0:
            log(f"[OK] {yesterday} 处理完成")
            log(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        else:
            log(f"[ERR] 处理失败: {result.stderr[-300:]}")
    except Exception as e:
        log(f"[ERR] 异常: {e}")

    log("=" * 40)

if __name__ == "__main__":
    log("=" * 50)
    log("超呼云 - 每日自动抓取调度器")
    log("规则: 每天自动抓取前一天的数据并转写")
    log("=" * 50)

    # 启动时先执行一次
    job()

    # 每天早上8点执行
    schedule.every().day.at("08:00").do(job)

    log("调度器已启动，每天 08:00 自动执行")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        log("调度器已停止")
