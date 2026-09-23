"""挑商品用：搜尋＋分頁（建改商品屬商品模組自己的規格書，這裡只給挑選框查詢）。"""
from ninja import Router, Schema
from ninja.security import django_auth

from apps._common.pagination import paginate

from .models import Product

router = Router(tags=['products'], auth=django_auth)


class ProductOut(Schema):
    id: int
    name: str
    default_price: int


class ProductPage(Schema):
    items: list[ProductOut]
    count: int


@router.get('', response=ProductPage)
def list_products(request, search: str = '', page: int = 1, page_size: int = 8):
    qs = Product.objects.all()
    if search := search.strip():
        qs = qs.filter(name__icontains=search)
    items, count = paginate(qs.order_by('name', 'id'), page, page_size)
    return {'items': items, 'count': count}
