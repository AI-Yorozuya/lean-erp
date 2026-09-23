#!/bin/bash
# 容器啟動流程。共用同一個 image 跑兩種角色：
#   - 沒帶參數（backend 預設）→ 等 DB → migrate → 起 gunicorn server。
#   - 有帶參數（例如 celery worker）→ 等 DB → 直接 exec 那個指令（不 migrate，
#     migration 交給 backend 跑，避免兩個容器搶著 migrate）。
set -e

echo "=================================="
echo "Starting lean-erp ($*)"
echo "=================================="

# 等 PostgreSQL 開好（compose 裡 service 名就是 postgres，port 5432）。
echo "Waiting for PostgreSQL..."
until nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL is ready"

# 有帶指令 → 那是 worker 之類的角色，直接跑它。
if [ "$#" -gt 0 ]; then
  echo "Running: $*"
  exec "$@"
fi

# 沒帶指令 → backend 預設流程：migrate 後起 server。
echo "Running migrations..."
uv run python manage.py migrate --noinput

# 本機開發（DEBUG）→ 灌示範資料（dev 帳號＋示範商品＋示範客戶），第一次起來就有東西看。
# 指令冪等（已有就跳過），所以每次開機都跑也安全。
# prod 不灌：entrypoint 是 local/prod 共用，這裡用 DEBUG 擋住。
if [ "${DEBUG}" = "True" ] || [ "${DEBUG}" = "true" ] || [ "${DEBUG}" = "1" ]; then
  echo "Seeding demo data (DEBUG only)..."
  uv run python manage.py seed_demo
fi

# DEBUG=True（本機開發）→ uvicorn --reload：改 code 自動重載（需掛 source volume，見 local compose）。
# 否則（prod）→ gunicorn + uvicorn worker。
if [ "${DEBUG}" = "True" ] || [ "${DEBUG}" = "true" ] || [ "${DEBUG}" = "1" ]; then
  echo "Starting DEV server (uvicorn --reload) on :8000 ..."
  exec uv run uvicorn core.asgi:application --host 0.0.0.0 --port 8000 --reload
else
  echo "Starting PROD server (gunicorn) on :8000 ..."
  exec uv run gunicorn core.asgi:application \
      --bind 0.0.0.0:8000 \
      --workers 2 \
      --worker-class uvicorn.workers.UvicornWorker \
      --access-logfile - \
      --error-logfile - \
      --log-level info \
      --timeout 120
fi
