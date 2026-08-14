"""health app 的 API。

教學重點（擴充模式）：
- 每個 feature app 在自己的 apis.py 建一個 ninja `Router`（不是 NinjaAPI）。
- 用 @router.get / @router.post 定義端點。
- 最後到 core/api.py 用 api.add_router(...) 把這個 router 掛上去。
- response=Schema 讓回傳自動驗證 + 序列化成 JSON。
"""
from ninja import Router

from apps.health.schemas import HealthSchema

router = Router(tags=['health'])  # tags 只是 API 文件分組用


@router.get('', response=HealthSchema)
def health(request):
    """最簡單的存活檢查：回 {"status": "ok"}。

    掛在 core 後的完整路徑是 GET /api/v1/health。
    服務能起來就代表 DB 連線設定與 migrate 都過了。
    """
    return {'status': 'ok'}
