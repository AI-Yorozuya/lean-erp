"""商品的 API（系統總覽・頁面 product_list、product_detail、product_picker）。

sp_product_save 商品詳細頁「儲存」：型號不能跟別的商品重複、名稱不能空白、單價大於 0；
失敗時資料不變。列表一定帶型號（rule_model_shown）。
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps._common.pagination import paginate
from apps._common.roles import sales_only

from .models import Product

router = Router(tags=['products'], auth=sales_only)  # 銷售管理：業務


class ProductIn(Schema):
    model: str
    name: str
    price: int


class ProductOut(Schema):
    id: int
    model: str
    name: str
    price: int


class ProductPage(Schema):
    items: list[ProductOut]
    count: int


def _clean(data: ProductIn, exclude_id=None) -> dict:
    model, name = data.model.strip(), data.name.strip()
    if not model:
        raise HttpError(400, '型號不能空白')
    if not name:
        raise HttpError(400, '名稱不能空白')
    if data.price <= 0:
        raise HttpError(400, '單價要大於 0')
    if Product.objects.filter(model__iexact=model).exclude(id=exclude_id).exists():
        raise HttpError(400, f'型號 {model} 已經有別的商品在用')
    return {'model': model, 'name': name, 'price': data.price}


@router.get('', response=ProductPage)
def list_products(request, search: str = '', page: int = 1, page_size: int = 20):
    qs = Product.objects.all()
    if search := search.strip():
        qs = qs.filter(Q(model__icontains=search) | Q(name__icontains=search))
    items, count = paginate(qs.order_by('model', 'id'), page, page_size)
    return {'items': items, 'count': count}


@router.get('/{product_id}', response=ProductOut)
def get_product(request, product_id: int):
    return get_object_or_404(Product, id=product_id)


@router.post('', response=ProductOut)
def create_product(request, data: ProductIn):
    return Product.objects.create(**_clean(data))


@router.put('/{product_id}', response=ProductOut)
def save_product(request, product_id: int, data: ProductIn):
    p = get_object_or_404(Product, id=product_id)
    for k, v in _clean(data, exclude_id=p.id).items():
        setattr(p, k, v)
    p.save()
    return p
