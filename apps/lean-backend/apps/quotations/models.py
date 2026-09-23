"""報價單＋報價單品項（系統總覽・資料 quote、quote_item）。

原則直接蓋進結構：
- rule_total_sum 總額＝品項加總：total 是 property，沒有欄位＝沒有輸入的地方。
- rule_free_shipping 滿十萬免運（剛好十萬也免運）：free_shipping 從總額算，不存。
- rule_customer_has_quote 有報價單的客戶不能刪：外鍵 PROTECT。
- rule_price_frozen 單價建立時從商品帶入、之後不變：存在品項自己身上，商品改價不回寫。
"""
import datetime as dt

from django.conf import settings
from django.db import models

from apps._common.models import TimeStampedModel

FREE_SHIPPING_THRESHOLD = 100_000


class Quotation(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        SENT = 'sent', '已送出'

    no = models.CharField('單號', max_length=20, unique=True, editable=False)
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT,
                                 related_name='quotations', verbose_name='客戶')
    date = models.DateField('日期', default=dt.date.today)              # 系統帶入今天
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name='quotations', verbose_name='業務')  # 系統帶入登入者
    status = models.CharField('狀態', max_length=10, choices=Status.choices, default=Status.DRAFT)
    sent_at = models.DateField('送出日期', null=True, blank=True)        # 匯出 PDF 那天

    @property
    def total(self) -> int:
        return sum(item.subtotal for item in self.items.all())

    @property
    def free_shipping(self) -> bool:
        return self.total >= FREE_SHIPPING_THRESHOLD

    @property
    def sales_name(self) -> str:
        return self.owner.shown_name

    def __str__(self):
        return self.no


class QuotationItem(TimeStampedModel):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items', verbose_name='報價單')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT,
                                related_name='quote_items', verbose_name='商品')
    qty = models.PositiveIntegerField('數量')
    unit_price = models.PositiveIntegerField('單價')   # 建立時從商品帶入，之後不變

    class Meta:
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=models.Q(qty__gte=1), name='quote_item_qty_gte_1')]

    @property
    def subtotal(self) -> int:
        return self.qty * self.unit_price
