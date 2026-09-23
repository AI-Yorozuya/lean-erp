"""業績：系統總覽 sp_stats 的驗收（test_stats_*）＋原則 rule_boss_view_only。"""
import datetime as dt

from django.test import TestCase

from apps._common.testing import login, make_catalog, make_quotation, make_user
from apps.accounts.models import User
from apps.products.models import Product
from apps.quotations.models import Quotation

API = '/api/v1/reports/stats'


def sent(q, day):
    Quotation.objects.filter(id=q.id).update(status=Quotation.Status.SENT, sent_at=day)


class StatsTests(TestCase):
    def setUp(self):
        self.sales = make_user()
        self.boss = make_user('boss', '老闆')
        User.objects.filter(id=self.boss.id).update(role=User.Role.BOSS)
        self.boss.refresh_from_db()
        self.cust, self.m27, self.m32, self.m24 = make_catalog()
        nb = Product.objects.create(model='NB14-I5', name='14" 商用筆電 i5', price=28900)
        # 照課程示範資料的三張已送出報價單（24 吋當時的單價是 7,900、7,200，品項存的是當時的價）
        q1 = make_quotation(self.sales, self.cust, [(self.m27, 20), (self.m32, 1), (nb, 1), (self.m24, 1)])
        q1.items.filter(product=self.m24).update(unit_price=7900)
        sent(q1, dt.date(2026, 9, 1))                                              # 257,800
        sent(make_quotation(self.sales, self.cust, [(self.m27, 10)]), dt.date(2026, 9, 3))   # 100,000
        q3 = make_quotation(self.sales, self.cust, [(self.m24, 12)])
        q3.items.update(unit_price=7200)
        sent(q3, dt.date(2026, 7, 15))                                             # 86,400

    def test_stats_ok(self):
        """老闆打開業績頁，2026 年 9 月那一列：報價張數 2、報價總額 357,800。"""
        r = login(self.boss).get(API)
        self.assertEqual(r.status_code, 200, r.content)
        rows = r.json()
        self.assertEqual([x['month'] for x in rows], ['2026-09-01', '2026-07-01'])
        self.assertEqual((rows[0]['quote_count'], rows[0]['quote_total']), (2, 357800))
        self.assertEqual((rows[1]['quote_count'], rows[1]['quote_total']), (1, 86400))

    def test_stats_no(self):
        """業務開一張草稿不匯出，9 月仍是 2 張、357,800；老闆想改報價單做不到。"""
        make_quotation(self.sales, self.cust, [(self.m32, 50)])       # 草稿，沒送出
        rows = login(self.boss).get(API).json()
        self.assertEqual((rows[0]['quote_count'], rows[0]['quote_total']), (2, 357800))
        q = Quotation.objects.first()
        r = login(self.boss).put(f'/api/v1/quotations/{q.id}', {'items': [{'product_id': self.m27.id, 'qty': 1}]},
                                 content_type='application/json')
        self.assertEqual(r.status_code, 403)

    def test_rule_boss_view_only(self):
        """老闆只能看業績，不能改報價單：銷售管理的每一支都擋老闆；業績頁擋業務。"""
        boss = login(self.boss)
        q = Quotation.objects.first()
        for method, url, body in [
            ('get', '/api/v1/quotations', None),
            ('post', '/api/v1/quotations', {'customer_id': self.cust.id, 'items': [{'product_id': self.m27.id, 'qty': 1}]}),
            ('put', f'/api/v1/quotations/{q.id}', {'items': [{'product_id': self.m27.id, 'qty': 1}]}),
            ('post', f'/api/v1/quotations/{q.id}/pdf', None),
            ('put', f'/api/v1/products/{self.m27.id}', {'model': 'X', 'name': 'X', 'price': 1}),
            ('put', f'/api/v1/customers/{self.cust.id}', {'name': 'X', 'contact': ''}),
        ]:
            r = getattr(boss, method)(url, body, content_type='application/json') if body else getattr(boss, method)(url)
            self.assertEqual(r.status_code, 403, f'{method} {url}')
        self.assertEqual(login(self.sales).get(API).status_code, 403)
        self.assertEqual(self.client.get(API).status_code, 401)
