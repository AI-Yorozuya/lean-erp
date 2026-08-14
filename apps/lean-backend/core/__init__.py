# Django 啟動時就載入 Celery app，讓 @shared_task 能找到它。
from core.celery import app as celery_app

__all__ = ('celery_app',)
