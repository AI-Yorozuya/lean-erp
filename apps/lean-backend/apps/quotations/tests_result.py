"""點結果.md 驗收 3 條。"""
from django.test import TestCase

from apps._common.testing import login, make_quotation, make_user
from apps.quotations.models import Quotation

API = '/api/v1/quotations'
S = Quotation.Status


class MarkResultTests(TestCase):
    def setUp(self):
        self.u = make_user()
        self.client = login(self.u)

    def test_ac1_win_and_lose_each_recorded(self):
        """驗收 1：已送出點成交 → 已成交＋一筆紀錄；點沒成 → 沒成＋一筆紀錄。"""
        q1 = make_quotation(self.u, status=S.SENT)
        r = self.client.post(f'{API}/{q1.id}/win')
        self.assertEqual(r.json()['status'], 'won')
        self.assertEqual(q1.logs.first().action, '點成交')
        q2 = make_quotation(self.u, status=S.SENT)
        r = self.client.post(f'{API}/{q2.id}/lose')
        self.assertEqual(r.json()['status'], 'lost')
        self.assertEqual(q2.logs.first().action, '點沒成')

    def test_ac2_reopen_goes_back_to_sent_and_is_recorded(self):
        """驗收 2：點錯改回 → 回已送出＋一筆改回紀錄。"""
        q = make_quotation(self.u, status=S.SENT)
        self.client.post(f'{API}/{q.id}/lose')
        r = self.client.post(f'{API}/{q.id}/reopen')
        self.assertEqual(r.json()['status'], 'sent')
        self.assertEqual(q.logs.first().action, '點錯改回')
        self.assertEqual(q.logs.count(), 2)

    def test_ac3_draft_has_no_result_buttons_and_api_blocks(self):
        """驗收 3：草擬單沒有點結果的按鈕；直接打 API → 被擋。"""
        q = make_quotation(self.u)
        actions = self.client.get(f'{API}/{q.id}').json()['actions']
        self.assertFalse({'win', 'lose', 'reopen'} & set(actions))
        for act in ('win', 'lose', 'reopen'):
            r = self.client.post(f'{API}/{q.id}/{act}')
            self.assertEqual(r.status_code, 400, act)
        self.assertEqual(Quotation.objects.get(id=q.id).status, S.DRAFT)
        self.assertEqual(q.logs.count(), 0)
