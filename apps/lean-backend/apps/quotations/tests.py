"""報價單：系統總覽的驗收（test_create_*、test_pdf_*）＋原則守護（test_rule_*）。

測試名＝系統總覽 tests[].id／principles[].id，對得回去。
原則 rule_total_sum 用 property-based（hypothesis）：隨機生品項組合打「總額＝品項加總」。
"""
import datetime as dt
import re
from types import SimpleNamespace

from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import Client, TestCase
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from apps._common.testing import login, make_catalog, make_quotation, make_user
from apps.customers.models import Customer
from apps.products.models import Product
from core.api import api

from .models import Quotation
from .services import _is_no_collision

API = '/api/v1/quotations'


class QuotationSpecTests(TestCase):
    """sp_create 確認建立、sp_pdf 匯出 PDF。"""

    def setUp(self):
        self.user = make_user()
        self.client = login(self.user)
        self.cust, self.m27, self.m32, self.m24 = make_catalog()

    def create(self, lines, **extra):
        payload = {'customer_id': self.cust.id,
                   'items': [{'product_id': p.id, 'qty': q, **extra} for p, q in lines]}
        return self.client.post(API, payload, content_type='application/json')

    def test_create_ok(self):
        """選客戶，加 27 吋螢幕 20 台、32 吋螢幕 1 台，按確認建立，列表看到總額 221,000。"""
        r = self.create([(self.m27, 20), (self.m32, 1)])
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body['total'], 221000)
        self.assertTrue(body['free_shipping'])
        self.assertEqual(body['status'], 'draft')
        self.assertEqual(body['sales_name'], '林郁婷')
        self.assertEqual(body['date'], dt.date.today().isoformat())
        first = self.client.get(API).json()['rows'][0]
        self.assertEqual((first['no'], first['total']), (body['no'], 221000))

    def test_create_no(self):
        """想手改單價做不到，總額仍是 221,000。"""
        r = self.create([(self.m27, 20), (self.m32, 1)], unit_price=1)
        self.assertEqual(r.json()['total'], 221000)
        self.assertEqual([i['unit_price'] for i in r.json()['items']], [10000, 21000])

    def test_create_failures_keep_nothing(self):
        """sp_create 失敗：沒選客戶、沒有品項、數量小於 1 都不能建立。"""
        self.assertEqual(self.client.post(API, {'items': [{'product_id': self.m27.id, 'qty': 1}]},
                                          content_type='application/json').status_code, 422)
        r = self.create([])
        self.assertEqual(r.status_code, 400)
        self.assertIn('至少要有一個品項', r.json()['detail'])
        r = self.create([(self.m27, 0)])
        self.assertEqual(r.status_code, 400)
        self.assertIn('數量最小是 1', r.json()['detail'])
        self.assertEqual(Quotation.objects.count(), 0)

    def test_pdf_ok(self):
        """匯出後重開這張單，狀態已送出、PDF 總額 221,000。"""
        q = self.create([(self.m27, 20), (self.m32, 1)]).json()
        pdf = self.client.post(f'{API}/{q["id"]}/pdf')
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        again = self.client.get(f'{API}/{q["id"]}').json()
        self.assertEqual(again['status'], 'sent')
        self.assertEqual(again['sent_at'], dt.date.today().isoformat())
        self.assertEqual(again['total'], 221000)

    def test_pdf_no(self):
        """已送出的單按編輯改不了；商品改價後重開這張單，單價仍是 10,000。"""
        q = self.create([(self.m27, 20), (self.m32, 1)]).json()
        self.client.post(f'{API}/{q["id"]}/pdf')
        r = self.client.put(f'{API}/{q["id"]}', {'items': [{'product_id': self.m27.id, 'qty': 1}]},
                            content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('已送出的報價單不能改', r.json()['detail'])
        Product.objects.filter(id=self.m27.id).update(price=12000)
        again = self.client.get(f'{API}/{q["id"]}').json()
        self.assertEqual(again['items'][0]['unit_price'], 10000)
        self.assertEqual(again['total'], 221000)

    def test_export_twice_keeps_first_sent_date(self):
        """已送出的再匯出一次只是再下載，狀態與送出日期不動。"""
        q = self.create([(self.m27, 1)]).json()
        self.client.post(f'{API}/{q["id"]}/pdf')
        Quotation.objects.filter(id=q['id']).update(sent_at=dt.date(2026, 9, 1))
        self.assertEqual(self.client.post(f'{API}/{q["id"]}/pdf').status_code, 200)
        self.assertEqual(Quotation.objects.get(id=q['id']).sent_at, dt.date(2026, 9, 1))

    def test_draft_edit_keeps_price_of_lines_already_on_the_quote(self):
        """草稿可以編輯：已經在單上的商品保留建立時的單價，新加的才照現價帶入。"""
        q = self.create([(self.m27, 1)]).json()
        Product.objects.filter(id=self.m27.id).update(price=12000)
        r = self.client.put(f'{API}/{q["id"]}', {'items': [
            {'product_id': self.m27.id, 'qty': 2}, {'product_id': self.m24.id, 'qty': 1}]},
            content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([(i['model'], i['unit_price']) for i in r.json()['items']],
                         [('M27F-B2', 10000), ('M24F-B1', 6800)])

    def test_list_status_and_search(self):
        a = make_quotation(self.user, self.cust, [(self.m27, 1)])
        b = make_quotation(self.user, self.cust, [(self.m32, 1)])
        self.client.post(f'{API}/{b.id}/pdf')
        nos = lambda **p: [r['no'] for r in self.client.get(API, p).json()['rows']]
        self.assertEqual(nos(status='draft'), [a.no])
        self.assertEqual(nos(status='sent'), [b.no])
        self.assertEqual(nos(search='M32U'), [b.no])
        self.assertEqual(nos(search='4K'), [b.no])
        self.assertEqual(self.client.get(API).json()['counts'], {'draft': 1, 'sent': 1, 'all': 2})


class PrincipleTests(TestCase):
    """系統總覽・原則：每條一個守護。"""

    def setUp(self):
        self.user = make_user()
        self.client = login(self.user)
        self.cust, self.m27, self.m32, self.m24 = make_catalog()

    def test_rule_customer_pick(self):
        """客戶只能選取引用：報價單只收 customer_id，打字的客戶名一律不收；不存在的客戶擋下。"""
        r = self.client.post(API, {'customer_id': 9999, 'customer_name': '亂打的公司',
                                   'items': [{'product_id': self.m27.id, 'qty': 1}]},
                             content_type='application/json')
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Customer.objects.filter(name='亂打的公司').exists())

    def test_rule_price_from_product(self):
        """單價一律取自商品：送出去的單價被忽略，帶入的是價目表的數字。"""
        r = self.client.post(API, {'customer_id': self.cust.id,
                                   'items': [{'product_id': self.m24.id, 'qty': 3, 'unit_price': 1}]},
                             content_type='application/json')
        self.assertEqual(r.json()['items'][0]['unit_price'], 6800)

    def test_rule_model_shown(self):
        """同名商品靠型號分：挑商品的清單、報價單品項都帶型號。"""
        Product.objects.create(model='M27F-B3', name='27" FHD 商用螢幕', price=9900)
        picks = self.client.get('/api/v1/products', {'search': '27" FHD'}).json()['items']
        self.assertEqual(sorted(p['model'] for p in picks), ['M27F-B2', 'M27F-B3'])
        q = make_quotation(self.user, self.cust, [(self.m27, 1)])
        self.assertEqual(self.client.get(f'{API}/{q.id}').json()['items'][0]['model'], 'M27F-B2')

    def test_rule_free_shipping(self):
        """滿十萬免運，剛好十萬也免運；差一塊就運費另計。"""
        cheap = Product.objects.create(model='T-1', name='測試品', price=1)
        exact = make_quotation(self.user, self.cust, [(self.m27, 10)])
        under = make_quotation(self.user, self.cust, [(self.m27, 9), (cheap, 9999)])
        self.assertEqual((exact.total, exact.free_shipping), (100000, True))
        self.assertEqual((under.total, under.free_shipping), (99999, False))

    def test_rule_sent_locked(self):
        """已送出的報價單不能改。"""
        q = make_quotation(self.user, self.cust, [(self.m27, 1)])
        self.client.post(f'{API}/{q.id}/pdf')
        r = self.client.put(f'{API}/{q.id}', {'items': [{'product_id': self.m27.id, 'qty': 5}]},
                            content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Quotation.objects.get(id=q.id).items.get().qty, 1)

    def test_rule_customer_has_quote(self):
        """有報價單的客戶不能刪。"""
        make_quotation(self.user, self.cust, [(self.m27, 1)])
        with self.assertRaises(ProtectedError):
            self.cust.delete()

    def test_rule_price_frozen(self):
        """已送出的報價單，單價不變；商品改價不影響舊單。"""
        q = make_quotation(self.user, self.cust, [(self.m27, 20)])
        self.client.post(f'{API}/{q.id}/pdf')
        self.client.put(f'/api/v1/products/{self.m27.id}', {'model': 'M27F-B2', 'name': '27" FHD 商用螢幕', 'price': 12000},
                        content_type='application/json')
        self.assertEqual(Quotation.objects.get(id=q.id).total, 200000)

    def test_serial_numbers_q_date_seq(self):
        """單號 Q-日期-三碼流水，同日連號不重複。"""
        a = make_quotation(self.user, self.cust, [(self.m27, 1)])
        b = make_quotation(self.user, self.cust, [(self.m27, 1)])
        today = f'{dt.date.today():%Y%m%d}'
        self.assertEqual((a.no, b.no), (f'Q-{today}-001', f'Q-{today}-002'))
        with self.assertRaises(IntegrityError):
            Quotation.objects.create(no=a.no, customer=self.cust, owner=self.user)


class TotalSumPropertyTests(HypothesisTestCase):
    """rule_total_sum 總額必須等於品項加總（隨機組合）。"""

    @hyp_settings(max_examples=40, deadline=None)
    @given(st.lists(st.tuples(st.integers(1, 5000), st.integers(1, 99)), min_size=1, max_size=6))
    def test_rule_total_sum(self, rows):
        user = make_user()
        cust = Customer.objects.create(name='客戶')
        lines = []
        for i, (price, qty) in enumerate(rows):
            lines.append((Product.objects.create(model=f'P-{Product.objects.count()}-{i}', name='品', price=price), qty))
        q = make_quotation(user, cust, lines)
        self.assertEqual(q.total, sum(price * qty for price, qty in rows))


class SerialCollisionTests(TestCase):
    """撞單號才重試；別的 IntegrityError 立刻往上丟。"""

    def _err(self, message, constraint_name=None):
        exc = IntegrityError(message)
        if constraint_name is not None:
            cause = Exception()
            cause.diag = SimpleNamespace(constraint_name=constraint_name)
            exc.__cause__ = cause
        return exc

    def test_serial_collision_is_retried(self):
        self.assertTrue(_is_no_collision(self._err('duplicate key "quotations_quotation_no_key"')))
        self.assertTrue(_is_no_collision(self._err('看不出來', constraint_name='quotations_quotation_no_key')))

    def test_other_integrity_errors_are_not_retried(self):
        self.assertFalse(_is_no_collision(self._err('violates check constraint "quote_item_qty_gte_1"')))


class EndpointAuthTests(TestCase):
    """結構守門：每支端點預設都要登入，公開的只有這裡明列的三支。"""

    PUBLIC = {('GET', '/api/v1/health'), ('GET', '/api/v1/auth/csrf'), ('POST', '/api/v1/auth/login')}

    def test_every_endpoint_requires_login_except_the_named_public_ones(self):
        anon = Client()
        seen = set()
        for prefix, router in api._routers:
            for path, path_view in router.path_operations.items():
                template = f'/api/v1{prefix}{path}'
                url = re.sub(r'\{[^}]+\}', '1', template)
                for op in path_view.operations:
                    for method in op.methods:
                        seen.add((method, template))
                        r = getattr(anon, method.lower())(url, content_type='application/json')
                        if (method, template) in self.PUBLIC:
                            self.assertNotEqual(r.status_code, 401, f'{method} {template} 應該是公開的')
                        else:
                            self.assertEqual(r.status_code, 401, f'{method} {template} 沒擋匿名')
        self.assertEqual(self.PUBLIC - seen, set(), '白名單列了已經不存在的端點')
