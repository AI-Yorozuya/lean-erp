"""報價單的動作：建立、改明細、送出／收回、點結果（規格：intents/ 同名規格書；原則照 intents/架構圖.md）。

- 建立報價單.md：單號 Q＋日期＋三碼流水（原則 6，取號在 apps/_common/serial.py）。
- 送出與收回.md：狀態轉移＋修改紀錄；送出後可改、每次改都留紀錄（原則 2），不鎖單、鎖的是歷史。
- 點結果.md：成交／沒成／點錯改回，退回也是修改（原則 4）。
- 動別人負責的單一律留紀錄，寫明是誰做的（原則 3）。
"""
import datetime as dt
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps._common import serial
from apps.changelog.models import record
from apps.products.models import Product

from .models import Quotation, QuotationItem

S = Quotation.Status

# 欄位上界。擋不住就會在 DB 那層炸成 DataError / CHECK 違反——那是 500，使用者只看到
# 「失敗」不知道哪裡填錯。所以擋在這裡回 400，把話講清楚。
_QTY_FIELD = QuotationItem._meta.get_field('qty')
QTY_MAX = Decimal(10) ** (_QTY_FIELD.max_digits - _QTY_FIELD.decimal_places)  # numeric(8,2) → 要小於 10^6
UNIT_PRICE_MAX = 2_147_483_647  # PositiveIntegerField 是 32-bit


class InvalidQuotation(Exception):
    pass


def _is_no_collision(exc: IntegrityError) -> bool:
    """撞單號才值得重試（其他 IntegrityError——例如 FK 在 commit 才炸——立刻往上丟）。"""
    return serial.is_no_collision(exc, Quotation)


def _validate_items(items: list[dict]) -> None:
    """開單與換明細共用的守門——只留一份，免得兩邊漂開。"""
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
    product_ids = {it['product_id'] for it in items if it.get('product_id') is not None}
    if product_ids:
        alive = set(Product.objects.filter(id__in=product_ids).values_list('id', flat=True))
        missing = sorted(product_ids - alive)
        if missing:
            raise InvalidQuotation(
                f'來源商品已不存在（id={"、".join(map(str, missing))}），請重新挑一次')


def _build_items(quotation, items):
    QuotationItem.objects.bulk_create([
        QuotationItem(quotation=quotation, name=it['name'], qty=it['qty'],
                      unit_price=it['unit_price'], product_id=it.get('product_id'))
        for it in items])


def create_quotation(*, owner, customer, items: list[dict],
                     valid_until=None, payment_terms='完工後三日內付款', note='') -> Quotation:
    _validate_items(items)

    def build(no):
        q = Quotation.objects.create(no=no, owner=owner, customer=customer,
                                     valid_until=valid_until, payment_terms=payment_terms, note=note)
        _build_items(q, items)
        return q

    return serial.create_with_no(Quotation, 'Q', build)


# ---------- 改明細（原則 2、3） ----------

def _fmt_qty(q) -> str:
    q = Decimal(str(q))
    return f'{q.normalize():f}' if q != q.to_integral() else f'{int(q)}'


def describe_item_changes(old: list[dict], new: list[dict]) -> str:
    """把「改了什麼」寫成人看得懂的幾行：哪一行數量／單價從多少到多少、加了什麼、拿掉什麼、總額變化。

    以品名對行（同名只比第一行）——紀錄是給人看的，不是給機器還原的。
    """
    def key(rows):
        d = {}
        for r in rows:
            d.setdefault(r['name'], r)
        return d

    o, n = key(old), key(new)
    lines = []
    for name, r in n.items():
        if name not in o:
            lines.append(f'新增 {name}：數量 {_fmt_qty(r["qty"])}、單價 {int(r["unit_price"]):,}')
            continue
        was, diffs = o[name], []
        if Decimal(str(was['qty'])) != Decimal(str(r['qty'])):
            diffs.append(f'數量 {_fmt_qty(was["qty"])}→{_fmt_qty(r["qty"])}')
        if int(was['unit_price']) != int(r['unit_price']):
            diffs.append(f'單價 {int(was["unit_price"]):,}→{int(r["unit_price"]):,}')
        if diffs:
            lines.append(f'{name}：' + '、'.join(diffs))
    for name in o:
        if name not in n:
            lines.append(f'移除 {name}')

    def total(rows):
        return sum(Decimal(str(r['qty'])) * int(r['unit_price']) for r in rows)
    t0, t1 = total(old), total(new)
    if t0 != t1:
        lines.append(f'總額 {int(t0):,}→{int(t1):,}')
    return '\n'.join(lines) or '明細重存，內容沒變'


def _must_record(quotation, actor) -> bool:
    return quotation.status != S.DRAFT or (actor is not None and actor.pk != quotation.owner_id)


def _current_items(quotation):
    return [{'name': i.name, 'qty': i.qty, 'unit_price': i.unit_price} for i in quotation.items.all()]


def update_quotation(quotation: Quotation, *, items, valid_until, payment_terms, note, actor) -> Quotation:
    """詳細頁編輯存檔：表頭三欄＋明細一起存；要留紀錄時（同 replace_items 的條件）寫成一筆。"""
    _validate_items(items)
    old_items = _current_items(quotation)
    lines = []
    fmt = lambda d: f'{d:%Y-%m-%d}' if d else '不設限'
    if quotation.valid_until != valid_until:
        lines.append(f'有效期限 {fmt(quotation.valid_until)}→{fmt(valid_until)}')
    if quotation.payment_terms != payment_terms:
        lines.append(f'付款條件 {quotation.payment_terms or "（空）"}→{payment_terms or "（空）"}')
    if quotation.note != note:
        lines.append('備註改了')
    item_desc = describe_item_changes(old_items, items)
    if item_desc != '明細重存，內容沒變':
        lines.append(item_desc)
    with transaction.atomic():
        quotation.valid_until, quotation.payment_terms, quotation.note = valid_until, payment_terms, note
        quotation.save(update_fields=['valid_until', 'payment_terms', 'note', 'updated_at'])
        quotation.items.all().delete()
        _build_items(quotation, items)
        if lines and _must_record(quotation, actor):
            record(actor, quotation=quotation, action='修改', detail='\n'.join(lines))
    return quotation


def replace_items(quotation: Quotation, items: list[dict], actor=None) -> Quotation:
    """整包換明細。任何狀態都能改（送出後不鎖單，鎖的是歷史）。

    要留紀錄的時候（原則 2、3）：已經送出過的單，或改的人不是負責人。
    草擬中的單由負責人自己改，還在打草稿，不記。
    """
    _validate_items(items)
    old = _current_items(quotation)
    must_record = _must_record(quotation, actor)
    if must_record and actor is None:
        raise ValueError('送出後或動別人的單，一定要知道是誰改的')
    with transaction.atomic():
        quotation.items.all().delete()
        _build_items(quotation, items)
        quotation.save(update_fields=['updated_at'])
        if must_record:
            record(actor, quotation=quotation, action='改明細', detail=describe_item_changes(old, items))
    return quotation


# ---------- 狀態轉移（送出與收回、點結果；原則 4：退回也是修改） ----------

# 動作 → (允許的起點, 終點, 紀錄上寫的動作名)
TRANSITIONS = {
    'send':   ({S.DRAFT}, S.SENT, '送出'),
    'recall': ({S.SENT}, S.DRAFT, '收回'),
    'win':    ({S.SENT}, S.WON, '點成交'),
    'lose':   ({S.SENT}, S.LOST, '點沒成'),
    'reopen': ({S.WON, S.LOST}, S.SENT, '點錯改回'),
}

_NOT_ALLOWED = {
    'send': '只有草擬的報價單能送出',
    'recall': '只有已送出的報價單能收回',
    'win': '只有已送出的報價單能點結果',
    'lose': '只有已送出的報價單能點結果',
    'reopen': '只有已成交或沒成的報價單能點錯改回',
}


def allowed_actions(q: Quotation) -> list[str]:
    """這張單現在能按哪些鍵——畫面只照這份清單出按鈕（狀態不對的動作不出現）。"""
    acts = [a for a, (frm, _, _) in TRANSITIONS.items() if q.status in frm]
    if q.status == S.WON and q.active_order:
        acts.remove('reopen')          # 已轉成訂單：先作廢訂單才能改回
    if q.status == S.WON and not q.active_order:
        acts.append('convert')         # 已成交才能轉訂單（原則 5）
    return acts


def transition(q: Quotation, action: str, actor) -> Quotation:
    frm, to, label = TRANSITIONS[action]
    with transaction.atomic():
        q = Quotation.objects.select_for_update().get(pk=q.pk)
        if q.status not in frm:
            raise InvalidQuotation(_NOT_ALLOWED[action])
        if action == 'reopen' and q.active_order:
            raise InvalidQuotation(f'這張單已轉成訂單 {q.active_order.no}，要改回先把訂單作廢')
        before = q.get_status_display()
        q.status = to
        if action == 'send':
            q.sent_on = dt.date.today()
        elif action == 'recall':
            q.sent_on = None
        q.save(update_fields=['status', 'sent_on', 'updated_at'])
        detail = f'狀態 {before}→{q.get_status_display()}'
        if action == 'send':
            detail += f'，送出日 {q.sent_on:%Y-%m-%d}'
        if action == 'recall':
            detail += '，客戶手上那份 PDF 作廢'
        record(actor, quotation=q, action=label, detail=detail)
    return q
