"""報價單的 API（系統總覽・頁面 quote_list、quote_detail）。

- 列表：GET ''（status、search、page、page_size）；搜單號、客戶名、商品型號或品名
- 確認建立：POST ''——只收 customer_id 與品項的 product_id、qty；單價、業務、日期、狀態都由系統帶
- 詳細：GET /{id}
- 編輯（只有草稿）：PUT /{id}
- 匯出 PDF：POST /{id}/pdf——草稿轉已送出、回 PDF 檔
"""
import datetime as dt

from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps._common.pagination import paginate
from apps._common.roles import sales_only
from apps.customers.models import Customer

from . import services
from .models import Quotation
from .pdf import render_quotation

router = Router(tags=['quotations'], auth=sales_only)  # 銷售管理：業務


class ItemIn(Schema):
    product_id: int
    qty: int


class QuotationIn(Schema):
    customer_id: int
    items: list[ItemIn]


class ItemsIn(Schema):
    items: list[ItemIn]


class ItemOut(Schema):
    product_id: int
    model: str
    name: str
    qty: int
    unit_price: int
    subtotal: int

    @staticmethod
    def resolve_model(obj):
        return obj.product.model

    @staticmethod
    def resolve_name(obj):
        return obj.product.name


class QuotationRow(Schema):
    id: int
    no: str
    customer_id: int
    customer_name: str
    date: dt.date
    sales_name: str
    status: str
    status_display: str
    sent_at: dt.date | None
    total: int

    @staticmethod
    def resolve_customer_name(obj):
        return obj.customer.name

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()


class QuotationOut(QuotationRow):
    customer_contact: str
    free_shipping: bool
    items: list[ItemOut]

    @staticmethod
    def resolve_customer_contact(obj):
        return obj.customer.contact

    @staticmethod
    def resolve_items(obj):
        return obj.items.select_related('product')


class ListOut(Schema):
    rows: list[QuotationRow]
    count: int
    counts: dict[str, int]


def _qs():
    return Quotation.objects.select_related('customer', 'owner').prefetch_related('items')


def _load(quotation_id: int) -> Quotation:
    return get_object_or_404(_qs(), id=quotation_id)


@router.get('', response=ListOut)
def list_(request, status: str = '', search: str = '', page: int = 1, page_size: int = 20):
    if status and status not in Quotation.Status.values:
        raise HttpError(400, f'沒有「{status}」這個狀態')
    qs = _qs()
    if status:
        qs = qs.filter(status=status)
    if search := search.strip():
        qs = qs.filter(Q(no__icontains=search) | Q(customer__name__icontains=search)
                       | Q(items__product__name__icontains=search)
                       | Q(items__product__model__icontains=search)).distinct()
    rows, count = paginate(qs.order_by('-date', '-no'), page, page_size)
    counts = {s.value: 0 for s in Quotation.Status}
    for row in Quotation.objects.values('status').annotate(n=Count('id')):
        counts[row['status']] = row['n']
    counts['all'] = sum(counts.values())
    return {'rows': rows, 'count': count, 'counts': counts}


@router.post('', response=QuotationOut)
def create(request, data: QuotationIn):
    customer = get_object_or_404(Customer, id=data.customer_id)
    try:
        q = services.create_quotation(owner=request.user, customer=customer,
                                      items=[i.dict() for i in data.items])
    except services.InvalidQuotation as e:
        raise HttpError(400, str(e))
    return _load(q.id)


@router.get('/{quotation_id}', response=QuotationOut)
def detail(request, quotation_id: int):
    return _load(quotation_id)


@router.put('/{quotation_id}', response=QuotationOut)
def update(request, quotation_id: int, data: ItemsIn):
    q = get_object_or_404(Quotation, id=quotation_id)
    try:
        services.update_items(q, [i.dict() for i in data.items])
    except services.InvalidQuotation as e:
        raise HttpError(400, str(e))
    return _load(q.id)


@router.post('/{quotation_id}/pdf')
def export_pdf(request, quotation_id: int):
    q = get_object_or_404(Quotation, id=quotation_id)
    try:
        q = services.export_pdf(q)
    except services.InvalidQuotation as e:
        raise HttpError(400, str(e))
    q = _load(q.id)
    resp = HttpResponse(render_quotation(q), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{q.no}.pdf"'
    return resp
