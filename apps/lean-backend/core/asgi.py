"""ASGI 進入點（gunicorn + uvicorn worker 用這個）。"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_asgi_application()
