"""報價單列表.md 驗收 4 條。"""
import datetime as dt

from django.test import TestCase

from apps._common.testing import login, make_quotation, make_user
from apps.customers.models import Customer
from apps.quotations.models import Quotation

API = '/api/v1/quotations'
S = Quotation.Status
today = dt.date.today()


def ago(days):
    return today - dt.timedelta(days=days)


class QuotationListTests(TestCase):
    def setUp(self):
        self.u = make_user()
        self.client = login(self.u)
        self.wang = Customer.objects.create(name='王小明', phone='0912345678')
        self.chen = Customer.objects.create(name='陳大同水電行', phone='0987654321')

    def nos(self, **params):
        r = self.client.get(API, params)
        self.assertEqual(r.status_code, 200, r.content)
        return [row['no'] for row in r.json()['rows']]

    def test_ac1_sent_tab_oldest_first(self):
        """驗收 1：已送出（10 天前／3 天前／今天）→ 10 天前最上。"""
        q3 = make_quotation(self.u, customer=self.wang, status=S.SENT, sent_on=ago(3))
        q0 = make_quotation(self.u, customer=self.wang, status=S.SENT, sent_on=today)
        q10 = make_quotation(self.u, customer=self.wang, status=S.SENT, sent_on=ago(10))
        self.assertEqual(self.nos(status='sent'), [q10.no, q3.no, q0.no])

    def test_ac2_search_by_customer_or_item_name(self):
        """驗收 2：搜「王小明」只出他的單；搜品名 → 含該品名明細的單全出。"""
        w = make_quotation(self.u, customer=self.wang)
        c1 = make_quotation(self.u, customer=self.chen,
                            items=[{'name': '五金零件包', 'qty': 1, 'unit_price': 800}])
        c2 = make_quotation(self.u, customer=self.chen,
                            items=[{'name': '丈量出圖', 'qty': 1, 'unit_price': 1500},
                                   {'name': '五金零件包', 'qty': 2, 'unit_price': 800}])
        self.assertEqual(self.nos(search='王小明'), [w.no])
        self.assertCountEqual(self.nos(search='五金零件包'), [c1.no, c2.no])

    def test_ac3_expired_keeps_position_and_shows_expired(self):
        """驗收 3：過期的單照掛的天數排，且看得到已過期。"""
        old = make_quotation(self.u, customer=self.wang, status=S.SENT, sent_on=ago(22))
        Quotation.objects.filter(id=old.id).update(valid_until=ago(1))
        new = make_quotation(self.u, customer=self.wang, status=S.SENT, sent_on=ago(2))
        Quotation.objects.filter(id=new.id).update(valid_until=today + dt.timedelta(days=30))
        rows = self.client.get(API, {'status': 'sent'}).json()['rows']
        self.assertEqual([r['no'] for r in rows], [old.no, new.no])
        self.assertTrue(rows[0]['is_expired'])
        self.assertFalse(rows[1]['is_expired'])

    def test_ac4_status_words_match_architecture(self):
        """驗收 4：tabs 上的狀態字＝草擬／已送出／已成交／沒成，無別名。"""
        self.assertEqual([label for _, label in S.choices], ['草擬', '已送出', '已成交', '沒成'])
        make_quotation(self.u, customer=self.wang, status=S.WON)
        body = self.client.get(API).json()
        self.assertEqual(body['rows'][0]['status_display'], '已成交')
        self.assertEqual(set(body['counts']), {'draft', 'sent', 'won', 'lost', 'all'})

    def test_unknown_status_rejected(self):
        self.assertEqual(self.client.get(API, {'status': 'nope'}).status_code, 400)
