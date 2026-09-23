"""報價單的動作（系統總覽・規格）。

- sp_create 確認建立：客戶選取引用、品項選取商品、數量最小 1；單價一律從商品帶入（rule_price_from_product），
  前端送什麼單價都不收；單號 Q-日期-流水（apps/_common/serial.py）；日期帶今天、業務帶登入者、狀態草稿。
- 編輯：只有草稿能改（rule_sent_locked）。已經在單上的商品保留建立時的單價，新加的才從商品帶入。
- sp_pdf 匯出 PDF：草稿 → 已送出、送出日期記今天；已送出的單再匯出只是再下載一次，狀態不動。
"""
import datetime as dt

from django.db import transaction

from apps._common import serial
from apps.products.models import Product

from .models import Quotation, QuotationItem

S = Quotation.Status


class InvalidQuotation(Exception):
    pass


def _is_no_collision(exc) -> bool:
    return serial.is_no_collision(exc, Quotation)


def _clean_items(items: list[dict]) -> list[dict]:
    """同一個商品只留一列（數量相加），並擋掉規格寫的失敗情況。"""
    if not items:
        raise InvalidQuotation('至少要有一個品項')
    merged: dict[int, int] = {}
    for it in items:
        qty = int(it['qty'])
        if qty < 1:
            raise InvalidQuotation('數量最小是 1')
        merged[it['product_id']] = merged.get(it['product_id'], 0) + qty
    found = {p.id: p for p in Product.objects.filter(id__in=merged)}
    missing = [pid for pid in merged if pid not in found]
    if missing:
        raise InvalidQuotation('有商品已經不存在，請重新選取')
    return [{'product': found[pid], 'qty': qty} for pid, qty in merged.items()]


def create_quotation(*, owner, customer, items: list[dict]) -> Quotation:
    rows = _clean_items(items)

    def build(no):
        q = Quotation.objects.create(no=no, owner=owner, customer=customer)
        QuotationItem.objects.bulk_create([
            QuotationItem(quotation=q, product=r['product'], qty=r['qty'], unit_price=r['product'].price)
            for r in rows])
        return q

    return serial.create_with_no(Quotation, 'Q', build)


def update_items(q: Quotation, items: list[dict]) -> Quotation:
    with transaction.atomic():
        q = Quotation.objects.select_for_update().get(pk=q.pk)
        if q.status != S.DRAFT:
            raise InvalidQuotation('已送出的報價單不能改')
        rows = _clean_items(items)
        kept = {i.product_id: i.unit_price for i in q.items.all()}   # 建立時帶入的單價，之後不變
        q.items.all().delete()
        QuotationItem.objects.bulk_create([
            QuotationItem(quotation=q, product=r['product'], qty=r['qty'],
                          unit_price=kept.get(r['product'].id, r['product'].price))
            for r in rows])
        q.save(update_fields=['updated_at'])
    return q


def export_pdf(q: Quotation) -> Quotation:
    """草稿 → 已送出，記送出日期；已送出的再匯出一次，狀態不動。"""
    with transaction.atomic():
        q = Quotation.objects.select_for_update().get(pk=q.pk)
        if not q.items.exists():
            raise InvalidQuotation('沒有品項不能匯出')
        if q.status == S.DRAFT:
            q.status = S.SENT
            q.sent_at = dt.date.today()
            q.save(update_fields=['status', 'sent_at', 'updated_at'])
    return q
