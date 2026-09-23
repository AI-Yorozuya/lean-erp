"""挑客戶用：搜尋＋分頁＋當場建（主流程①：清單沒有→填名字＋電話存成新客戶）。"""
from django.db.models import Q
from ninja import Router, Schema
from ninja.security import django_auth

from apps._common.pagination import paginate

from .models import Customer

router = Router(tags=['customers'], auth=django_auth)


class CustomerIn(Schema):
    name: str
    phone: str
    note: str = ''


class CustomerOut(Schema):
    id: int
    name: str
    phone: str
    note: str


class CustomerPage(Schema):
    items: list[CustomerOut]
    count: int


@router.get('', response=CustomerPage)
def list_customers(request, search: str = '', page: int = 1, page_size: int = 8):
    qs = Customer.objects.all()
    if search := search.strip():
        qs = qs.filter(Q(name__icontains=search) | Q(phone__icontains=search))
    items, count = paginate(qs.order_by('-updated_at', '-id'), page, page_size)
    return {'items': items, 'count': count}


@router.post('', response=CustomerOut)
def create_customer(request, data: CustomerIn):
    return Customer.objects.create(name=data.name.strip(), phone=data.phone.strip(), note=data.note.strip())
