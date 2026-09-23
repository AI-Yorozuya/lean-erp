"""測試共用：建帳號、登入、開一張單。各規格書的測試都從這裡起手，不各寫一份。"""
import datetime as dt

from django.contrib.auth import get_user_model
from django.test import Client

from apps.customers.models import Customer
from apps.quotations.models import Quotation
from apps.quotations.services import create_quotation


def make_user(username='dev', display_name=None):
    user, created = get_user_model().objects.get_or_create(
        username=username, defaults={'display_name': display_name or username})
    if created:
        user.set_password('x')
        user.save()
    return user


def login(user) -> Client:
    c = Client()
    c.force_login(user)
    return c


def make_quotation(owner, *, customer=None, items=None, status=None, sent_on=None) -> Quotation:
    customer = customer or Customer.objects.create(name='王小明', phone='0912345678')
    q = create_quotation(owner=owner, customer=customer,
                         items=items or [{'name': '鋁框玻璃門', 'qty': 2, 'unit_price': 12000}])
    if status:
        q.status = status
        q.sent_on = sent_on if sent_on is not None else (
            dt.date.today() if status != Quotation.Status.DRAFT else None)
        q.save()
    return q
