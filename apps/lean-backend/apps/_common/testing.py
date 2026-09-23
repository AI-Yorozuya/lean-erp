"""測試共用：建帳號、登入、課程案例的客戶與商品、開一張單。"""
from django.contrib.auth import get_user_model
from django.test import Client

from apps.customers.models import Customer
from apps.products.models import Product
from apps.quotations.services import create_quotation


def make_user(username='dev', display_name='林郁婷'):
    user, created = get_user_model().objects.get_or_create(username=username, defaults={'display_name': display_name})
    if created:
        user.set_password('x')
        user.save()
    return user


def login(user) -> Client:
    c = Client()
    c.force_login(user)
    return c


def make_catalog():
    """課程範例的一個客戶、三個商品（27 吋螢幕 10,000、32 吋螢幕 21,000、24 吋螢幕 6,800）。"""
    cust = Customer.objects.create(name='弘遠科技', contact='陳志明')
    m27 = Product.objects.create(model='M27F-B2', name='27" FHD 商用螢幕', price=10000)
    m32 = Product.objects.create(model='M32U-C1', name='32" 4K 螢幕', price=21000)
    m24 = Product.objects.create(model='M24F-B1', name='24" FHD 商用螢幕', price=6800)
    return cust, m27, m32, m24


def make_quotation(owner, customer, lines):
    """lines：[(product, qty), …]"""
    return create_quotation(owner=owner, customer=customer,
                            items=[{'product_id': p.id, 'qty': qty} for p, qty in lines])
