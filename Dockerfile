# ===== 阶段1：构建前端 =====
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY web/frontend/package.json web/frontend/package-lock.json* ./
RUN npm install
COPY web/frontend/ .
RUN npm run build

# ===== 阶段2：Python 运行环境 =====
FROM python:3.12-slim
WORKDIR /app

# 系统依赖（Playwright Chromium）
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg fonts-wqy-zenhei fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps chromium

# 复制后端代码
COPY *.py ./
COPY web/backend/ ./web/backend/

# 复制构建好的前端到后端可服务的目录
COPY --from=frontend-build /build/dist ./web/frontend/dist

# 创建 output 目录（实际数据通过 volume 挂载）
RUN mkdir -p output/audio

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8066

ENTRYPOINT ["./entrypoint.sh"]
CMD ["web"]
