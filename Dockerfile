# ===== 阶段1：构建前端 =====
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY web/frontend/package.json web/frontend/package-lock.json* ./
RUN npm install || npm install --no-package-lock
COPY web/frontend/ .
RUN npm run build

# ===== 阶段2：Python 运行环境 =====
FROM python:3.12-slim
WORKDIR /app

# 系统依赖（Playwright + 中文字体）
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg fonts-wqy-zenhei fonts-noto-cjk libglib2.0-0 \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（分步安装，利用缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir --no-build-isolation \
    fastapi uvicorn pandas openpyxl requests schedule \
    && pip install --no-cache-dir --no-build-isolation playwright \
    && playwright install chromium \
    && pip install --no-cache-dir --no-build-isolation funasr \
    || pip install --no-cache-dir funasr[all]

# 可选依赖（失败不阻塞构建）
RUN pip install --no-cache-dir opencc-python-reimplemented 2>/dev/null || true

# 复制后端代码
COPY *.py ./
COPY web/backend/ ./web/backend/

# 复制构建好的前端
COPY --from=frontend-build /build/dist ./web/frontend/dist

# 创建 output 目录
RUN mkdir -p output/audio

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8066

ENTRYPOINT ["./entrypoint.sh"]
CMD ["web"]
