"""建立報價單的 API。負責人自動＝登入者，payload 不收 owner、不收 total——多給的欄位一律忽略。"""
import datetime as dt
from decimal import Decimal

from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from apps.customers.models import Customer

from .models import Quotation
from .services import InvalidQuotation, create_quotation, replace_items

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


class ItemOut(Schema):
    name: str
    qty: Decimal
    unit_price: int
    subtotal: Decimal


class QuotationOut(Schema):
    id: int
    no: str
    status: str
    customer_id: int
    customer_name: str
    owner_name: str
    total: Decimal
    days_left: int | None
    is_expired: bool
    valid_until: dt.date | None
    payment_terms: str
    note: str
    items: list[ItemOut]

    @staticmethod
    def resolve_customer_name(obj):
        return obj.customer.name

    @staticmethod
    def resolve_owner_name(obj):
        return obj.owner.shown_name


@router.post('', response=QuotationOut)
def create(request, data: QuotationIn):
    customer = get_object_or_404(Customer, id=data.customer_id)
    try:
        return create_quotation(
            owner=request.user, customer=customer,
            items=[i.dict() for i in data.items],
            valid_until=data.valid_until, payment_terms=data.payment_terms, note=data.note)
    except InvalidQuotation as e:
        raise HttpError(400, str(e))


@router.get('/{quotation_id}', response=QuotationOut)
def detail(request, quotation_id: int):
    return get_object_or_404(
        Quotation.objects.select_related('customer', 'owner').prefetch_related('items'),
        id=quotation_id)


@router.put('/{quotation_id}/items', response=QuotationOut)
def update_items(request, quotation_id: int, data: ItemsIn):
    q = get_object_or_404(Quotation, id=quotation_id)
    try:
        return replace_items(q, [i.dict() for i in data.items])
    except InvalidQuotation as e:
        raise HttpError(400, str(e))
