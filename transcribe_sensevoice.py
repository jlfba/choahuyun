#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SenseVoice 转写脚本 - 用已下载的音频+已有Excel，只做转写回填
用法:
  python transcribe_sensevoice.py              # 自动找最新的Excel
  python transcribe_sensevoice.py 2026-07-15   # 指定日期
  python transcribe_sensevoice.py all          # 转写所有日期
"""
import re, sys, os
from pathlib import Path
from datetime import datetime
import pandas as pd

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

AUDIO_DIR = Path("output/audio")

# 简繁转换
try:
    from opencc import OpenCC
    cc = OpenCC('t2s')
    HAVE_OPENCC = True
except ImportError:
    HAVE_OPENCC = False

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def to_simplified(text):
    if HAVE_OPENCC and text:
        return cc.convert(text)
    return text

def extract_date(row):
    for key in ["接通时间", "拨号时间"]:
        v = str(row.get(key, "")).strip()
        m = re.search(r'(\d{4}-\d{2}-\d{2})', v)
        if m:
            return m.group(1)
    return datetime.now().strftime('%Y-%m-%d')

def find_audio(seq, caller, callee, call_time, dt):
    """在日期文件夹里找音频文件"""
    fname_base = f"{seq}_{caller}_{callee}_{call_time}"
    dt_dir = AUDIO_DIR / dt
    if dt_dir.exists():
        f = next(dt_dir.glob(f"{fname_base}.*"), None)
        if f:
            return f
        # 模糊匹配
        for f in dt_dir.glob(f"{seq}_*"):
            if caller in f.name and callee in f.name:
                return f
    return None

def transcribe_one(excel_path, output_path, date_override=None):
    """转写一个Excel文件"""
    df = pd.read_excel(excel_path)
    log(f"Excel: {excel_path.name} ({len(df)} 条)")

    # 检查是否已有转写结果（避免重复转写）
    if "录音转写文字" in df.columns and df["录音转写文字"].notna().any():
        non_empty = df["录音转写文字"].dropna()
        non_empty = non_empty[non_empty.astype(str).str.strip() != ""]
        if len(non_empty) > 0:
            log("  跳过 - 已有转写结果")
            return

    # 加载模型（只加载一次，函数外管理）
    from funasr import AutoModel
    model = AutoModel(
        model="iic/SenseVoiceSmall",
        vad_model="fsmn-vad",
        punc_model="ct-punc",
        device="cpu",
    )

    transcribed = 0
    texts = []

    for i, row in df.iterrows():
        caller = str(row.get("主叫", "")).strip()
        callee = str(row.get("被叫", "")).strip()
        dt = date_override if date_override else extract_date(row)

        call_time = str(row.get("通话时间", "")).replace(" ", "_").replace(":", "-")
        seq = str(row.get("序号", i+1)).zfill(4)

        audio_file = find_audio(seq, caller, callee, call_time, dt)
        # 指定日期找不到，再从原始日期找
        if not audio_file and date_override:
            fallback_dt = extract_date(row)
            if fallback_dt != date_override:
                audio_file = find_audio(seq, caller, callee, call_time, fallback_dt)

        text = ""
        if audio_file and audio_file.stat().st_size > 1000:
            try:
                result = model.generate(input=str(audio_file))
                if result and len(result) > 0:
                    raw = result[0].get("text", "").strip()
                    text = re.sub(r'<\s*\|[^|]*\|\s*>', '', raw).strip()
                    text = re.sub(r'\s+', ' ', text).strip()
                if not text:
                    text = "(未能识别)"
                text = to_simplified(text)
                transcribed += 1
            except Exception as e:
                log(f"  [X] {audio_file.name}: {e}")
                text = "(转写失败)"

        texts.append(text)
        if (i + 1) % 20 == 0:
            log(f"  进度: {i+1}/{len(df)}, 已转写{transcribed}")

    # 回填Excel
    df["录音转写文字"] = texts
    with pd.ExcelWriter(output_path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="通话记录", index=False)

    log(f"  完成! 转写 {transcribed}/{len(df)} 条 -> {output_path.name}")

if __name__ == "__main__":
    arg = sys.argv[1].strip() if len(sys.argv) > 1 else ""

    # 加载模型（所有文件共享）
    log("加载 SenseVoice...")
    from funasr import AutoModel
    model = AutoModel(
        model="iic/SenseVoiceSmall",
        vad_model="fsmn-vad",
        punc_model="ct-punc",
        device="cpu",
    )
    log("SenseVoice 模型加载完成")

    if arg == "all" or arg == "":
        # 转写所有日期的Excel
        files = sorted(Path("output").glob("通话记录_*.xlsx"))
        files = [f for f in files if "_Whisper" not in f.name and "_FunASR" not in f.name and "_SenseVoice" not in f.name]
        if not files:
            print("找不到 Excel 文件!")
            sys.exit(1)
        log(f"找到 {len(files)} 个Excel文件待转写")
        for excel_path in files:
            stem = excel_path.stem
            output_path = excel_path.parent / f"{stem}_SenseVoice.xlsx"
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', stem)
            date_override = date_match.group(1) if date_match else None
            transcribe_one(excel_path, output_path, date_override)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', arg):
        # 指定日期
        excel_path = Path(f"output/通话记录_{arg}.xlsx")
        output_path = Path(f"output/通话记录_{arg}_SenseVoice.xlsx")
        if not excel_path.exists():
            print(f"找不到: {excel_path}")
            sys.exit(1)
        transcribe_one(excel_path, output_path, arg)
    else:
        # 自动找最新的
        files = sorted(Path("output").glob("通话记录_*.xlsx"))
        files = [f for f in files if "_Whisper" not in f.name and "_FunASR" not in f.name and "_SenseVoice" not in f.name]
        if not files:
            print("找不到 Excel 文件!")
            sys.exit(1)
        excel_path = Path(files[-1])
        stem = excel_path.stem
        output_path = excel_path.parent / f"{stem}_SenseVoice.xlsx"
        transcribe_one(excel_path, output_path)
