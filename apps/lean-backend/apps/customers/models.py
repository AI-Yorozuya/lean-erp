"""客戶：名稱＋電話（認人鍵，email 不強制）。

電話刻意「不」設 unique——同人兩支電話／換號怎麼認是待拍板的題（架構圖待問），
先用搜尋讓人自己挑，不偷拍資料層決定。
"""
from django.db import models

from apps._common.models import TimeStampedModel


class Customer(TimeStampedModel):
    name = models.CharField('名稱', max_length=100)
    phone = models.CharField('電話', max_length=30, db_index=True)
    note = models.TextField('備註', blank=True, default='')

    def __str__(self):
        return f'{self.name}（{self.phone}）'
