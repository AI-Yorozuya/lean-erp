"""轉成訂單.md 驗收 4 條＋架構圖原則 5（已成交才轉訂單）。"""
from django.test import TestCase

from apps._common.testing import login, make_quotation, make_user
from apps.orders.models import Order
from apps.quotations.models import Quotation

API = '/api/v1/orders'
QAPI = '/api/v1/quotations'
S = Quotation.Status


class ConvertTests(TestCase):
    def setUp(self):
        self.u = make_user()
        self.client = login(self.u)
        self.q = make_quotation(self.u, items=[
            {'name': '鋁框玻璃門', 'qty': 2, 'unit_price': 12000},
            {'name': '到府安裝工資（半天）', 'qty': 1, 'unit_price': 3500}], status=S.WON)

    def convert(self, q=None):
        return self.client.post(API, {'quotation_id': (q or self.q).id}, content_type='application/json')

    def test_ac1_won_converts_to_pending_order_with_same_items(self):
        """驗收 1：已成交按轉單 → O 開頭訂單、待處理、明細與報價單當下一致。"""
        r = self.convert()
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertRegex(body['no'], r'^O\d{8}-\d{3}$')
        self.assertEqual(body['status'], 'pending')
        self.assertEqual([(i['name'], i['unit_price']) for i in body['items']],
                         [(i.name, i.unit_price) for i in self.q.items.all()])
        self.assertEqual(body['total'], str(self.q.total))

    def test_ac2_non_won_blocked_with_reason(self):
        """驗收 2：草擬／已送出／沒成打轉單 → 被擋，看得懂為什麼。"""
        for st in (S.DRAFT, S.SENT, S.LOST):
            q = make_quotation(self.u, status=st)
            r = self.convert(q)
            self.assertEqual(r.status_code, 400, st)
            self.assertIn('只有已成交', r.json()['detail'])
        self.assertEqual(Order.objects.count(), 0)

    def test_ac3_void_then_convert_again(self):
        """驗收 3：作廢待處理訂單 → 留作廢紀錄、報價單回已成交、可再轉一張新訂單。"""
        o = self.convert().json()
        r = self.client.post(f'{API}/{o["id"]}/void')
        self.assertEqual(r.json()['status'], 'void')
        self.assertEqual(r.json()['logs'][0]['action'], '作廢')
        self.assertTrue(Order.objects.filter(id=o['id']).exists())   # 不真刪
        self.assertEqual(Quotation.objects.get(id=self.q.id).status, S.WON)
        again = self.convert()
        self.assertEqual(again.status_code, 200, again.content)
        self.assertNotEqual(again.json()['no'], o['no'])

    def test_ac4_editing_quotation_after_convert_leaves_order_alone(self):
        """驗收 4：轉單後改報價明細 → 訂單明細不動。"""
        o = self.convert().json()
        self.client.put(f'{QAPI}/{self.q.id}/items', {'items': [
            {'name': '鋁框玻璃門', 'qty': 9, 'unit_price': 99999}]}, content_type='application/json')
        body = self.client.get(f'{API}/{o["id"]}').json()
        self.assertEqual(len(body['items']), 2)
        self.assertEqual(body['items'][0]['unit_price'], 12000)

    def test_principle_5_only_won_quotations_convert(self):
        """原則 5：已成交才轉訂單；一張報價同時只有一張有效訂單。"""
        self.assertEqual(self.convert().status_code, 200)
        r = self.convert()
        self.assertEqual(r.status_code, 400)
        self.assertIn('已經轉成訂單', r.json()['detail'])
        self.assertEqual(Order.objects.exclude(status='void').count(), 1)

    def test_converted_quotation_cannot_be_reopened_until_order_voided(self):
        """報價單已轉訂單時，點錯改回會讓兩邊對不起來：先作廢訂單才放行。"""
        o = self.convert().json()
        body = self.client.get(f'{QAPI}/{self.q.id}').json()
        self.assertNotIn('reopen', body['actions'])
        self.assertNotIn('convert', body['actions'])
        r = self.client.post(f'{QAPI}/{self.q.id}/reopen')
        self.assertEqual(r.status_code, 400)
        self.assertIn(o['no'], r.json()['detail'])
        self.client.post(f'{API}/{o["id"]}/void')
        self.assertEqual(self.client.post(f'{QAPI}/{self.q.id}/reopen').status_code, 200)
