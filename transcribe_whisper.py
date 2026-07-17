#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper base 转写脚本
用法:
  python transcribe_whisper.py              # 自动找最新的Excel
  python transcribe_whisper.py 2026-07-15   # 指定日期
  python transcribe_whisper.py all          # 转写所有日期
"""
import re, sys, os
from pathlib import Path
from datetime import datetime
import pandas as pd

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

AUDIO_DIR = Path("output/audio")

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
    fname_base = f"{seq}_{caller}_{callee}_{call_time}"
    dt_dir = AUDIO_DIR / dt
    if dt_dir.exists():
        f = next(dt_dir.glob(f"{fname_base}.*"), None)
        if f:
            return f
        for f in dt_dir.glob(f"{seq}_*"):
            if caller in f.name and callee in f.name:
                return f
    return None

def transcribe_one(excel_path, output_path, date_override=None):
    df = pd.read_excel(excel_path)
    log(f"Excel: {excel_path.name} ({len(df)} 条)")

    if "转写模型" in df.columns and df["转写模型"].notna().any():
        existing = str(df["转写模型"].dropna().iloc[0])
        if "Whisper" in existing:
            log("  跳过 - 已有 Whisper 转写结果")
            return

    import whisper
    model = whisper.load_model("base", device="cpu")

    transcribed = 0
    texts = []
    for i, row in df.iterrows():
        caller = str(row.get("主叫", "")).strip()
        callee = str(row.get("被叫", "")).strip()
        dt = date_override if date_override else extract_date(row)
        call_time = str(row.get("通话时间", "")).replace(" ", "_").replace(":", "-")
        seq = str(row.get("序号", i+1)).zfill(4)

        audio_file = find_audio(seq, caller, callee, call_time, dt)
        if not audio_file and date_override:
            fb = extract_date(row)
            if fb != date_override:
                audio_file = find_audio(seq, caller, callee, call_time, fb)

        text = ""
        if audio_file and audio_file.stat().st_size > 1000:
            try:
                result = model.transcribe(str(audio_file), language="zh", fp16=False)
                text = (result.get("text") or "").strip()
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

    df["录音转写文字"] = texts
    df["转写模型"] = "Whisper base"
    with pd.ExcelWriter(output_path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="通话记录", index=False)
    log(f"  完成! 转写 {transcribed}/{len(df)} 条 -> {output_path.name}")

if __name__ == "__main__":
    arg = sys.argv[1].strip() if len(sys.argv) > 1 else ""

    if arg == "all" or arg == "":
        files = sorted(Path("output").glob("通话记录_*.xlsx"))
        files = [f for f in files if "_Whisper" not in f.name and "_FunASR" not in f.name and "_SenseVoice" not in f.name]
        if not files:
            print("找不到 Excel!"); sys.exit(1)
        log(f"找到 {len(files)} 个Excel文件")
        for fp in files:
            stem = fp.stem
            out = fp.parent / f"{stem}_Whisper_base.xlsx"
            dm = re.search(r'(\d{4}-\d{2}-\d{2})', stem)
            transcribe_one(fp, out, dm.group(1) if dm else None)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', arg):
        ep = Path(f"output/通话记录_{arg}.xlsx")
        op = Path(f"output/通话记录_{arg}_Whisper_base.xlsx")
        if not ep.exists(): print(f"找不到: {ep}"); sys.exit(1)
        transcribe_one(ep, op, arg)
    else:
        files = sorted(Path("output").glob("通话记录_*.xlsx"))
        files = [f for f in files if "_Whisper" not in f.name and "_FunASR" not in f.name and "_SenseVoice" not in f.name]
        if not files: print("找不到 Excel!"); sys.exit(1)
        ep = Path(files[-1])
        op = ep.parent / f"{ep.stem}_Whisper_base.xlsx"
        transcribe_one(ep, op)
