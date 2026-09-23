"""塞一組假資料讓系統一開就能玩（紅線：零真實資料——全是編的）。

帳號兩個（dev、amy），好示範「動別人的單會留紀錄」；報價單各狀態都有一張以上，
列表的盯單排序、查舊價、訂單推進打開就看得到。可重跑：已經有報價單就不再塞單。
"""
import datetime as dt

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps._common import serial
from apps.changelog.models import ChangeLog
from apps.customers.models import Customer
from apps.orders import services as orders
from apps.products.models import Product
from apps.quotations import services as quotes
from apps.quotations.models import Quotation


def user(username, name):
    U = get_user_model()
    u, created = U.objects.get_or_create(username=username, defaults={'display_name': name})
    if created:
        u.set_password(f'{username}1234')
        u.save()
    return u, created


class Command(BaseCommand):
    help = '假資料：dev／amy 帳號＋示範商品＋示範客戶＋各狀態報價單與訂單（可重跑，不重複建）'

    def handle(self, *args, **options):
        dev, c1 = user('dev', '示範帳號')
        amy, c2 = user('amy', '艾美')
        if c1 or c2:
            self.stdout.write('帳號 dev / dev1234、amy / amy1234')

        P = {}
        for name, price in [('到府安裝工資（半天）', 3500), ('鋁框玻璃門', 12000),
                            ('五金零件包', 800), ('丈量出圖', 1500), ('舊品拆除清運', 2000)]:
            P[name], _ = Product.objects.get_or_create(name=name, defaults={'default_price': price})
        C = {}
        for name, phone in [('王小明', '0912345678'), ('陳大同水電行', '0987654321'),
                            ('林太太', '0933222111')]:
            C[name], _ = Customer.objects.get_or_create(name=name, phone=phone)

        if Quotation.objects.exists():
            self.stdout.write(self.style.SUCCESS('seed 完成（報價單已存在，不再塞單）'))
            return

        def line(name, qty):
            p = P[name]
            return {'name': name, 'qty': qty, 'unit_price': p.default_price, 'product_id': p.id}

        today = dt.date.today()

        def q(owner, cust, items, days_ago=None, then=(), valid_days=30):
            obj = quotes.create_quotation(owner=owner, customer=C[cust], items=items,
                                          valid_until=today + dt.timedelta(days=valid_days))
            for act in ('send', *then) if days_ago is not None else ():
                quotes.transition(obj, act, owner)
            if days_ago is not None:
                d = today - dt.timedelta(days=days_ago)   # 單號日期跟著送出日走，看起來才像真的
                Quotation.objects.filter(id=obj.id).update(sent_on=d, no=serial.next_no(Quotation, 'Q', d))
                # 紀錄的時間與內容也跟著送出日走，不然紀錄寫今天送出、單子寫三週前送出
                at = dt.datetime.combine(d, dt.time(10, 0), tzinfo=dt.timezone.utc)
                for log in ChangeLog.objects.filter(quotation=obj):
                    log.detail = log.detail.replace(f'{today:%Y-%m-%d}', f'{d:%Y-%m-%d}')
                    log.save(update_fields=['detail'])
                ChangeLog.objects.filter(quotation=obj).update(created_at=at)
            return obj

        with transaction.atomic():
            q(dev, '林太太', [line('丈量出圖', 1)])                                        # 草擬
            q(dev, '王小明', [line('鋁框玻璃門', 2), line('到府安裝工資（半天）', 1)],
              days_ago=22, valid_days=-1)                                                   # 已送出、掛最久、已過期
            q(amy, '陳大同水電行', [line('五金零件包', 10), line('到府安裝工資（半天）', 2)],
              days_ago=12)                                                                  # 已送出
            sent = q(amy, '林太太', [line('舊品拆除清運', 1), line('鋁框玻璃門', 1)], days_ago=3)
            quotes.replace_items(sent, [line('舊品拆除清運', 1), line('鋁框玻璃門', 2)], actor=dev)  # 別人改：留紀錄
            won = q(dev, '陳大同水電行', [line('鋁框玻璃門', 4), line('到府安裝工資（半天）', 2)],
                    days_ago=15, then=('win',))                                             # 已成交→訂單處理中
            o = orders.convert(won, dev, expected_delivery=today + dt.timedelta(days=10))
            orders.transition(o, 'start', dev)
            q(amy, '王小明', [line('五金零件包', 3)], days_ago=30, then=('lose',))            # 沒成

        self.stdout.write(self.style.SUCCESS('seed 完成：報價單 6 張、訂單 1 張'))
