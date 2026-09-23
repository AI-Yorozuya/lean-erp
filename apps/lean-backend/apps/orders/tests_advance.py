"""訂單推進.md 驗收 3 條。"""
from django.test import TestCase

from apps._common.testing import login, make_quotation, make_user
from apps.orders.services import convert
from apps.quotations.models import Quotation

API = '/api/v1/orders'


class AdvanceTests(TestCase):
    def setUp(self):
        self.u = make_user()
        self.client = login(self.u)
        self.o = convert(make_quotation(self.u, status=Quotation.Status.WON), self.u)

    def post(self, action):
        return self.client.post(f'{API}/{self.o.id}/{action}')

    def actions_logged(self):
        return list(self.o.logs.order_by('id').values_list('action', flat=True))

    def test_ac1_advance_step_by_step_each_recorded(self):
        """驗收 1：待處理→處理中→完成，逐步推進各留一筆紀錄。"""
        self.assertEqual(self.post('start').json()['status'], 'processing')
        self.assertEqual(self.post('finish').json()['status'], 'done')
        self.assertEqual(self.actions_logged(), ['轉成訂單', '開始處理', '完成'])

    def test_ac2_step_back_recorded(self):
        """驗收 2：完成點錯改回 → 處理中＋紀錄；處理中退回 → 待處理＋紀錄。"""
        self.post('start')
        self.post('finish')
        self.assertEqual(self.post('reopen').json()['status'], 'processing')
        self.assertEqual(self.post('back').json()['status'], 'pending')
        self.assertEqual(self.actions_logged()[-2:], ['點錯改回', '退回'])

    def test_ac3_void_while_processing_points_the_way(self):
        """驗收 3：處理中打作廢 → 被擋，訊息指路「先退回待處理」。"""
        self.post('start')
        self.assertNotIn('void', self.client.get(f'{API}/{self.o.id}').json()['actions'])
        r = self.post('void')
        self.assertEqual(r.status_code, 400)
        self.assertIn('先退回待處理', r.json()['detail'])
