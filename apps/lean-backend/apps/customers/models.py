"""客戶（系統總覽・資料 customer）：名稱、聯絡人。

報價紀錄幾筆、最近一張報價是從報價單反算出來的，不存欄位（見 apis.py）。
被報價單引用的客戶不能刪（原則 rule_customer_has_quote）：報價單的外鍵用 PROTECT。
"""
from django.db import models

from apps._common.models import TimeStampedModel


class Customer(TimeStampedModel):
    name = models.CharField('名稱', max_length=100)
    contact = models.CharField('聯絡人', max_length=50, blank=True, default='')

    def __str__(self):
        return self.name
