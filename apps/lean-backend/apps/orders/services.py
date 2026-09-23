"""轉單、作廢、推進與退回（規格：intents/轉成訂單.md、intents/訂單推進.md）。"""
from django.db import IntegrityError, transaction

from apps._common import serial
from apps.changelog.models import record
from apps.quotations.models import Quotation

from .models import Order, OrderItem

OS = Order.Status
QS = Quotation.Status


class InvalidOrder(Exception):
    pass


def convert(quotation: Quotation, actor, expected_delivery=None) -> Order:
    """已成交的報價單轉成訂單（原則 5）：建訂單＋複製明細＋兩邊各留一筆紀錄。"""
    with transaction.atomic():
        q = Quotation.objects.select_for_update().get(pk=quotation.pk)
        if q.status != QS.WON:
            raise InvalidOrder(f'只有已成交的報價單能轉訂單——這張現在是「{q.get_status_display()}」')
        if q.active_order:
            raise InvalidOrder(f'這張報價單已經轉成訂單 {q.active_order.no}（一張報價只轉一張）')

        def build(no):
            o = Order.objects.create(no=no, quotation=q, expected_delivery=expected_delivery)
            OrderItem.objects.bulk_create([
                OrderItem(order=o, name=i.name, qty=i.qty, unit_price=i.unit_price)
                for i in q.items.all()])
            return o

        try:
            o = serial.create_with_no(Order, 'O', build)
        except IntegrityError:
            raise InvalidOrder('這張報價單剛剛已經被轉成訂單了，重新整理看看')
        record(actor, order=o, action='轉成訂單', detail=f'由報價單 {q.no} 轉出，狀態 待處理')
        record(actor, quotation=q, action='轉成訂單', detail=f'轉出訂單 {o.no}')
    return o


# 動作 → (允許的起點, 終點, 紀錄上寫的動作名)
TRANSITIONS = {
    'start':  (OS.PENDING, OS.PROCESSING, '開始處理'),
    'finish': (OS.PROCESSING, OS.DONE, '完成'),
    'back':   (OS.PROCESSING, OS.PENDING, '退回'),
    'reopen': (OS.DONE, OS.PROCESSING, '點錯改回'),
    'void':   (OS.PENDING, OS.VOID, '作廢'),
}

_NOT_ALLOWED = {
    'start': '只有待處理的訂單能開始處理',
    'finish': '只有處理中的訂單能按完成',
    'back': '只有處理中的訂單能退回待處理',
    'reopen': '只有完成的訂單能點錯改回',
    'void': '只有待處理的訂單能作廢——已開工的先退回待處理再作廢',
}


def allowed_actions(o: Order) -> list[str]:
    return [a for a, (frm, _, _) in TRANSITIONS.items() if o.status == frm]


def transition(o: Order, action: str, actor) -> Order:
    frm, to, label = TRANSITIONS[action]
    with transaction.atomic():
        o = Order.objects.select_for_update().get(pk=o.pk)
        if o.status != frm:
            raise InvalidOrder(_NOT_ALLOWED[action])
        before = o.get_status_display()
        o.status = to
        o.save(update_fields=['status', 'updated_at'])
        record(actor, order=o, action=label, detail=f'狀態 {before}→{o.get_status_display()}')
        if action == 'void':
            # 報價單本來就停在已成交；紀錄寫在報價單上，看報價單的人也知道訂單沒了、可以再轉
            record(actor, quotation=o.quotation, action='訂單作廢',
                   detail=f'訂單 {o.no} 作廢，報價單回到已成交，可再轉一張')
    return o
