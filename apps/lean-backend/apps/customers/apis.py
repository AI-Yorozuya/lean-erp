"""挑客戶用：搜尋＋當場建（主流程①：清單沒有→填名字＋電話存成新客戶）。"""
from ninja import Router, Schema
from ninja.security import django_auth

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


@router.get('', response=list[CustomerOut])
def list_customers(request, search: str = ''):
    qs = Customer.objects.all()
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(phone__icontains=search)
    return qs.order_by('-updated_at')[:20]


@router.post('', response=CustomerOut)
def create_customer(request, data: CustomerIn):
    return Customer.objects.create(**data.dict())
