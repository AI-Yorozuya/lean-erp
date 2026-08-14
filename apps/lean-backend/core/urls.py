"""URL 路由設定。

教學重點：整個專案只有一個 NinjaAPI（定義在 core/api.py），
這裡把它的 `.urls` 掛在 /api/v1/ 之下。
要新增端點 → 不用改這裡，去 core/api.py 註冊 router 即可。
"""
from django.urls import path

from core.api import api

urlpatterns = [
    path('api/v1/', api.urls),
]
