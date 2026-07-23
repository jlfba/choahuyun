#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量按日期范围抓取 - 依次抓取指定日期范围内的每一天数据
流程（每日）: 抓取 -> 转写 -> 清洗数据 -> 清理重复音频

用法:
  python batch_scrape.py 2026-07-10 2026-07-22
  python batch_scrape.py 2026-07-10 2026-07-22 --skip-transcribe
  python batch_scrape.py 2026-07-10 2026-07-22 --force   # 忽略已存在数据，强制重新抓取
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

WORK_DIR = Path(__file__).parent

# 子进程统一使用 UTF-8 编码，避免 Windows GBK 解码报错
SUBPROCESS_ENV = os.environ.copy()
SUBPROCESS_ENV['PYTHONIOENCODING'] = 'utf-8'


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def _run(cmd, timeout):
    """运行子进程，用 UTF-8 解码输出，避免 GBK 报错。"""
    proc = subprocess.run(
        cmd, cwd=str(WORK_DIR), capture_output=True, timeout=timeout,
        env=SUBPROCESS_ENV,
    )
    stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ""
    stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ""
    return proc.returncode, stdout, stderr


def run_day(date_str, force=False, skip_transcribe=False):
    """处理单日: 抓取 -> 转写 -> 清洗 -> 清理音频"""
    from daily_task import clean_data

    excel_path = WORK_DIR / "output" / f"通话记录_{date_str}.xlsx"
    sensevoice_path = WORK_DIR / "output" / f"通话记录_{date_str}_SenseVoice.xlsx"

    if not force and sensevoice_path.exists() and sensevoice_path.stat().st_size > 1000:
        log(f"[SKIP] {date_str} 已有转写结果，跳过")
        return "skipped"

    if not force and excel_path.exists() and excel_path.stat().st_size > 1000 and skip_transcribe:
        log(f"[SKIP] {date_str} 已有抓取数据，跳过")
        return "scraped_only_skipped"

    log("-" * 50)
    log(f"开始处理 {date_str}")
    log("-" * 50)

    # 1. 抓取
    log("[1/4] 抓取数据...")
    code, stdout, stderr = _run(
        [sys.executable, str(WORK_DIR / "auto_scrape.py"), date_str], 3600)
    if code != 0:
        log(f"[ERR] 抓取失败: {stderr[-400:]}")
        return "scrape_failed"
    log("[OK] 抓取完成")
    if stdout:
        log(stdout[-400:])

    if skip_transcribe:
        log("[SKIP] 跳过转写")
        return "scraped_only"

    # 2. 转写
    log("[2/4] 语音转写...")
    code, stdout, stderr = _run(
        [sys.executable, str(WORK_DIR / "transcribe_sensevoice.py"), date_str], 7200)
    if code != 0:
        log(f"[ERR] 转写失败: {stderr[-400:]}")
        return "transcribe_failed"
    log("[OK] 转写完成")

    # 3. 清洗数据
    log("[3/4] 清洗数据...")
    clean_data(date_str)

    # 4. 清理重复音频
    log("[4/4] 清理重复音频...")
    try:
        code, stdout, stderr = _run(
            [sys.executable, str(WORK_DIR / "clean_audio.py"), date_str], 600)
        if code == 0:
            log("[OK] 音频清理完成")
        else:
            log(f"[WARN] 音频清理异常: {stderr[-200:]}")
    except Exception as e:
        log(f"[WARN] 音频清理异常: {e}")

    return "done"


def main():
    args = sys.argv[1:]
    force = "--force" in args
    skip_transcribe = "--skip-transcribe" in args
    date_args = [a for a in args if not a.startswith("--")]

    if len(date_args) < 1:
        print("用法: python batch_scrape.py <开始日期> [结束日期] [--force] [--skip-transcribe]")
        print("示例: python batch_scrape.py 2026-07-10 2026-07-22")
        sys.exit(1)

    start_str = date_args[0]
    end_str = date_args[1] if len(date_args) > 1 else start_str

    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_str, "%Y-%m-%d")
    except ValueError:
        print("日期格式错误，请使用 YYYY-MM-DD")
        sys.exit(1)

    if start_date > end_date:
        print("开始日期不能晚于结束日期")
        sys.exit(1)

    dates = []
    cur = start_date
    while cur <= end_date:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)

    log("=" * 60)
    log(f"批量抓取: {start_str} ~ {end_str} (共 {len(dates)} 天)")
    if force:
        log("模式: 强制重新抓取")
    if skip_transcribe:
        log("模式: 跳过转写，仅抓取与下载")
    log("=" * 60)

    results = {}
    for i, d in enumerate(dates, 1):
        log(f"\n[{i}/{len(dates)}] 处理 {d}")
        results[d] = run_day(d, force=force, skip_transcribe=skip_transcribe)

    # 汇总
    log("\n" + "=" * 60)
    log("批量抓取汇总")
    log("=" * 60)
    for d, r in results.items():
        log(f"  {d}: {r}")

    done = sum(1 for r in results.values() if r == "done")
    scraped = sum(1 for r in results.values() if r == "scraped_only")
    skipped = sum(1 for r in results.values() if "skipped" in r)
    failed = sum(1 for r in results.values() if "failed" in r)
    log(f"  完成: {done}  仅抓取: {scraped}  跳过: {skipped}  失败: {failed}")
    log("=" * 60)


if __name__ == "__main__":
    main()
