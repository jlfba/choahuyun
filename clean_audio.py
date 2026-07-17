#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理孤立音频：
1. 删除主叫+被叫组合不在 Excel 里的音频
2. 同一组合超过 Excel 行数的重复音频也删除

用法:
  python clean_audio.py              # 清理所有日期
  python clean_audio.py 2026-07-15   # 只清理指定日期
  python clean_audio.py --dry-run    # 只预览不删除
"""
import re, sys, os
from pathlib import Path
from datetime import datetime
from collections import Counter
import pandas as pd

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

WORK_DIR = Path(__file__).parent
OUTPUT_DIR = WORK_DIR / "output"
# 本地 D:\output 优先
if Path(r"D:\output").exists():
    OUTPUT_DIR = Path(r"D:\output")
AUDIO_DIR = OUTPUT_DIR / "audio"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def get_pair_counts_from_excel(excel_path):
    """从 Excel 提取每个 主叫+被叫 组合出现的次数"""
    try:
        df = pd.read_excel(excel_path, sheet_name="通话记录")
    except Exception:
        try:
            df = pd.read_excel(excel_path)
        except Exception as e:
            log(f"  [WARN] 读取失败: {excel_path.name} - {e}")
            return Counter()

    pairs = []
    if "主叫" in df.columns and "被叫" in df.columns:
        for _, row in df.iterrows():
            caller = str(row.get("主叫", "")).strip()
            callee = str(row.get("被叫", "")).strip()
            if caller and callee and caller != "nan" and callee != "nan":
                # 处理浮点数格式的号码
                try:
                    caller = str(int(float(caller)))
                    callee = str(int(float(callee)))
                except:
                    pass
                pairs.append((caller, callee))
    return Counter(pairs)

def extract_call_pair(filename):
    """从文件名提取主叫+被叫"""
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) >= 3:
        return parts[1], parts[2]
    return None, None

def clean_audio(date_str=None, dry_run=False):
    if not AUDIO_DIR.exists():
        log("audio 目录不存在")
        return

    # 按日期收集 Excel 组合计数
    date_pair_counts = {}
    for ef in sorted(OUTPUT_DIR.glob("通话记录_*.xlsx")):
        if "~$" in ef.name:
            continue
        m = re.search(r'(\d{4}-\d{2}-\d{2})', ef.name)
        if not m:
            continue
        d = m.group(1)
        counts = get_pair_counts_from_excel(ef)
        if d in date_pair_counts:
            date_pair_counts[d] += counts
        else:
            date_pair_counts[d] = counts
        log(f"  Excel {ef.name}: {sum(counts.values())} 行, {len(counts)} 组合 → {d}")

    # 扫描音频
    if date_str:
        date_dirs = [AUDIO_DIR / date_str]
    else:
        date_dirs = sorted([d for d in AUDIO_DIR.iterdir() if d.is_dir()])

    total_scanned = 0
    total_deleted = 0
    total_kept = 0

    for date_dir in date_dirs:
        if not date_dir.is_dir():
            continue

        d = date_dir.name
        pair_counts = date_pair_counts.get(d, Counter())
        audio_files = sorted([f for f in date_dir.glob("*.*") if f.suffix.lower() in (".wav", ".mp3", ".ogg")])

        if not pair_counts:
            log(f"\n[{d}] 没有对应 Excel，将删除全部 {len(audio_files)} 个音频")
            for f in audio_files:
                total_scanned += 1
                if dry_run:
                    log(f"  [DRY] 将删除: {f.name}")
                else:
                    try:
                        f.unlink()
                        log(f"  [DEL] {f.name}")
                    except Exception as e:
                        log(f"  [ERR] {f.name}: {e}")
                        continue
                total_deleted += 1
            continue

        log(f"\n[{d}] Excel {sum(pair_counts.values())} 行, 音频 {len(audio_files)} 个")

        # 按组合分组音频文件
        audio_by_pair = {}
        unparseable = []
        for f in audio_files:
            caller, callee = extract_call_pair(f.name)
            if caller and callee:
                key = (caller, callee)
                if key not in audio_by_pair:
                    audio_by_pair[key] = []
                audio_by_pair[key].append(f)
            else:
                unparseable.append(f)

        # 1. 删除不在 Excel 里的组合
        for pair, files in audio_by_pair.items():
            if pair not in pair_counts:
                for f in files:
                    total_scanned += 1
                    if dry_run:
                        log(f"  [DRY] 不在表格: {f.name}  ({pair[0]}→{pair[1]})")
                    else:
                        try:
                            f.unlink()
                            log(f"  [DEL] 不在表格: {f.name}  ({pair[0]}→{pair[1]})")
                        except Exception as e:
                            log(f"  [ERR] {f.name}: {e}")
                            continue
                    total_deleted += 1
                del audio_by_pair[pair]

        # 2. 超出 Excel 行数的重复音频删除
        for pair, files in audio_by_pair.items():
            max_keep = pair_counts.get(pair, 0)
            if len(files) <= max_keep:
                total_kept += len(files)
                total_scanned += len(files)
                continue

            # 保留前 max_keep 个，删除多余的
            to_keep = files[:max_keep]
            to_delete = files[max_keep:]
            total_kept += len(to_keep)
            total_scanned += len(files)

            for f in to_delete:
                if dry_run:
                    log(f"  [DRY] 重复: {f.name}  ({pair[0]}→{pair[1]}, 保留{max_keep}个)")
                else:
                    try:
                        f.unlink()
                        log(f"  [DEL] 重复: {f.name}  ({pair[0]}→{pair[1]}, 保留{max_keep}个)")
                    except Exception as e:
                        log(f"  [ERR] {f.name}: {e}")
                        continue
                total_deleted += 1

        # 3. 无法解析的文件
        for f in unparseable:
            total_scanned += 1
            total_kept += 1
            log(f"  [SKIP] 无法解析: {f.name}")

    log(f"\n{'=' * 50}")
    log(f"扫描: {total_scanned} 个音频")
    log(f"{'将删除' if dry_run else '已删除'}: {total_deleted} 个")
    log(f"保留: {total_kept} 个")
    if dry_run:
        log("(预览模式，未实际删除。去掉 --dry-run 执行删除)")
    log(f"{'=' * 50}")

if __name__ == "__main__":
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    date_arg = [a for a in args if re.match(r'^\d{4}-\d{2}-\d{2}$', a)]
    date_str = date_arg[0] if date_arg else None

    if dry_run:
        log("=== 预览模式（不删除） ===")
    if date_str:
        log(f"日期: {date_str}")
    else:
        log("日期: 全部")

    clean_audio(date_str, dry_run)
