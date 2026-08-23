"""建立報價單（規格：intents/建立報價單.md；原則照 intents/架構圖.md）。

單號 `Q` + 日期 + 三碼流水，同日連號不重複（原則 6）：
靠 DB unique 約束＋撞號重試——兩個人同秒開單，慢的那個撞 IntegrityError 再取號一次。
"""
import datetime as dt
from decimal import Decimal

from django.db import IntegrityError, transaction

from .models import Quotation, QuotationItem

MAX_RETRY = 3


class InvalidQuotation(Exception):
    pass


def _next_no(today: dt.date) -> str:
    prefix = f'Q{today:%Y%m%d}'
    last = (Quotation.objects.filter(no__startswith=prefix)
            .order_by('-no').values_list('no', flat=True).first())
    seq = int(last.rsplit('-', 1)[1]) + 1 if last else 1
    return f'{prefix}-{seq:03d}'


def create_quotation(*, owner, customer, items: list[dict],
                     valid_until=None, payment_terms='完工後三日內付款', note='') -> Quotation:
    if not items:
        raise InvalidQuotation('明細至少要有一行')
    for it in items:
        if Decimal(str(it['qty'])) <= 0:
            raise InvalidQuotation('數量必須大於 0')
        if int(it['unit_price']) < 0:
            raise InvalidQuotation('單價不能是負數')

    for attempt in range(MAX_RETRY):
        try:
            with transaction.atomic():
                q = Quotation.objects.create(
                    no=_next_no(dt.date.today()), owner=owner, customer=customer,
                    valid_until=valid_until, payment_terms=payment_terms, note=note)
                QuotationItem.objects.bulk_create([
                    QuotationItem(quotation=q, name=it['name'], qty=it['qty'],
                                  unit_price=it['unit_price'], product_id=it.get('product_id'))
                    for it in items])
                return q
        except IntegrityError:
            if attempt == MAX_RETRY - 1:
                raise
    raise AssertionError('unreachable')


def replace_items(quotation: Quotation, items: list[dict]) -> Quotation:
    """草擬態整包換明細（驗收 2「改數量總額自己變」）。

    送出後的修改要留紀錄（原則 2）——那是「送出」那本規格書的事；
    這裡先只放行草擬態，免得偷做一半把原則弄瞎。
    """
    if quotation.status != Quotation.Status.DRAFT:
        raise InvalidQuotation('只有草擬中的報價單能在這裡改；送出後的修改走送出流程（會留紀錄）')
    if not items:
        raise InvalidQuotation('明細至少要有一行')
    for it in items:
        if Decimal(str(it['qty'])) <= 0:
            raise InvalidQuotation('數量必須大於 0')
    with transaction.atomic():
        quotation.items.all().delete()
        QuotationItem.objects.bulk_create([
            QuotationItem(quotation=quotation, name=it['name'], qty=it['qty'],
                          unit_price=it['unit_price'], product_id=it.get('product_id'))
            for it in items])
    return quotation
