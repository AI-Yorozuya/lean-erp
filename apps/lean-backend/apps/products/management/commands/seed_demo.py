"""塞課程 3C 報價案例的假資料（紅線：零真實資料——全是編的）。

客戶、商品、報價單照課程範例專案的原型（intents/原型.html）：
弘遠科技、立群工程、安橋資訊、南方紡織；五個商品；三張已送出的報價單。
Q-20260901-003 裡 24" FHD 商用螢幕 單價 7,900、Q-20260715-002 單價 7,200——
那是當時的價，現在價目表是 6,800：單價建立時帶入、之後不變（rule_price_frozen）。
可重跑：已經有報價單就不再塞單。
"""
import datetime as dt

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.customers.models import Customer
from apps.products.models import Product
from apps.quotations.models import Quotation, QuotationItem

CUSTOMERS = [('弘遠科技', '陳志明'), ('立群工程', '王美玲'), ('安橋資訊', '李建宏'), ('南方紡織', '黃淑芬')]
PRODUCTS = [
    ('M27F-B2', '27" FHD 商用螢幕', 10000),
    ('M27Q-A1', '27" QHD 螢幕', 13500),
    ('M24F-B1', '24" FHD 商用螢幕', 6800),
    ('M32U-C1', '32" 4K 螢幕', 21000),
    ('NB14-I5', '14" 商用筆電 i5', 28900),
]
# 單號、客戶、日期、品項（型號, 數量, 當時單價）
QUOTES = [
    ('Q-20260715-002', '立群工程', dt.date(2026, 7, 15), [('M24F-B1', 12, 7200)]),
    ('Q-20260901-003', '弘遠科技', dt.date(2026, 9, 1),
     [('M27F-B2', 20, 10000), ('M32U-C1', 1, 21000), ('NB14-I5', 1, 28900), ('M24F-B1', 1, 7900)]),
    ('Q-20260903-004', '安橋資訊', dt.date(2026, 9, 3), [('M27F-B2', 10, 10000)]),
]


class Command(BaseCommand):
    help = '課程 3C 報價案例：業務帳號＋客戶＋商品＋三張已送出的報價單（可重跑，不重複建）'

    def handle(self, *args, **options):
        U = get_user_model()
        sales, created = U.objects.get_or_create(username='dev', defaults={'display_name': '林郁婷'})
        if created:
            sales.set_password('dev1234')
            sales.save()
            self.stdout.write('建了業務帳號 dev / dev1234（林郁婷）')

        C = {name: Customer.objects.get_or_create(name=name, defaults={'contact': contact})[0]
             for name, contact in CUSTOMERS}
        P = {model: Product.objects.get_or_create(model=model, defaults={'name': name, 'price': price})[0]
             for model, name, price in PRODUCTS}

        if Quotation.objects.exists():
            self.stdout.write(self.style.SUCCESS('seed 完成（報價單已存在，不再塞單）'))
            return
        with transaction.atomic():
            for no, cust, day, lines in QUOTES:
                q = Quotation.objects.create(no=no, customer=C[cust], date=day, owner=sales,
                                             status=Quotation.Status.SENT, sent_at=day)
                QuotationItem.objects.bulk_create([
                    QuotationItem(quotation=q, product=P[m], qty=qty, unit_price=price) for m, qty, price in lines])
        self.stdout.write(self.style.SUCCESS(f'seed 完成：報價單 {len(QUOTES)} 張'))
