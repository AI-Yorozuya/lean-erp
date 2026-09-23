"""客戶的 API（系統總覽・頁面 customer_list、customer_detail、customer_picker）。

報價紀錄幾筆、最近一張報價從報價單反算，不存欄位。客戶沒有刪除：有報價單的客戶不能刪（rule_customer_has_quote）。
"""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps._common.pagination import paginate
from apps._common.roles import sales_only

from .models import Customer

router = Router(tags=['customers'], auth=sales_only)  # 銷售管理：業務


class CustomerIn(Schema):
    name: str
    contact: str = ''


class CustomerOut(Schema):
    id: int
    name: str
    contact: str
    quote_count: int
    last_quote_id: int | None
    last_quote_no: str | None

    @staticmethod
    def _last(obj):
        return obj.quotations.order_by('-date', '-no').first()

    @staticmethod
    def resolve_quote_count(obj):
        return obj.n_quotes if hasattr(obj, 'n_quotes') else obj.quotations.count()

    @staticmethod
    def resolve_last_quote_id(obj):
        q = CustomerOut._last(obj)
        return q.id if q else None

    @staticmethod
    def resolve_last_quote_no(obj):
        q = CustomerOut._last(obj)
        return q.no if q else None


class CustomerPage(Schema):
    items: list[CustomerOut]
    count: int


def _clean(data: CustomerIn) -> dict:
    name = data.name.strip()
    if not name:
        raise HttpError(400, '名稱不能空白')
    return {'name': name, 'contact': data.contact.strip()}


@router.get('', response=CustomerPage)
def list_customers(request, search: str = '', page: int = 1, page_size: int = 20):
    qs = Customer.objects.annotate(n_quotes=Count('quotations'))
    if search := search.strip():
        qs = qs.filter(Q(name__icontains=search) | Q(contact__icontains=search))
    items, count = paginate(qs.order_by('name', 'id'), page, page_size)
    return {'items': items, 'count': count}


@router.get('/{customer_id}', response=CustomerOut)
def get_customer(request, customer_id: int):
    return get_object_or_404(Customer, id=customer_id)


@router.post('', response=CustomerOut)
def create_customer(request, data: CustomerIn):
    return Customer.objects.create(**_clean(data))


@router.put('/{customer_id}', response=CustomerOut)
def save_customer(request, customer_id: int, data: CustomerIn):
    c = get_object_or_404(Customer, id=customer_id)
    for k, v in _clean(data).items():
        setattr(c, k, v)
    c.save()
    return c
