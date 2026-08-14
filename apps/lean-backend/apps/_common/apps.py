from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps._common'
    label = 'common'  # 預設 label 會是 _common，避開底線開頭
