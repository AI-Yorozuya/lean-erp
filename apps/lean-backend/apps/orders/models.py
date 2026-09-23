"""訂單＋訂單明細（轉成訂單.md、訂單推進.md）。

- 一張成交的報價單轉一張訂單；作廢的訂單留著（不真刪），報價單可以再轉一張新的。
- 訂單明細是轉單當下從報價明細複製的一份，之後改報價單不會動到訂單。
"""
from django.db import models

from apps._common.models import TimeStampedModel


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', '待處理'
        PROCESSING = 'processing', '處理中'
        DONE = 'done', '完成'
        VOID = 'void', '已作廢'

    no = models.CharField('單號', max_length=20, unique=True, editable=False)
    status = models.CharField('狀態', max_length=12, choices=Status.choices, default=Status.PENDING)
    quotation = models.ForeignKey('quotations.Quotation', on_delete=models.PROTECT,
                                  related_name='orders', verbose_name='來源報價單')
    expected_delivery = models.DateField('預計交付日', null=True, blank=True)

    class Meta:
        constraints = [
            # 一張報價單同時只能有一張沒作廢的訂單——兩個人同時按轉單，DB 擋下慢的那個
            models.UniqueConstraint(fields=['quotation'], condition=~models.Q(status='void'),
                                    name='one_active_order_per_quotation'),
        ]

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    def __str__(self):
        return self.no


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    name = models.CharField('品名', max_length=100)
    qty = models.DecimalField('數量', max_digits=8, decimal_places=2)
    unit_price = models.PositiveIntegerField('單價')

    @property
    def subtotal(self):
        return self.qty * self.unit_price
