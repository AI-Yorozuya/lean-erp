"""驗收 8 條（intents/建立報價單.md）逐條變測試＋原則測試（intents/架構圖.md 原則 1/6/7/8）。

原則 1 用 property-based（hypothesis）：隨機生明細組合打「總額＝Σ小計」這條不變量，
不是挑兩三組數字自我安慰。
"""
import re
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import Client, TestCase
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase  # @given 要配它：每個 example 各自包 transaction

from apps.customers.models import Customer
from apps.products.models import Product
from core.api import api

from .models import Quotation
from .services import _is_no_collision, create_quotation

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


class PayloadGuardTests(TestCase):
    """壞明細一律 400，而且開單與換明細給一樣的答案。

    這四條原本全是 500（DB 的 CHECK / numeric overflow / FK 直接往上噴）——
    使用者只看到「失敗」，不知道哪裡填錯。同款出現在 ns-erp 2026-08-27 的
    「畸形 payload 擋在 view 層」與「送到失效的 FK 會 500 + 整筆存檔 rollback」。
    """

    def setUp(self):
        self.user = make_user()
        self.customer = Customer.objects.create(name='王小明', phone='0912345678')
        self.client = Client()
        self.client.force_login(self.user)
        # 換明細要有一張草擬單可以改
        self.quotation = create_quotation(
            owner=self.user, customer=self.customer,
            items=[{'name': 'A', 'qty': 1, 'unit_price': 100}])

    def both_write_paths(self, items):
        """同一份明細分別走 POST 開單與 PUT 換明細——驗證不准在兩邊漂開。"""
        return (
            self.client.post(API, {'customer_id': self.customer.id, 'items': items},
                             content_type='application/json'),
            self.client.put(f'{API}/{self.quotation.id}/items', {'items': items},
                            content_type='application/json'),
        )

    def assert_both_reject(self, items, message):
        for r in self.both_write_paths(items):
            self.assertEqual(r.status_code, 400, r.content)
            self.assertIn(message, r.json()['detail'])

    def test_negative_unit_price_rejected_on_both_paths(self):
        """原本只有開單擋得住；換明細讓 PositiveIntegerField 的 CHECK 炸成 500。"""
        self.assert_both_reject([{'name': 'A', 'qty': 1, 'unit_price': -5}], '單價不能是負數')

    def test_qty_over_field_precision_rejected(self):
        """qty 是 numeric(8,2)，塞 8 位數會 numeric field overflow（DataError → 500）。"""
        self.assert_both_reject([{'name': 'A', 'qty': '99999999', 'unit_price': 1}], '數量太大')

    def test_unit_price_over_int32_rejected(self):
        self.assert_both_reject([{'name': 'A', 'qty': 1, 'unit_price': 2_147_483_648}], '單價太大')

    def test_stale_product_id_rejected_with_reason(self):
        """挑選框開著的時候商品被刪掉：FK 是 DEFERRABLE，不擋的話要到 commit 才炸。"""
        p = Product.objects.create(name='保養包', default_price=1000)
        stale_id = p.id
        p.delete()
        self.assert_both_reject(
            [{'name': '保養包', 'qty': 1, 'unit_price': 1000, 'product_id': stale_id}],
            '請重新挑一次')

    def test_valid_items_still_go_through_on_both_paths(self):
        """守門不能誤傷正常單——挑得到的商品照樣存得進去。"""
        p = Product.objects.create(name='保養包', default_price=1000)
        for r in self.both_write_paths(
                [{'name': p.name, 'qty': '1.5', 'unit_price': p.default_price, 'product_id': p.id}]):
            self.assertEqual(r.status_code, 200, r.content)
            self.assertEqual(Decimal(r.json()['total']), Decimal('1500'))


class NoCollisionRetryTests(TestCase):
    """撞號重試只認撞號那一顆約束。

    舊寫法 `except IntegrityError` 照單全收：明細帶了失效的 product_id 時，FK 要到
    commit 才違反、正好落在重試迴圈裡——白重試三次，最後還是以 500 出去，而且錯誤
    訊息指向「撞號」這個根本不相干的地方。
    """

    def _err(self, message, constraint_name=None):
        exc = IntegrityError(message)
        if constraint_name is not None:
            cause = Exception()
            cause.diag = SimpleNamespace(constraint_name=constraint_name)
            exc.__cause__ = cause
        return exc

    def test_serial_collision_is_retried(self):
        self.assertTrue(_is_no_collision(self._err(
            'duplicate key value violates unique constraint "quotations_quotation_no_key"')))
        self.assertTrue(_is_no_collision(self._err(
            '訊息裡看不出來', constraint_name='quotations_quotation_no_key')))

    def test_other_integrity_errors_are_not_retried(self):
        self.assertFalse(_is_no_collision(self._err(
            'violates foreign key constraint "quotations_quotation_product_id_3ac5d6a5_fk_products_"')))
        self.assertFalse(_is_no_collision(self._err(
            'violates check constraint "quotations_quotationitem_unit_price_check"')))
        self.assertFalse(_is_no_collision(self._err(
            '別的約束', constraint_name='quotations_quotationitem_item_qty_gt_0')))


class EndpointAuthTests(TestCase):
    """結構守門：每支端點預設都要登入，公開的只有這裡明列的三支。

    ns-erp 2026-08-27 的 logout 就是漏在白名單外、fall through 成匿名可打——
    「每支自己掛 auth」漏一支從 code 上看不出來。這條測試讓漏掛當場變紅。
    """

    PUBLIC = {
        ('GET', '/api/v1/health'),
        ('GET', '/api/v1/auth/csrf'),
        ('POST', '/api/v1/auth/login'),
    }

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
                            self.assertEqual(
                                r.status_code, 401,
                                f'{method} {template} 沒擋匿名——router 忘了掛 auth？')
        self.assertEqual(self.PUBLIC - seen, set(), '白名單列了已經不存在的端點')
