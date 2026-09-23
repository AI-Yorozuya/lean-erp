"""建立報價單（規格：intents/建立報價單.md；原則照 intents/架構圖.md）。

單號 `Q` + 日期 + 三碼流水，同日連號不重複（原則 6）：
靠 DB unique 約束＋撞號重試——兩個人同秒開單，慢的那個撞 IntegrityError 再取號一次。
"""
import datetime as dt
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.products.models import Product

from .models import Quotation, QuotationItem

MAX_RETRY = 3

# 欄位上界。擋不住就會在 DB 那層炸成 DataError / CHECK 違反——那是 500，使用者只看到
# 「失敗」不知道哪裡填錯。所以擋在這裡回 400，把話講清楚。
_QTY_FIELD = QuotationItem._meta.get_field('qty')
QTY_MAX = Decimal(10) ** (_QTY_FIELD.max_digits - _QTY_FIELD.decimal_places)  # numeric(8,2) → 要小於 10^6
UNIT_PRICE_MAX = 2_147_483_647  # PositiveIntegerField 是 32-bit

# 撞號重試只認這一顆約束（postgres 對 unique=True 的自動命名：<table>_<column>_key）。
_NO_UNIQUE_CONSTRAINT = f'{Quotation._meta.db_table}_no_key'


class InvalidQuotation(Exception):
    pass


def _is_no_collision(exc: IntegrityError) -> bool:
    """這顆 IntegrityError 是不是「同秒開單撞單號」？

    只有撞號值得重試。其他 IntegrityError 重試三次也不會變好，只會把真正的原因吃掉、
    最後以 500 出去——而 postgres 的 FK 是 DEFERRABLE，明細帶了已被刪掉的 product_id
    要到 commit 才炸，正好落在重試迴圈裡。
    """
    diag = getattr(getattr(exc, '__cause__', None), 'diag', None)
    return _NO_UNIQUE_CONSTRAINT in (getattr(diag, 'constraint_name', None) or str(exc))


def _validate_items(items: list[dict]) -> None:
    """開單與換明細共用的守門——只留一份，免得兩邊漂開。

    原本 create_quotation 驗了 unit_price、replace_items 沒驗：同一筆 payload 走開單
    回 400（看得懂），走換明細卻讓 DB 的 CHECK 約束炸成 500（看不懂）。
    有兩份驗證就一定會漂開，所以合成一份。
    """
    if not items:
        raise InvalidQuotation('明細至少要有一行')

    for it in items:
        qty = Decimal(str(it['qty']))
        if qty <= 0:
            raise InvalidQuotation('數量必須大於 0')
        if qty >= QTY_MAX:
            raise InvalidQuotation(f'數量太大——每行要小於 {QTY_MAX:,.0f}')

        unit_price = int(it['unit_price'])
        if unit_price < 0:
            raise InvalidQuotation('單價不能是負數')
        if unit_price > UNIT_PRICE_MAX:
            raise InvalidQuotation(f'單價太大——要小於等於 {UNIT_PRICE_MAX:,}')

    # 來源商品：挑的就填、手打的就空（原則 8）。填了就得真的存在——挑選框開著的時候
    # 商品被刪掉，沒擋的話 FK 會在 commit 才違反，整筆存檔 rollback、前端只看到「失敗」。
    # （驗完到寫入之間還有極窄的競態窗；那一顆會走 _is_no_collision 立刻往上丟，不再空轉重試。）
    product_ids = {it['product_id'] for it in items if it.get('product_id') is not None}
    if product_ids:
        alive = set(Product.objects.filter(id__in=product_ids).values_list('id', flat=True))
        missing = sorted(product_ids - alive)
        if missing:
            raise InvalidQuotation(
                f'來源商品已不存在（id={"、".join(map(str, missing))}），請重新挑一次')


def _next_no(today: dt.date) -> str:
    prefix = f'Q{today:%Y%m%d}'
    last = (Quotation.objects.filter(no__startswith=prefix)
            .order_by('-no').values_list('no', flat=True).first())
    seq = int(last.rsplit('-', 1)[1]) + 1 if last else 1
    return f'{prefix}-{seq:03d}'


def create_quotation(*, owner, customer, items: list[dict],
                     valid_until=None, payment_terms='完工後三日內付款', note='') -> Quotation:
    _validate_items(items)

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
        except IntegrityError as e:
            # 只有撞號值得再取一次號；別的立刻往上丟，不要重試三次再把原因吃掉。
            if not _is_no_collision(e) or attempt == MAX_RETRY - 1:
                raise
    raise AssertionError('unreachable')


def replace_items(quotation: Quotation, items: list[dict]) -> Quotation:
    """草擬態整包換明細（驗收 2「改數量總額自己變」）。

    送出後的修改要留紀錄（原則 2）——那是「送出」那本規格書的事；
    這裡先只放行草擬態，免得偷做一半把原則弄瞎。
    """
    if quotation.status != Quotation.Status.DRAFT:
        raise InvalidQuotation('只有草擬中的報價單能在這裡改；送出後的修改走送出流程（會留紀錄）')
    _validate_items(items)
    with transaction.atomic():
        quotation.items.all().delete()
        QuotationItem.objects.bulk_create([
            QuotationItem(quotation=quotation, name=it['name'], qty=it['qty'],
                          unit_price=it['unit_price'], product_id=it.get('product_id'))
            for it in items])
    return quotation
