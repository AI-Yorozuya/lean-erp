"""商品（系統總覽・資料 product）：型號、名稱、單價。價目表就是這張表：一個型號一個價，全客戶相同。

- 型號唯一：同名的商品靠型號分（原則 rule_model_shown）。
- 報價單的單價從這裡帶入，帶入後不再跟著改（原則 rule_price_frozen，存在報價單品項上）。
"""
from django.db import models

from apps._common.models import TimeStampedModel


class Product(TimeStampedModel):
    model = models.CharField('型號', max_length=50, unique=True)
    name = models.CharField('名稱', max_length=100)
    price = models.PositiveIntegerField('單價')

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0), name='product_price_gt_0')]

    def __str__(self):
        return f'{self.model} {self.name}'
