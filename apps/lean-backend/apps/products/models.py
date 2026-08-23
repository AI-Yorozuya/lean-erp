"""商品：品名＋預設單價。報價時挑它只是「帶入」——明細存快照，之後改這裡不回寫舊單（架構圖原則 8）。"""
from django.db import models

from apps._common.models import TimeStampedModel


class Product(TimeStampedModel):
    name = models.CharField('品名', max_length=100)
    default_price = models.PositiveIntegerField('預設單價')
    note = models.TextField('備註', blank=True, default='')

    def __str__(self):
        return self.name
