"""使用者：帳號、密碼（Django 雜湊存放，不存明文）、顯示名稱、角色。

角色＝系統總覽的 roles：業務用銷售管理、老闆用報表分析（模組的 roles 決定誰進得去，見 apps/_common/roles.py）。

教學重點：專案起手就自訂 User——AUTH_USER_MODEL 事後要換是 Django 最痛的手術。
帳號先由開發者手建（`manage.py createsuperuser` 或 seed_demo），沒有註冊頁。
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SALESPERSON = 'salesperson', '業務'
        BOSS = 'boss', '老闆'

    display_name = models.CharField('顯示名稱', max_length=50, blank=True, default='')
    role = models.CharField('角色', max_length=20, choices=Role.choices, default=Role.SALESPERSON)

    @property
    def shown_name(self) -> str:
        return self.display_name or self.username
