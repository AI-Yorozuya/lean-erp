"""挑商品用（建改商品屬商品模組自己的規格書，這裡只給挑選框查詢）。"""
from ninja import Router, Schema
from ninja.security import django_auth

from .models import Product

router = Router(tags=['products'], auth=django_auth)


class ProductOut(Schema):
    id: int
    name: str
    default_price: int


@router.get('', response=list[ProductOut])
def list_products(request, search: str = ''):
    qs = Product.objects.all()
    if search:
        qs = qs.filter(name__icontains=search)
    return qs.order_by('name')[:20]
