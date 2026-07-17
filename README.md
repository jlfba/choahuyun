# 潮呼云通话记录

自动抓取通话记录、语音转写，并提供网页展示。

## 架构

```
Vue3 + Vite (前端)  ←→  Python FastAPI (后端API)
                          ├── GET /api/dates     → 可用日期列表
                          ├── GET /api/records    → 通话记录(支持日期筛选)
                          └── GET /audio/:path    → 音频文件流
```

## 功能

1. 日期选择器 - 筛选某天的数据
2. 表格展示 - 通话记录数据
3. 每行播放器 - 对应录音音频
4. 转写文字列 - 显示语音转写内容

## 快速开始

### 1. 配置

```bash
cp config.example.json config.json
# 编辑 config.json，填入账号密码
```

### 2. 抓取与转写

```bash
python auto_scrape.py
python daily_task.py
```

### 3. 启动网页

```bash
# 后端
cd web/backend
python main.py

# 前端
cd web/frontend
npm install
npm run dev
```

也可使用 `web/start.bat` 一键启动。

## 目录结构

```
chaohuyun/
  auto_scrape.py          # 自动抓取
  daily_task.py           # 日常任务
  scheduler.py            # 定时调度
  transcribe_*.py         # 语音转写
  config.example.json     # 配置模板
  web/
    backend/main.py       # FastAPI 服务
    frontend/             # Vue3 前端
  output/                 # 本地运行产物（不入仓库）
```

## 版本

见 [DEVELOPMENT.md](DEVELOPMENT.md)
