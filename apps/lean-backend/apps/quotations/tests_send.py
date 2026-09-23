"""送出與收回.md 驗收 5 條。"""
import datetime as dt

from django.test import TestCase

from apps._common.testing import login, make_quotation, make_user
from apps.quotations.models import Quotation

API = '/api/v1/quotations'
S = Quotation.Status


class SendAndRecallTests(TestCase):
    def setUp(self):
        self.a = make_user('amy', '艾美')
        self.b = make_user('ben', '阿班')
        self.q = make_quotation(self.a)
        self.client = login(self.a)

    def test_ac1_send_sets_status_date_and_pdf_opens(self):
        """驗收 1：草擬單按送出 → 已送出、送出日＝今天、拿到打得開的 PDF。"""
        r = self.client.post(f'{API}/{self.q.id}/send')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['status'], 'sent')
        self.assertEqual(r.json()['sent_on'], dt.date.today().isoformat())
        pdf = self.client.get(f'{API}/{self.q.id}/pdf')
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertGreater(len(pdf.content), 1000)

    def test_ac2_edit_after_send_is_recorded(self):
        """驗收 2：已送出的單改一行明細 → 紀錄多一筆（誰、何時、改了什麼）。"""
        self.client.post(f'{API}/{self.q.id}/send')
        before = self.q.logs.count()
        r = self.client.put(f'{API}/{self.q.id}/items', {'items': [
            {'name': '鋁框玻璃門', 'qty': 3, 'unit_price': 12000}]}, content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.q.logs.count(), before + 1)
        log = self.q.logs.first()
        self.assertEqual(log.actor, self.a)
        self.assertEqual(log.action, '改明細')
        self.assertIn('數量 2→3', log.detail)
        self.assertIn('總額 24,000→36,000', log.detail)
        self.assertIsNotNone(log.created_at)

    def test_ac3_someone_else_editing_is_recorded_as_them(self):
        """驗收 3：B 改 A 負責的單 → 紀錄標的是 B（原則 3）。"""
        self.client.post(f'{API}/{self.q.id}/send')
        r = login(self.b).put(f'{API}/{self.q.id}/items', {'items': [
            {'name': '鋁框玻璃門', 'qty': 1, 'unit_price': 12000}]}, content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.q.logs.first().actor, self.b)
        self.assertEqual(r.json()['logs'][0]['actor_name'], '阿班')

    def test_ac4_recall_goes_back_to_draft_and_is_recorded(self):
        """驗收 4：按收回 → 回草擬、留一筆「收回」紀錄。"""
        self.client.post(f'{API}/{self.q.id}/send')
        r = self.client.post(f'{API}/{self.q.id}/recall')
        self.assertEqual(r.json()['status'], 'draft')
        self.assertIsNone(r.json()['sent_on'])
        self.assertEqual(self.q.logs.first().action, '收回')

    def test_ac5_wrong_state_actions_hidden_and_blocked(self):
        """驗收 5：草擬單看不到收回、已送出的單看不到送出；直接打 API 也被擋。"""
        body = self.client.get(f'{API}/{self.q.id}').json()
        self.assertIn('send', body['actions'])
        self.assertNotIn('recall', body['actions'])
        self.assertEqual(self.client.post(f'{API}/{self.q.id}/recall').status_code, 400)

        self.client.post(f'{API}/{self.q.id}/send')
        body = self.client.get(f'{API}/{self.q.id}').json()
        self.assertIn('recall', body['actions'])
        self.assertNotIn('send', body['actions'])
        r = self.client.post(f'{API}/{self.q.id}/send')
        self.assertEqual(r.status_code, 400)
        self.assertIn('只有草擬', r.json()['detail'])

    def test_resend_stamps_new_date(self):
        """收回再送出，蓋新的送出日。"""
        self.client.post(f'{API}/{self.q.id}/send')
        Quotation.objects.filter(id=self.q.id).update(sent_on=dt.date(2026, 1, 1))
        self.client.post(f'{API}/{self.q.id}/recall')
        r = self.client.post(f'{API}/{self.q.id}/send')
        self.assertEqual(r.json()['sent_on'], dt.date.today().isoformat())


class EditWholeQuotationTests(TestCase):
    """詳細頁「編輯」存檔：表頭三欄＋明細一起存，送出後改的內容寫成一筆紀錄。"""

    def test_header_and_items_change_recorded_once(self):
        a = make_user('amy')
        q = make_quotation(a, status=S.SENT)
        r = login(a).put(f'{API}/{q.id}', {
            'items': [{'name': '鋁框玻璃門', 'qty': 2, 'unit_price': 11000}],
            'valid_until': '2026-12-31', 'payment_terms': '訂金三成', 'note': ''},
            content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(q.logs.count(), 1)
        detail = q.logs.first().detail
        self.assertIn('有效期限 不設限→2026-12-31', detail)
        self.assertIn('付款條件 完工後三日內付款→訂金三成', detail)
        self.assertIn('單價 12,000→11,000', detail)

    def test_owner_editing_own_draft_not_recorded(self):
        a = make_user('amy')
        q = make_quotation(a)
        login(a).put(f'{API}/{q.id}', {'items': [{'name': 'X', 'qty': 1, 'unit_price': 1}],
                                       'payment_terms': '', 'note': ''}, content_type='application/json')
        self.assertEqual(q.logs.count(), 0)
