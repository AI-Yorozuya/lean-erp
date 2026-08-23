"""驗收 8 條（intents/建立報價單.md）逐條變測試＋原則測試（intents/架構圖.md 原則 1/6/7/8）。

原則 1 用 property-based（hypothesis）：隨機生明細組合打「總額＝Σ小計」這條不變量，
不是挑兩三組數字自我安慰。
"""
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import Client, TestCase
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase  # @given 要配它：每個 example 各自包 transaction

from apps.customers.models import Customer
from apps.products.models import Product

from .models import Quotation
from .services import create_quotation

API = '/api/v1/quotations'


def make_user(username='dev'):
    # get_or_create 冪等：hypothesis 的 TestCase 走 TransactionTestCase 清理時序，帳號可能跨測試殘留
    user, created = get_user_model().objects.get_or_create(
        username=username, defaults={'display_name': '開發者'})
    if created:
        user.set_password('x')
        user.save()
    return user


class CreateQuotationApiTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.customer = Customer.objects.create(name='王小明', phone='0912345678')
        self.client = Client()
        self.client.force_login(self.user)

    def post_quotation(self, items, **extra):
        payload = {'customer_id': self.customer.id, 'items': items, **extra}
        return self.client.post(API, payload, content_type='application/json')

    def test_ac1_create_shows_total_status_no(self):
        """驗收 1：兩行明細（2×1000、1×500）→ 總額 2500、狀態草擬、單號長 QYYYYMMDD-NNN。"""
        r = self.post_quotation([
            {'name': '安裝工資', 'qty': 2, 'unit_price': 1000},
            {'name': '零件', 'qty': 1, 'unit_price': 500},
        ])
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(Decimal(body['total']), Decimal('2500'))
        self.assertEqual(body['status'], 'draft')
        self.assertRegex(body['no'], r'^Q\d{8}-\d{3}$')

    def test_ac2_change_qty_recomputes_and_total_not_writable(self):
        """驗收 2：改數量總額自己變；payload 塞 total 也沒有任何地方收它。"""
        r = self.post_quotation([{'name': 'A', 'qty': 2, 'unit_price': 1000},
                                 {'name': 'B', 'qty': 1, 'unit_price': 500}])
        qid = r.json()['id']
        r2 = self.client.put(
            f'{API}/{qid}/items',
            {'items': [{'name': 'A', 'qty': 3, 'unit_price': 1000},
                       {'name': 'B', 'qty': 1, 'unit_price': 500}],
             'total': 99},  # 惡意塞總額——schema 沒這欄位，一律忽略
            content_type='application/json')
        self.assertEqual(Decimal(r2.json()['total']), Decimal('3500'))

    def test_ac3_no_items_rejected_with_reason(self):
        r = self.post_quotation([])
        self.assertEqual(r.status_code, 400)
        self.assertIn('明細至少要有一行', r.json()['detail'])

    def test_ac4_zero_or_negative_qty_rejected(self):
        for bad in (0, -1):
            r = self.post_quotation([{'name': 'A', 'qty': bad, 'unit_price': 100}])
            self.assertEqual(r.status_code, 400, f'qty={bad} 應被擋')

    def test_ac5_same_day_serial_numbers(self):
        """驗收 5＋原則 6：同日連開三張 → -001、-002、-003 不重複。"""
        nos = [self.post_quotation([{'name': 'A', 'qty': 1, 'unit_price': 100}]).json()['no']
               for _ in range(3)]
        self.assertEqual([n.rsplit('-', 1)[1] for n in nos], ['001', '002', '003'])
        self.assertEqual(len(set(nos)), 3)

    def test_ac6_expired_shown_status_unchanged(self):
        r = self.post_quotation([{'name': 'A', 'qty': 1, 'unit_price': 100}],
                                valid_until='2020-01-01')
        body = self.client.get(f"{API}/{r.json()['id']}").json()
        self.assertTrue(body['is_expired'])
        self.assertEqual(body['status'], 'draft')  # 狀態不會自己變

    def test_ac7_anonymous_blocked(self):
        r = Client().post(API, {'customer_id': self.customer.id,
                                'items': [{'name': 'A', 'qty': 1, 'unit_price': 100}]},
                          content_type='application/json')
        self.assertEqual(r.status_code, 401)

    def test_ac8_owner_is_login_user_and_not_assignable(self):
        other = make_user('other')
        r = self.post_quotation([{'name': 'A', 'qty': 1, 'unit_price': 100}],
                                owner_id=other.id)  # 想指定別人——schema 沒這欄位
        body = self.client.get(f"{API}/{r.json()['id']}").json()
        self.assertEqual(body['owner_name'], '開發者')
        self.assertEqual(Quotation.objects.get(id=r.json()['id']).owner, self.user)


class PrincipleTests(HypothesisTestCase):
    """架構圖原則的直接測試（測試欄回填用）。"""

    def setUp(self):
        self.user = make_user()
        self.customer = Customer.objects.create(name='客', phone='0900000000')

    @hyp_settings(max_examples=30, deadline=None)
    @given(st.lists(
        st.tuples(st.decimals(min_value='0.01', max_value='999', places=2),
                  st.integers(min_value=0, max_value=10_000_000)),
        min_size=1, max_size=8))
    def test_principle_1_total_equals_sum(self, rows):
        """原則 1：總額＝明細加總——隨機明細組合下永真（property-based）。"""
        q = create_quotation(
            owner=self.user, customer=self.customer,
            items=[{'name': f'品{i}', 'qty': qty, 'unit_price': price}
                   for i, (qty, price) in enumerate(rows)])
        try:
            self.assertEqual(q.total, sum(qty * price for qty, price in rows))
        finally:
            q.delete()  # hypothesis 多輪共用 DB，砍掉避免單號堆積

    def test_principle_6_no_is_unique(self):
        """原則 6：單號唯一——DB unique 約束在，重試邏輯覆蓋同日撞號。"""
        self.assertTrue(Quotation._meta.get_field('no').unique)

    def test_principle_7_referenced_customer_undeletable(self):
        """原則 7：被引用的客戶不能硬刪（PROTECT）。"""
        create_quotation(owner=self.user, customer=self.customer,
                         items=[{'name': 'A', 'qty': 1, 'unit_price': 1}])
        with self.assertRaises(ProtectedError):
            self.customer.delete()

    def test_principle_8_snapshot_survives_product_change(self):
        """原則 8：明細存快照——來源商品改價，舊單金額一毛不動。"""
        p = Product.objects.create(name='保養包', default_price=1000)
        q = create_quotation(owner=self.user, customer=self.customer,
                             items=[{'name': p.name, 'qty': 2,
                                     'unit_price': p.default_price, 'product_id': p.id}])
        p.default_price = 9999
        p.save()
        q.refresh_from_db()
        self.assertEqual(q.total, 2000)
        self.assertEqual(q.items.first().unit_price, 1000)
