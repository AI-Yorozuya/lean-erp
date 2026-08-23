"""
lean-stack 的 Django 設定。

教學版精簡：沿用 top-erp 的慣例（django-environ 讀環境變數、apps/ 放各 app），
但砍掉所有正式環境才需要的東西（Redis / Celery / S3 / JWT...），
只留「能跑起來」的最小集合。
"""
import os
from pathlib import Path

import environ

# 專案根目錄（manage.py 所在的那一層）。BASE_DIR / 'xxx' 可組出絕對路徑。
BASE_DIR = Path(__file__).resolve().parent.parent

# 讓 import 能直接寫 `apps.health`，而不用 `backend.apps.health`。
# 沿用 top-erp：把 apps/ 也加進 sys.path。
APPS_DIR = BASE_DIR / 'apps'
os.sys.path.insert(0, str(APPS_DIR))

# ---- 環境變數 -------------------------------------------------------------
# django-environ：型別安全地讀 .env / 系統環境變數。
# DEBUG 預設 False（正式環境安全優先）。
env = environ.Env(
    DEBUG=(bool, False),
)
# 本機開發時讀 backend/.env（docker 裡用 env_file 注入，這行讀不到也沒關係）。
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: 正式環境務必用環境變數覆蓋，別用這個 fallback。
SECRET_KEY = env('DJANGO_SECRET_KEY', default='dev-only-insecure-change-me')

DEBUG = env('DEBUG')

# ---- CORS / Hosts ---------------------------------------------------------
# 開發時全開方便；正式環境才從環境變數讀白名單。
if DEBUG:
    ALLOWED_HOSTS = ['*']
    CORS_ALLOW_ALL_ORIGINS = True
else:
    ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
    CORS_ALLOW_ALL_ORIGINS = False
    # 例如 http://localhost:5174（Vite dev server）。
    CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# ---- Apps -----------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',   # 登入用 session——登入後每個動作都記得到誰在操作
    'corsheaders',
    # 自己的 app
    'apps._common',  # 共用：抽象 model（TimeStampedModel）等
    'apps.health',
    'apps.accounts',
    'apps.customers',
    'apps.products',
    'apps.quotations',
]

# 自訂 User（帳號／密碼雜湊／顯示名稱）——起手就換，事後換是 Django 最痛的手術。
AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # 要放在 CommonMiddleware 之前
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = []

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# ---- 資料庫 ---------------------------------------------------------------
# 用 DATABASE_URL 一行搞定（django-environ 的 db_url 解析）。
# 格式：postgres://USER:PASSWORD@HOST:PORT/DBNAME
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://postgres:postgres@localhost:5432/lean_stack'),
}

# ---- 非同步任務 / Celery --------------------------------------------------
# broker（派工佇列）與 result backend 都用 redis。
# 關鍵：local 與 prod 走「同一條設定路徑」—— 只差 env 裡 redis 的 host。
# 刻意「不」開 eager 模式：eager 會把任務當同步函式直接跑，藏掉「序列化、
# 連線、worker 沒起來」這類只有真 worker 才會炸的 bug —— 那正是「demo 會動、
# 上 prod 垮」的牆。所以本機也跑真 redis + 真 worker（見 docker-compose.local.yml）。
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Taipei'

# ---- 國際化 ---------------------------------------------------------------
LANGUAGE_CODE = 'zh-hant'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = True

# ---- 靜態檔 ---------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

# ---- 上傳檔 / media（env 切換：本機檔案系統 ↔ S3）-------------------------
# 教學重點：用一個 USE_S3 開關決定檔案存哪。
#   - 本機開發（USE_S3=False）→ Django 預設 FileSystemStorage，存到 /media，零設定零摩擦。
#   - 正式環境（USE_S3=True）→ django-storages 的 S3 backend，存到 S3 bucket。
# 不論哪種，model 裡寫 ImageField/FileField 的方式完全一樣（見下方註解），
# 切換只改 env，不用改 code —— 這就是 STORAGES 抽象的好處。
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

USE_S3 = env.bool('USE_S3', default=False)

if USE_S3:
    # 正式：S3。憑證優先走 EC2 instance role / 環境變數，不寫死在 code。
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='ap-northeast-1')
    AWS_DEFAULT_ACL = None          # bucket 預設私有，靠 IAM 控權
    AWS_QUERYSTRING_AUTH = True     # 私有物件用 signed URL 存取
    STORAGES = {
        'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
else:
    # 本機：檔案系統（Django 預設）。STORAGES 留預設即可，這裡顯式寫出來方便對照。
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }

# 之後加領域 model 時，FileField/ImageField「直接就能用」上面設定的 storage：
#   from apps._common.models import TimeStampedModel
#   class Receipt(TimeStampedModel):
#       image = models.ImageField(upload_to='receipts/%Y/%m/')
#   本機 → 存 /media/receipts/...；prod(USE_S3=True) → 存 S3 同路徑，code 不用改。
#   （ImageField 需要 Pillow；要用時再把 pillow 加進 pyproject。）

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
