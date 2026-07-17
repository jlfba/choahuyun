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

## 版本记录
v1.0.0 - 初始版本
