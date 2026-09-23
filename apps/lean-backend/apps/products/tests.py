"""商品：系統總覽 sp_product_save 的驗收（test_product_save_*）。"""
from django.test import TestCase

from apps._common.testing import login, make_catalog, make_quotation, make_user
from apps.products.models import Product

API = '/api/v1/products'


class ProductSaveTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = login(self.user)
        self.cust, self.m27, self.m32, self.m24 = make_catalog()

    def save(self, p, **change):
        body = {'model': p.model, 'name': p.name, 'price': p.price, **change}
        return self.client.put(f'{API}/{p.id}', body, content_type='application/json')

    def test_product_save_ok(self):
        """把 27 吋螢幕單價改成 12,000 存檔，重開看到 12,000；開一張新報價單加這個商品，單價帶入 12,000。"""
        self.assertEqual(self.save(self.m27, price=12000).status_code, 200)
        self.assertEqual(self.client.get(f'{API}/{self.m27.id}').json()['price'], 12000)
        q = make_quotation(self.user, self.cust, [(self.m27, 1)])
        self.assertEqual(q.items.get().unit_price, 12000)

    def test_product_save_no(self):
        """改價後重開舊單，那一列單價仍是 10,000，總額不變。"""
        old = make_quotation(self.user, self.cust, [(self.m27, 20), (self.m32, 1)])
        self.client.post(f'/api/v1/quotations/{old.id}/pdf')
        self.save(self.m27, price=12000)
        body = self.client.get(f'/api/v1/quotations/{old.id}').json()
        self.assertEqual(body['items'][0]['unit_price'], 10000)
        self.assertEqual(body['total'], 221000)

    def test_product_save_failures_leave_data_unchanged(self):
        """型號、名稱空白或單價不大於 0 都不能儲存；型號不能跟別的商品重複。"""
        for change, msg in [({'model': ' '}, '型號不能空白'), ({'name': ''}, '名稱不能空白'),
                            ({'price': 0}, '單價要大於 0'), ({'model': 'M32U-C1'}, '已經有別的商品在用')]:
            r = self.save(self.m27, **change)
            self.assertEqual(r.status_code, 400, change)
            self.assertIn(msg, r.json()['detail'])
        self.m27.refresh_from_db()
        self.assertEqual((self.m27.model, self.m27.name, self.m27.price), ('M27F-B2', '27" FHD 商用螢幕', 10000))
