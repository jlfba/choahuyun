# ===== 阶段1：构建前端 =====
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY web/frontend/package.json web/frontend/package-lock.json* ./
RUN npm install || npm install --no-package-lock
COPY web/frontend/ .
RUN npm run build

# ===== 阶段2：轻量网页服务 =====
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi==0.115.12 uvicorn==0.34.2 pandas==2.2.3 openpyxl==3.1.5

COPY web/backend/ ./web/backend/
COPY --from=frontend-build /build/dist ./web/frontend/dist
COPY entrypoint.sh .
RUN mkdir -p output/audio && chmod +x entrypoint.sh

EXPOSE 8066
ENTRYPOINT ["./entrypoint.sh"]
CMD ["web"]
