"""訂單的 API（轉成訂單.md、訂單推進.md）。

- 轉單：POST ''（帶 quotation_id）
- 列表／詳細：GET ''（status）、GET /{id}
- 推進與退回：POST /{id}/start、finish、back、reopen；作廢：POST /{id}/void
"""
import datetime as dt
from decimal import Decimal

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from apps._common.pagination import paginate
from apps.changelog.schemas import LogOut
from apps.quotations.models import Quotation

from . import services
from .models import Order
from .services import InvalidOrder

router = Router(tags=['orders'], auth=django_auth)


class ConvertIn(Schema):
    quotation_id: int
    expected_delivery: dt.date | None = None


class ItemOut(Schema):
    name: str
    qty: Decimal
    unit_price: int
    subtotal: Decimal


class _Base(Schema):
    id: int
    no: str
    status: str
    status_display: str
    quotation_id: int
    quotation_no: str
    customer_name: str
    total: Decimal
    expected_delivery: dt.date | None
    created_at: dt.datetime

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_quotation_no(obj):
        return obj.quotation.no

    @staticmethod
    def resolve_customer_name(obj):
        return obj.quotation.customer.name


class OrderRow(_Base):
    pass


class OrderOut(_Base):
    items: list[ItemOut]
    actions: list[str]
    logs: list[LogOut]

    @staticmethod
    def resolve_actions(obj):
        return services.allowed_actions(obj)

    @staticmethod
    def resolve_logs(obj):
        return obj.logs.select_related('actor')


class ListOut(Schema):
    rows: list[OrderRow]
    count: int
    counts: dict[str, int]


def _qs():
    return Order.objects.select_related('quotation__customer').prefetch_related('items')


def _load(order_id: int) -> Order:
    return get_object_or_404(_qs(), id=order_id)


@router.get('', response=ListOut)
def list_(request, status: str = '', search: str = '', page: int = 1, page_size: int = 20):
    if status and status not in Order.Status.values:
        raise HttpError(400, f'沒有「{status}」這個狀態')
    qs = _qs()
    if status:
        qs = qs.filter(status=status)
    if search := search.strip():
        qs = qs.filter(Q(no__icontains=search) | Q(quotation__customer__name__icontains=search)
                       | Q(quotation__no__icontains=search))
    counts = {s.value: 0 for s in Order.Status}
    for row in Order.objects.values('status').annotate(n=Count('id')):
        counts[row['status']] = row['n']
    counts['all'] = sum(counts.values())
    rows, count = paginate(qs.order_by('-created_at', '-id'), page, page_size)
    return {'rows': rows, 'count': count, 'counts': counts}


@router.post('', response=OrderOut)
def convert(request, data: ConvertIn):
    q = get_object_or_404(Quotation, id=data.quotation_id)
    try:
        o = services.convert(q, request.user, expected_delivery=data.expected_delivery)
    except InvalidOrder as e:
        raise HttpError(400, str(e))
    return _load(o.id)


@router.get('/{order_id}', response=OrderOut)
def detail(request, order_id: int):
    return _load(order_id)


def _transition(request, order_id, action):
    o = get_object_or_404(Order, id=order_id)
    try:
        services.transition(o, action, request.user)
    except InvalidOrder as e:
        raise HttpError(400, str(e))
    return _load(o.id)


@router.post('/{order_id}/start', response=OrderOut)
def start(request, order_id: int):
    return _transition(request, order_id, 'start')


@router.post('/{order_id}/finish', response=OrderOut)
def finish(request, order_id: int):
    return _transition(request, order_id, 'finish')


@router.post('/{order_id}/back', response=OrderOut)
def back(request, order_id: int):
    return _transition(request, order_id, 'back')


@router.post('/{order_id}/reopen', response=OrderOut)
def reopen(request, order_id: int):
    return _transition(request, order_id, 'reopen')


@router.post('/{order_id}/void', response=OrderOut)
def void(request, order_id: int):
    return _transition(request, order_id, 'void')
