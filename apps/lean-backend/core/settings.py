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
    'apps.reports',    # 報表分析：業績
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

# ---- 連線池（psycopg3）---------------------------------------------------
# 不開池的話 CONN_MAX_AGE=0（Django 預設）＝每個 request 開一條新連線、用完就關。
# 本機實測 GET /products（400 筆、並發 4）：162 req/s、中位 23.2 ms
#                              → 開池後：333 req/s、中位 11.1 ms。
# localhost 沒有網路來回、沒有 TLS，已經是建連線最便宜的情況；正式環境只會差更多。
#
# ⚠ 不要改用 CONN_MAX_AGE 來省這筆。我們跑的是 ASGI（entrypoint.sh：dev 是 uvicorn、
# prod 是 gunicorn + UvicornWorker，兩邊都吃 core.asgi）：
#   - DB 連線存在 thread-local（django/utils/connection.py 的 Local(thread_critical=True)）
#   - 但 ASGIHandler.__call__ 每個 request 都包一層 asgiref 的 ThreadSensitiveContext，
#     它結束時會 shutdown 自己的 executor —— 等於每個 request 跑在一條新的 thread
#   - CONN_MAX_AGE > 0 時 close_old_connections 不會關掉還沒到期的連線，thread 卻已經
#     死了 → 連線變孤兒，只能等 60 秒到期，期間一路堆積
# 本機實測（才 1 個 worker、並發 8）：連線數衝到 98，撞上 postgres max_connections，
# 240 筆請求裡 25 筆變成 500 "sorry, too many clients already"。WSGI 沒這問題，因為
# 同一條 thread 會回來重用連線 —— 所以這是 ASGI 專屬的坑，不是 CONN_MAX_AGE 本身壞掉。
#
# 池子沒這問題：DatabaseWrapper._connection_pools 是 class attribute，池活在 process 層、
# 被 max_size 封頂，跟有幾條 request thread 無關。上限＝worker 數 × max_size（prod 2×4=8）。
# 池與 CONN_MAX_AGE != 0 互斥，同時設會 ImproperlyConfigured。
#
# DB_POOL=0 是緊急關閉閥：prod 萬一池子出狀況，只改 .env 就能退回「每 request 開新連線」
# 的舊行為，不必回退程式碼。
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
if env.bool('DB_POOL', default=True):
    DATABASES['default'].setdefault('OPTIONS', {})['pool'] = {
        'min_size': env.int('DB_POOL_MIN', default=2),
        'max_size': env.int('DB_POOL_MAX', default=4),
        # 池子被借光時等多久才放棄（秒）。psycopg 預設 30 太長，request 會卡著不回。
        'timeout': 10,
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
