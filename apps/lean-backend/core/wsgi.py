"""WSGI 進入點（傳統部署備用；本專案預設走 ASGI）。"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()
