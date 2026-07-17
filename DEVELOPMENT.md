# 通话记录展示网页 - 开发计划

## 架构
```
Vue3 + Vite (前端)  ←→  Python FastAPI (后端API)
                          ├── GET /api/dates     → 可用日期列表
                          ├── GET /api/records    → 通话记录(支持日期筛选)
                          └── GET /audio/:path    → 音频文件流
```

## 功能
1. 日期选择器 - 筛选某天的数据
2. 表格展示 - 14列通话记录数据
3. 每行播放器 - 对应录音音频
4. 转写文字列 - 显示语音转写内容

## 文件结构
```
chaohuyun/
  web/
    backend/
      main.py          # FastAPI 服务
    frontend/
      src/
        App.vue         # 主页面
        components/
          RecordTable.vue  # 表格组件
      package.json
      vite.config.js
```

## 开发步骤
1. 创建 FastAPI 后端 - 读Excel + 提供音频
2. 创建 Vue3 前端 - 表格 + 播放器 + 筛选
3. 联调测试

## Docker 部署

### 快速启动
```bash
# 1. 准备配置文件
cp config.example.json config.json
# 编辑 config.json 填入账号密码

# 2. 启动（网页 + 定时抓取）
docker compose up -d

# 3. 访问
# 网页: http://服务器IP:8066
```

### 单独执行任务
```bash
# 一次性抓取全部数据
docker compose run --rm web scrape

# 抓取指定日期
docker compose run --rm web scrape 2026-07-15

# 执行每日任务（抓取+转写+清洗）
docker compose run --rm web daily
```

### 数据目录
| 容器路径 | 宿主机路径 | 说明 |
|---|---|---|
| `/app/config.json` | `./config.json` | 账号密码（只读挂载） |
| `/app/output/` | `./output/` | Excel + 音频（读写，持久化） |

## 版本记录
v1.0.0 - 初始版本
v1.1.0 - 添加 Docker 部署支持
