"""django-ninja 的 response schema。

教學重點：ninja 用 Schema（底層是 pydantic）描述輸入/輸出的形狀，
回傳時會自動驗證 + 序列化成 JSON。這裡只示範一個最小的回應結構。
"""
from ninja import Schema


class HealthSchema(Schema):
    status: str
