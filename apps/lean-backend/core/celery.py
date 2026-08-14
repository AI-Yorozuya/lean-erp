"""Celery app（非同步任務的入口）。

教學重點：
- 一個 Celery 實例叫 'core'，設定從 Django settings 讀（namespace='CELERY' →
  只認 settings 裡 CELERY_ 開頭的設定，例如 CELERY_BROKER_URL）。
- autodiscover_tasks()：自動掃描每個 app 的 tasks.py，不用手動 import。
  → 加新任務只要在某個 app 寫 tasks.py，worker 就找得到。
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# 從 Django settings 讀設定；只抓 CELERY_ 前綴的 key。
app.config_from_object('django.conf:settings', namespace='CELERY')

# 掃描所有 INSTALLED_APPS 底下的 tasks.py。
app.autodiscover_tasks()
