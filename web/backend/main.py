#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通话记录展示 - FastAPI 后端
"""
import re, os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI(title="通话记录展示")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
AUDIO_DIR = OUTPUT_DIR / "audio"

@app.get("/api/dates")
def get_dates():
    """返回所有可用日期"""
    dates = []
    for f in sorted(OUTPUT_DIR.glob("通话记录_2026-*.xlsx")):
        m = re.search(r'(\d{4}-\d{2}-\d{2})', f.name)
        if m:
            d = m.group(1)
            df = pd.read_excel(f, sheet_name="通话记录")
            has_sensevoice = "_SenseVoice" in f.name
            dates.append({
                "date": d,
                "file": f.name,
                "count": len(df),
                "model": "SenseVoice" if has_sensevoice else "",
            })
    return dates

@app.get("/api/records")
def get_records(date: str = Query("", description="日期筛选")):
    """返回通话记录"""
    if date:
        excel_path = OUTPUT_DIR / f"通话记录_{date}.xlsx"
        if not excel_path.exists():
            # 尝试找带模型名的
            for f in OUTPUT_DIR.glob(f"通话记录_{date}*.xlsx"):
                excel_path = f
                break
    else:
        # 找最新的
        files = sorted(OUTPUT_DIR.glob("通话记录_2026-*.xlsx"))
        files = [f for f in files if "_Whisper" not in f.name and "_FunASR" not in f.name and "_SenseVoice" not in f.name]
        if not files:
            return []
        excel_path = Path(files[-1])

    if not excel_path.exists():
        return []

    df = pd.read_excel(excel_path, sheet_name="通话记录")

    # 提取日期用于找音频文件夹
    m = re.search(r'(\d{4}-\d{2}-\d{2})', excel_path.name)
    date_str = m.group(1) if m else ""

    records = []
    for i, row in df.iterrows():
        caller = str(row.get("主叫", "")).strip()
        callee = str(row.get("被叫", "")).strip()
        call_time = str(row.get("通话时间", "")).replace(" ", "_").replace(":", "-")
        seq = str(row.get("序号", i+1)).zfill(4)

        # 找音频文件
        audio_url = ""
        fname_base = f"{seq}_{caller}_{callee}_{call_time}"
        dt_dir = AUDIO_DIR / date_str
        if dt_dir.exists():
            audio_file = next(dt_dir.glob(f"{fname_base}.*"), None)
            if not audio_file:
                for f in dt_dir.glob(f"{seq}_*"):
                    if caller in f.name and callee in f.name:
                        audio_file = f
                        break
            if audio_file:
                audio_url = f"/audio/{date_str}/{audio_file.name}"

        records.append({
            "id": i + 1,
            "user_info": str(row.get("用户信息", "")),
            "company": str(row.get("公司信息", "")),
            "caller": caller,
            "callee": callee,
            "customer_name": str(row.get("客户姓名", "")),
            "customer_company": str(row.get("客户公司", "")),
            "mark": str(row.get("标记", "")),
            "call_time": str(row.get("通话时间", "")),
            "connect_time": str(row.get("接通时间", "")),
            "hangup_time": str(row.get("挂断时间", "")),
            "status": str(row.get("状态", "")),
            "dial_time": str(row.get("拨号时间", "")),
            "transcription": str(row.get("录音转写文字", "")) if pd.notna(row.get("录音转写文字")) else "",
            "audio_url": audio_url,
        })

    return records

@app.get("/audio/{date}/{filename}")
def get_audio(date: str, filename: str):
    """返回音频文件"""
    file_path = AUDIO_DIR / date / filename
    if not file_path.exists():
        return JSONResponse({"error": "file not found"}, status_code=404)
    ext = file_path.suffix.lower()
    media_type = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
    }.get(ext, "audio/wav")
    return FileResponse(file_path, media_type=media_type)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8066)
