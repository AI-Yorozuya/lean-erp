"""塞一組假資料讓系統一開就能玩（紅線：零真實資料——全是編的）。"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.customers.models import Customer
from apps.products.models import Product


class Command(BaseCommand):
    help = '假資料：dev 帳號＋示範商品＋示範客戶（可重跑，不重複建）'

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username='dev').exists():
            User.objects.create_user(username='dev', password='dev1234', display_name='示範帳號')
            self.stdout.write('建了帳號 dev / dev1234')
        for name, price in [('到府安裝工資（半天）', 3500), ('鋁框玻璃門', 12000),
                            ('五金零件包', 800), ('丈量出圖', 1500), ('舊品拆除清運', 2000)]:
            Product.objects.get_or_create(name=name, defaults={'default_price': price})
        for name, phone in [('王小明', '0912345678'), ('陳大同水電行', '0987654321'),
                            ('林太太', '0933222111')]:
            Customer.objects.get_or_create(name=name, phone=phone)
        self.stdout.write(self.style.SUCCESS('seed 完成'))
