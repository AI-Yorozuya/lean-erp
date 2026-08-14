# 用 astral 官方 uv 映像（內建 uv + Python），與 top-erp 慣例一致。
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 先只複製依賴宣告，利用 Docker layer cache：依賴沒變就不用重裝。
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# netcat 給 entrypoint.sh 等 DB 用；postgresql-client 方便除錯。
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# 再複製其餘程式碼。
COPY . .

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
