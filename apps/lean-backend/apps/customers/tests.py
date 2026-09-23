"""客戶：列表帶報價紀錄幾筆、最近一張；儲存名稱不能空白。"""
from django.test import TestCase

from apps._common.testing import login, make_catalog, make_quotation, make_user

API = '/api/v1/customers'


class CustomerTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = login(self.user)
        self.cust, self.m27, _, _ = make_catalog()

    def test_list_shows_quote_count_and_last_quote(self):
        make_quotation(self.user, self.cust, [(self.m27, 1)])
        last = make_quotation(self.user, self.cust, [(self.m27, 2)])
        row = self.client.get(API).json()['items'][0]
        self.assertEqual((row['quote_count'], row['last_quote_no']), (2, last.no))

    def test_save_requires_name(self):
        r = self.client.put(f'{API}/{self.cust.id}', {'name': ' ', 'contact': 'x'}, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        r = self.client.put(f'{API}/{self.cust.id}', {'name': '弘遠科技股份有限公司', 'contact': '陳志明'},
                            content_type='application/json')
        self.assertEqual(r.json()['name'], '弘遠科技股份有限公司')
