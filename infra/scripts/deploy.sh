#!/usr/bin/env bash
# lean 單機部署腳本。在「已 terraform apply 出來、裝好 docker」的伺服器上跑，
# 或本機指向遠端 docker context 時也行。
#
# 做的事：build 前端 → build/起後端+nginx+db → 跑 migrate。
# 從 repo 根目錄執行：  bash infra/scripts/deploy.sh
set -euo pipefail

# 切到 repo 根目錄（這個腳本在 infra/scripts/ 底下）。
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod"

# 0. 前置檢查：機密檔在不在（不存在就停，別用半套設定上線）。
if [ ! -f infra/.env.prod ]; then
  echo "✗ 找不到 infra/.env.prod —— 先 cp infra/.env.prod.example infra/.env.prod 並填好正式值。" >&2
  exit 1
fi

# 1. build admin 前端的靜態檔（nginx 會掛 dist/ 進去服務）。
echo "==> building frontend (lean-admin)"
( cd apps/lean-admin && npm ci && npm run build )

# 2. build image 並啟動整套（postgres + backend + nginx）。
echo "==> docker compose up -d --build"
$COMPOSE up -d --build

# 3. 跑 migration（backend image 內含 entrypoint，但這裡再顯式跑一次保險）。
echo "==> running migrations"
$COMPOSE exec -T backend uv run python manage.py migrate --noinput

echo "==> done. 確認："
echo "    curl -s localhost/api/v1/health   # 預期 {\"status\": \"ok\"}"
