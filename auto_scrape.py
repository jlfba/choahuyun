#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超呼云 - 全自动无头抓取 + 下载 + 转写
音频按日期自动归类到子文件夹，转写结果转简体
"""
import re, sys, os, asyncio, json
from pathlib import Path
from datetime import datetime
import requests
import pandas as pd

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

CONFIG = json.load(open("config.json", encoding="utf-8"))
AUDIO_DIR = Path("output/audio")
EXCEL_PATH = Path("output/通话记录_完整数据.xlsx")
WHISPER_CONFIG = CONFIG.get("whisper", {})
WHISPER_MODEL = WHISPER_CONFIG.get("model", "base")
WHISPER_LANGUAGE = WHISPER_CONFIG.get("language", "zh")
WHISPER_INITIAL_PROMPT = WHISPER_CONFIG.get("initial_prompt") or "请使用简体中文准确转写以下音频内容，不要输出繁体字。"

# 简繁转换
SIMPLIFIED_CONVERTER = None
SIMPLIFIED_CONVERTER_NAME = None
try:
    from opencc import OpenCC
    for converter_name in ("t2s", "hk2s"):
        try:
            SIMPLIFIED_CONVERTER = OpenCC(converter_name)
            SIMPLIFIED_CONVERTER_NAME = converter_name
            break
        except Exception:
            continue
except ImportError:
    pass

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def extract_date(row):
    # 支持两种key格式：中文列名 或 a8/a9/a12
    for key in ["接通时间", "拨号时间", "a9", "a12"]:
        v = str(row.get(key, "")).strip()
        m = re.search(r'(\d{4}-\d{2}-\d{2})', v)
        if m:
            return m.group(1)
    return datetime.now().strftime('%Y-%m-%d')

def to_simplified(text):
    if not text:
        return text
    if SIMPLIFIED_CONVERTER:
        return SIMPLIFIED_CONVERTER.convert(text)
    return text

async def run():
    from playwright.async_api import async_playwright

    log("=" * 60)
    log("超呼云 - 全自动无头抓取工具")
    log("=" * 60)
    if SIMPLIFIED_CONVERTER_NAME:
        log(f"简繁转换已启用: OpenCC({SIMPLIFIED_CONVERTER_NAME})")
    else:
        log("[WARN] 未安装 opencc，转写结果可能包含繁体字")

    async with async_playwright() as pw:
        import platform
        browser_args = {"headless": True}
        if platform.system() == "Windows":
            browser_args["channel"] = "msedge"
        browser = await pw.chromium.launch(**browser_args)
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        # ── 登录 ──
        log("[1/4] 登录...")
        await page.goto("https://chaohuzhineng.com")
        await page.wait_for_timeout(2000)
        await page.fill('input[name="username"]', CONFIG["credentials"]["username"])
        await page.fill('input[name="password"]', CONFIG["credentials"]["password"])
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(5000)

        if "login" in page.url.lower():
            log("出现验证码，需要手动处理")
            log("请运行: python easy_scrape.py")
            await browser.close()
            return

        log("登录成功")

        # ── 进入通话列表 ──
        log("[2/4] 进入通话列表...")
        await page.evaluate("""()=>{
            var a=document.querySelector('a[data-open*="phone/index"], a[data-target-tips="通话列表"]');
            if(a)a.click();
        }""")
        await page.wait_for_timeout(3000)

        # ── 筛选 ──
        date_filter = CONFIG["settings"].get("date_filter", "")
        log(f"[3/4] 设置筛选... (日期: {date_filter or '全部'})")
        filter_result = await page.evaluate(f"""()=>{{
            var di=document.querySelector('input[name="create_date"]');
            if(di)di.value='{date_filter}';
            var sel=document.querySelector('select[name="is_sound"]');
            if(!sel)return 'no_select';
            sel.value='1';
            if(typeof layui!=='undefined'&&layui.form)layui.form.render('select');
            var btns=document.querySelectorAll('button');
            for(var i=0;i<btns.length;i++){{
                var html=btns[i].innerHTML.replace(/\\s/g,'');
                if(html.indexOf('搜索')>=0||html.indexOf('搜')>=0){{btns[i].click();return 'ok';}}
            }}
            return 'no_btn';
        }}""")
        log(f"  筛选: {filter_result}")
        await page.wait_for_timeout(5000)

        total = await page.evaluate("""()=>{
            var ps=document.querySelectorAll('.pagination li'),n=1;
            ps.forEach(function(l){var t=l.textContent.trim(),v=parseInt(t);if(!isNaN(v)&&v>n)n=v;});
            return n;
        }""")
        log(f"  总页数: {total}")

        # ── 抓取所有页 ──
        log("[4/4] 开始抓取...")
        all_data = []

        for p in range(1, total + 1):
            if p > 1:
                await page.evaluate(f"""()=>{{var ls=document.querySelectorAll('.pagination a[data-open]');for(var i=0;i<ls.length;i++){{if(ls[i].textContent.trim()==='{p}'){{ls[i].click();return;}}}}}}""")
                await page.wait_for_timeout(2000)

            rows = await page.evaluate("""()=>{
                var trs=document.querySelectorAll('tbody tr'),res=[];
                trs.forEach(function(tr){
                    var tds=tr.querySelectorAll('td');if(tds.length<13)return;
                    var u='',h=tds[12].innerHTML,m=h.match(/src="([^"]+)"/);
                    if(m)u=m[1].replace(/&amp;/g,'&');
                    var c='',ch=tds[3].innerHTML,cm=ch.match(/(\\d{7,15})\\s*$/);
                    if(cm)c=cm[1];
                    res.push({a1:(tds[0].textContent||'').trim(),a2:(tds[1].textContent||'').trim(),a3:(tds[2].textContent||'').trim(),a4:c,a5:(tds[4].textContent||'').trim(),a6:(tds[5].textContent||'').trim(),a7:(tds[6].textContent||'').trim(),a8:(tds[7].textContent||'').trim(),a9:(tds[8].textContent||'').trim(),a10:(tds[9].textContent||'').trim(),a11:(tds[10].textContent||'').trim(),a12:(tds[11].textContent||'').trim(),url:u});
                });return res;
            }""")
            audio_rows = [r for r in rows if r.get("url")]
            # 过滤掉10秒以下的通话
            filtered = []
            for r in audio_rows:
                try:
                    t1 = datetime.strptime(r.get("a9","").strip(), "%Y-%m-%d %H:%M:%S")
                    t2 = datetime.strptime(r.get("a10","").strip(), "%Y-%m-%d %H:%M:%S")
                    if (t2 - t1).total_seconds() >= 10:
                        filtered.append(r)
                except:
                    filtered.append(r)  # 解析失败的保留
            # 去重
            seen = {r.get("a3","")+r.get("a4","")+r.get("a12","") for r in all_data}
            new_rows = [r for r in filtered if (r.get("a3","")+r.get("a4","")+r.get("a12","")) not in seen]
            all_data.extend(new_rows)
            log(f"  第{p}/{total}页: {len(rows)}行, 有录音{len(audio_rows)}条, >=10秒{len(filtered)}条, 新增{len(new_rows)}条")

        await browser.close()
        log(f"\n抓取完成: {len(all_data)} 条有录音记录")

        if not all_data:
            log("没有数据!")
            return

        # ── 下载音频 ──
        log("\n=== 下载音频 ===")
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        downloaded = 0

        for i, r in enumerate(all_data):
            url = r.get("url", "")
            if not url:
                continue
            ext = Path(url.split("?")[0]).suffix or ".wav"
            caller = r["a3"]
            callee = r["a4"]
            # 用时间戳区分同一主叫被叫的多次通话
            call_time = r.get("a8", "").replace(" ", "_").replace(":", "-")
            fname = f"{i+1:04d}_{caller}_{callee}_{call_time}{ext}"
            dt = extract_date(r)
            dt_dir = AUDIO_DIR / dt
            dt_dir.mkdir(exist_ok=True)
            fpath = dt_dir / fname

            if fpath.exists() and fpath.stat().st_size > 1000:
                downloaded += 1
                continue

            try:
                resp = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://chaohuzhineng.com/",
                }, timeout=30)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    fpath.write_bytes(resp.content)
                    downloaded += 1
            except Exception as e:
                log(f"  [X] {fname}: {e}")

            if (i + 1) % 50 == 0:
                log(f"  进度: {i+1}/{len(all_data)}, 已下载{downloaded}")

        log(f"下载完成: {downloaded}/{len(all_data)}")

        # ── FunASR Paraformer 转写 ──
        log("\n=== 语音转写 (FunASR Paraformer) ===")
        from funasr import AutoModel
        model = AutoModel(
            model="paraformer-zh",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            device="cpu",
        )
        log("Paraformer模型加载完成")

        records = []
        transcribed = 0

        for i, r in enumerate(all_data):
            caller = r["a3"]
            callee = r["a4"]
            dt = extract_date(r)
            call_time = r.get("a8", "").replace(" ", "_").replace(":", "-")
            fname_base = f"{i+1:04d}_{caller}_{callee}_{call_time}"

            audio_file = None
            dt_dir = AUDIO_DIR / dt
            if dt_dir.exists():
                audio_file = next(dt_dir.glob(f"{fname_base}.*"), None)

            text = ""
            if audio_file and audio_file.stat().st_size > 1000:
                try:
                    result = model.generate(input=str(audio_file))
                    if result and len(result) > 0:
                        text = result[0].get("text", "").strip()
                    if not text:
                        text = "(未能识别)"
                    text = to_simplified(text)
                    transcribed += 1
                except Exception as e:
                    text = "(转写失败)"

            records.append({
                "序号": i + 1,
                "用户信息": to_simplified(r["a1"]),
                "公司信息": to_simplified(r["a2"]),
                "主叫": caller,
                "被叫": callee,
                "客户姓名": to_simplified(r["a5"]),
                "客户公司": to_simplified(r["a6"]),
                "标记": to_simplified(r["a7"]),
                "通话时间": r["a8"],
                "接通时间": r["a9"],
                "挂断时间": r["a10"],
                "状态": to_simplified(r["a11"]),
                "拨号时间": r["a12"],
                "录音转写文字": text,
            })

            if (i + 1) % 20 == 0:
                log(f"  转写进度: {i+1}/{len(all_data)}, 已转写{transcribed}")

        # ── 输出Excel ──
        df = pd.DataFrame(records)
        EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="通话记录", index=False)

        log(f"\n{'=' * 60}")
        log(f"全部完成!")
        log(f"  记录: {len(records)} 条")
        log(f"  下载: {downloaded} 个音频")
        log(f"  转写: {transcribed} 条")
        log(f"  Excel: {EXCEL_PATH.resolve()}")
        log(f"{'=' * 60}")

if __name__ == "__main__":
    import sys
    # 用法: python auto_scrape.py [日期]
    # 例: python auto_scrape.py 2026-07-15
    # 例: python auto_scrape.py  (抓全部)
    date_input = ""
    if len(sys.argv) > 1:
        date_input = sys.argv[1].strip()

    import re as _re
    if date_input and _re.match(r'^\d{4}-\d{2}-\d{2}$', date_input):
        CONFIG["settings"]["date_filter"] = date_input
        print(f"抓取日期: {date_input}")
    else:
        CONFIG["settings"]["date_filter"] = ""
        print("抓取全部历史数据")

    # 根据日期设置输出文件名
    if date_input:
        EXCEL_PATH = Path(f"output/通话记录_{date_input}.xlsx")
    else:
        EXCEL_PATH = Path(f"output/通话记录_全部.xlsx")

    asyncio.run(run())
