"""報價單的 API。負責人自動＝登入者，payload 不收 owner、不收 total——多給的欄位一律忽略。

端點對規格書：
- 建立報價單：POST ''、GET /{id}、PUT /{id}/items
- 報價單列表：GET ''（status、search）
- 送出與收回：POST /{id}/send、/{id}/recall、GET /{id}/pdf
- 點結果：POST /{id}/win、/{id}/lose、/{id}/reopen
"""
import datetime as dt
from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from apps._common.pagination import paginate
from apps.changelog.schemas import LogOut
from apps.customers.models import Customer

from . import queries, services
from .models import Quotation
from .pdf import render_quotation
from .services import InvalidQuotation, create_quotation, replace_items, update_quotation

router = Router(tags=['quotations'], auth=django_auth)


class ItemIn(Schema):
    name: str
    qty: Decimal
    unit_price: int
    product_id: int | None = None


class QuotationIn(Schema):
    customer_id: int
    items: list[ItemIn]
    valid_until: dt.date | None = None
    payment_terms: str = '完工後三日內付款'
    note: str = ''


class ItemsIn(Schema):
    items: list[ItemIn]


class QuotationUpdate(Schema):
    items: list[ItemIn]
    valid_until: dt.date | None = None
    payment_terms: str = ''
    note: str = ''


class ItemOut(Schema):
    name: str
    qty: Decimal
    unit_price: int
    subtotal: Decimal
    product_id: int | None


class OrderRef(Schema):
    id: int
    no: str
    status: str
    status_display: str

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()


class _Base(Schema):
    id: int
    no: str
    status: str
    status_display: str
    customer_id: int
    customer_name: str
    customer_phone: str
    owner_name: str
    total: Decimal
    sent_on: dt.date | None
    days_left: int | None
    is_expired: bool
    valid_until: dt.date | None

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_customer_name(obj):
        return obj.customer.name

    @staticmethod
    def resolve_customer_phone(obj):
        return obj.customer.phone

    @staticmethod
    def resolve_owner_name(obj):
        return obj.owner.shown_name


class QuotationRow(_Base):
    pass


class QuotationOut(_Base):
    payment_terms: str
    note: str
    items: list[ItemOut]
    actions: list[str]
    logs: list[LogOut]
    orders: list[OrderRef]

    @staticmethod
    def resolve_actions(obj):
        return services.allowed_actions(obj)

    @staticmethod
    def resolve_logs(obj):
        return obj.logs.select_related('actor')

    @staticmethod
    def resolve_orders(obj):
        return obj.orders.order_by('-id')


class ListOut(Schema):
    rows: list[QuotationRow]
    count: int
    counts: dict[str, int]


def _load(quotation_id: int) -> Quotation:
    return get_object_or_404(
        Quotation.objects.select_related('customer', 'owner').prefetch_related('items'),
        id=quotation_id)


@router.get('', response=ListOut)
def list_(request, status: str = '', search: str = '', page: int = 1, page_size: int = 20):
    if status and status not in Quotation.Status.values:
        raise HttpError(400, f'沒有「{status}」這個狀態')
    rows, count = paginate(queries.list_quotations(status=status, search=search.strip()), page, page_size)
    return {'rows': rows, 'count': count, 'counts': queries.status_counts()}


@router.post('', response=QuotationOut)
def create(request, data: QuotationIn):
    customer = get_object_or_404(Customer, id=data.customer_id)
    try:
        q = create_quotation(
            owner=request.user, customer=customer,
            items=[i.dict() for i in data.items],
            valid_until=data.valid_until, payment_terms=data.payment_terms, note=data.note)
    except InvalidQuotation as e:
        raise HttpError(400, str(e))
    return _load(q.id)


@router.get('/{quotation_id}', response=QuotationOut)
def detail(request, quotation_id: int):
    return _load(quotation_id)


@router.put('/{quotation_id}', response=QuotationOut)
def update(request, quotation_id: int, data: QuotationUpdate):
    """詳細頁「編輯」存檔：明細＋有效期限、付款條件、備註一起存，改了什麼寫成一筆紀錄。"""
    q = get_object_or_404(Quotation, id=quotation_id)
    try:
        update_quotation(q, items=[i.dict() for i in data.items], valid_until=data.valid_until,
                         payment_terms=data.payment_terms.strip(), note=data.note.strip(), actor=request.user)
    except InvalidQuotation as e:
        raise HttpError(400, str(e))
    return _load(q.id)


@router.put('/{quotation_id}/items', response=QuotationOut)
def update_items(request, quotation_id: int, data: ItemsIn):
    q = get_object_or_404(Quotation, id=quotation_id)
    try:
        replace_items(q, [i.dict() for i in data.items], actor=request.user)
    except InvalidQuotation as e:
        raise HttpError(400, str(e))
    return _load(q.id)


def _transition(request, quotation_id, action):
    q = get_object_or_404(Quotation, id=quotation_id)
    try:
        services.transition(q, action, request.user)
    except InvalidQuotation as e:
        raise HttpError(400, str(e))
    return _load(q.id)


@router.post('/{quotation_id}/send', response=QuotationOut)
def send(request, quotation_id: int):
    return _transition(request, quotation_id, 'send')


@router.post('/{quotation_id}/recall', response=QuotationOut)
def recall(request, quotation_id: int):
    return _transition(request, quotation_id, 'recall')


@router.post('/{quotation_id}/win', response=QuotationOut)
def win(request, quotation_id: int):
    return _transition(request, quotation_id, 'win')


@router.post('/{quotation_id}/lose', response=QuotationOut)
def lose(request, quotation_id: int):
    return _transition(request, quotation_id, 'lose')


@router.post('/{quotation_id}/reopen', response=QuotationOut)
def reopen(request, quotation_id: int):
    return _transition(request, quotation_id, 'reopen')


@router.get('/{quotation_id}/pdf')
def pdf(request, quotation_id: int):
    q = _load(quotation_id)
    resp = HttpResponse(render_quotation(q), content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{q.no}.pdf"'
    return resp
