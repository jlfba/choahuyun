#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日自动抓取 - 抓取前一天数据 → 转写 → 完成退出
用法: python daily_task.py
配合 cron 或 systemd 每天8点自动执行
"""
import os, sys, subprocess, re
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

WORK_DIR = Path(__file__).parent
MIN_TEXT_LENGTH = 20
# 系统语音关键词 → 直接删除
NOISE_KEYWORDS = [
    "语音留言", "转至语音", "已转至语音", "话已转至", "话已转",
    "提示音后录制", "录音完成后挂断", "无法接听", "无法接通",
    "录制留言", "未能识别", "转写失败", "音频未找到", "音频文件太小",
    "语音流", "一转",
]
# 真实对话关键词 → 包含这些才算有效通话
KEEP_KEYWORDS = ["喂", "你好", "哎"]
# 接通提示音前缀（去掉，但保留后面的内容）
STRIP_PREFIXES = [
    "电话正在接通中，请稍后。", "电话正在接通中，请稍后",
    "电话正在接通中，", "电话正在接通中。",
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def clean_data(date_str):
    """清洗数据：清理标签 + 删除不符合条件的行"""
    excel_path = WORK_DIR / "output" / f"通话记录_{date_str}_SenseVoice.xlsx"
    if not excel_path.exists():
        excel_path = WORK_DIR / "output" / f"通话记录_{date_str}.xlsx"
    if not excel_path.exists():
        log(f"[SKIP] 找不到 {date_str} 的Excel")
        return

    df = pd.read_excel(excel_path)
    before = len(df)

    # 1. 清理转写文字中的SenseVoice标签 + 去掉接通提示音前缀
    def clean_text(text):
        if not text or pd.isna(text):
            return ""
        text = str(text)
        text = re.sub(r'<\s*\|[^|]*\|\s*>', '', text)  # <|zh|> <|NEUTRAL|> 等
        # 去掉接通提示音前缀
        for prefix in STRIP_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    df["录音转写文字"] = df["录音转写文字"].apply(clean_text)

    # 2. 过滤：字数<20 或 仍有标签残留 或 无意义内容的删除
    def should_keep(text):
        if not text or pd.isna(text):
            return False
        text = str(text).strip()
        # 还有标签残留
        if '<|' in text or '|>' in text:
            return False
        # 包含系统语音关键词 → 直接删除
        if any(kw in text for kw in NOISE_KEYWORDS):
            return False
        # 不包含真实对话关键词 → 删除
        if not any(kw in text for kw in KEEP_KEYWORDS):
            return False
        # 字数不足
        if len(text) < MIN_TEXT_LENGTH:
            return False
        return True

    df["keep"] = df["录音转写文字"].apply(should_keep)
    df = df[df["keep"]].drop(columns=["keep"])
    df = df.reset_index(drop=True)
    df["序号"] = range(1, len(df) + 1)

    after = len(df)
    log(f"[CLEAN] {date_str}: {before} → {after} 条 (删除 {before - after} 条)")

    with pd.ExcelWriter(excel_path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="通话记录", index=False)

def main():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    excel_path = WORK_DIR / "output" / f"通话记录_{yesterday}.xlsx"

    # 已有数据就跳过
    if excel_path.exists() and excel_path.stat().st_size > 1000:
        log(f"[SKIP] {yesterday} 数据已存在，跳过")
        return

    log("=" * 50)
    log(f"开始处理 {yesterday} 的数据")
    log("=" * 50)

    # 1. 抓取
    log("[1/2] 抓取数据...")
    result = subprocess.run(
        [sys.executable, str(WORK_DIR / "auto_scrape.py"), yesterday],
        cwd=str(WORK_DIR), capture_output=True, text=True, timeout=1800,
    )
    if result.returncode != 0:
        log(f"[ERR] 抓取失败: {result.stderr[-300:]}")
        return
    log("[OK] 抓取完成")

    # 2. 转写
    log("[2/2] 语音转写...")
    result = subprocess.run(
        [sys.executable, str(WORK_DIR / "transcribe_sensevoice.py"), yesterday],
        cwd=str(WORK_DIR), capture_output=True, text=True, timeout=3600,
    )
    if result.returncode != 0:
        log(f"[ERR] 转写失败: {result.stderr[-300:]}")
        return
    log("[OK] 转写完成")

    # 3. 清洗数据
    log("[3/3] 清洗数据...")
    clean_data(yesterday)

    # 4. 完成
    log("=" * 50)
    log(f"{yesterday} 数据处理完成!")
    log(f"Excel: output/通话记录_{yesterday}_SenseVoice.xlsx")
    log(f"音频: output/audio/{yesterday}/")
    log("=" * 50)

if __name__ == "__main__":
    main()
