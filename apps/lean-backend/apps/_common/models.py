"""共用的抽象 model。

教學重點：abstract=True 的 model 不會自己建表，而是給其他 model「繼承」用。
之後所有領域 model（帳本、訂單...）都繼承 TimeStampedModel，
就自動有了 created_at / updated_at，不必每張表重寫。
"""
from django.db import models


class TimeStampedModel(models.Model):
    """所有業務 model 的基底：自動記錄建立/更新時間。

    用法：
        class Ledger(TimeStampedModel):
            name = models.CharField(max_length=100)
    """
    created_at = models.DateTimeField(auto_now_add=True)  # 第一次存檔時自動填
    updated_at = models.DateTimeField(auto_now=True)      # 每次存檔自動更新

    class Meta:
        abstract = True  # 關鍵：不建表，只供繼承
