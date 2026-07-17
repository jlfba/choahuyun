# ===== 阶段1：构建前端 =====
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY web/frontend/package.json web/frontend/package-lock.json* ./
RUN npm install || npm install --no-package-lock
COPY web/frontend/ .
RUN npm run build

# ===== 阶段2：完整运行环境 =====
FROM python:3.12-slim
WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg ca-certificates \
    fonts-wqy-zenhei fonts-noto-cjk \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（分步安装）
RUN pip install --no-cache-dir \
    fastapi==0.115.12 uvicorn==0.34.2 pandas==2.2.3 openpyxl==3.1.5 \
    requests==2.32.3 schedule==1.2.2
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && playwright install-deps chromium
RUN pip install --no-cache-dir funasr
RUN pip install --no-cache-dir opencc-python-reimplemented 2>/dev/null || true

# 复制代码
COPY *.py ./
COPY web/backend/ ./web/backend/
COPY --from=frontend-build /build/dist ./web/frontend/dist
COPY entrypoint.sh .
RUN mkdir -p output/audio && chmod +x entrypoint.sh

EXPOSE 8066
ENTRYPOINT ["./entrypoint.sh"]
CMD ["web"]
