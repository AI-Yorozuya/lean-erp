"""整個專案唯一的 NinjaAPI 物件，與「新功能 router 註冊處」。

教學重點（擴充模式）：
- 只建「一個」NinjaAPI（掛在 core/urls.py 的 /api/v1/）。
- 每個 feature app 在自己的 apis.py 裡建一個 ninja `Router`，
  然後在「下面這個區塊」用 api.add_router(...) 掛上來。
- 想加新功能 → 寫 apps/<feature>/apis.py 的 router → 來這裡加一行。
  這就是這個 sandbox 的標準擴充點。
"""
from ninja import NinjaAPI

from apps.accounts.apis import router as auth_router
from apps.customers.apis import router as customers_router
from apps.health.apis import router as health_router
from apps.products.apis import router as products_router
from apps.quotations.apis import router as quotations_router

# title / version 會顯示在自動產生的 API 文件（/api/v1/docs）。
api = NinjaAPI(title='lean-erp API', version='1.0.0')

# ──────────────────────────────────────────────────────────────
# 新功能 router 註冊在這
#   範例：api.add_router('/ledger/', ledger_router)
# ──────────────────────────────────────────────────────────────
api.add_router('/health', health_router)
api.add_router('/auth', auth_router)
api.add_router('/customers', customers_router)
api.add_router('/products', products_router)
api.add_router('/quotations', quotations_router)

