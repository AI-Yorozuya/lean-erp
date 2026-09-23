"""報價單＋報價明細。

三條原則直接蓋進結構（架構圖〈原則〉）：
- 原則 1 總額＝明細加總：total 是 property，**沒有欄位＝沒有輸入的地方**。
- 原則 7 被引用的客戶不能硬刪：FK 用 PROTECT。
- 原則 8 明細存快照：品名/單價存在明細自己身上，來源商品之後改名改價不回寫。
"""
import datetime as dt

from django.conf import settings
from django.db import models

from apps._common.models import TimeStampedModel


class Quotation(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', '草擬'
        SENT = 'sent', '已送出'
        WON = 'won', '已成交'
        LOST = 'lost', '沒成'

    no = models.CharField('單號', max_length=20, unique=True, editable=False)
    status = models.CharField('狀態', max_length=10, choices=Status.choices, default=Status.DRAFT)
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT,
                                 related_name='quotations', verbose_name='客戶')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name='quotations', verbose_name='負責人')
    valid_until = models.DateField('有效期限', null=True, blank=True)  # 沒填＝不設限
    payment_terms = models.CharField('付款條件', max_length=100, blank=True,
                                     default='完工後三日內付款')
    note = models.TextField('備註', blank=True, default='')
    sent_on = models.DateField('送出日', null=True, blank=True)  # 送出時蓋；收回清掉，再送出蓋新的

    @property
    def total(self) -> int:
        """總額＝Σ 小計。查詢時現算——這不是 UI 的貼心，是原則 1 的兌現方式。"""
        return sum(item.subtotal for item in self.items.all())

    @property
    def days_left(self):
        """剩幾天：現算，不存欄位、不跑排程（架構圖〈流程〉的拍板）。沒設限回 None。"""
        if self.valid_until is None:
            return None
        return (self.valid_until - dt.date.today()).days

    @property
    def is_expired(self) -> bool:
        return self.days_left is not None and self.days_left < 0

    @property
    def active_order(self):
        """還沒作廢的那張訂單（一張報價只轉一張；作廢的不算）。"""
        return self.orders.exclude(status='void').first()

    def __str__(self):
        return self.no


class QuotationItem(TimeStampedModel):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    name = models.CharField('品名', max_length=100)                      # 快照：存自己的
    qty = models.DecimalField('數量', max_digits=8, decimal_places=2)    # 工時類會用到 1.5
    unit_price = models.PositiveIntegerField('單價')                     # 快照：整數台幣
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL,
                                null=True, blank=True, verbose_name='來源商品')  # 挑的就填、手打的就空

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(qty__gt=0), name='item_qty_gt_0'),
        ]

    @property
    def subtotal(self):
        return self.qty * self.unit_price
