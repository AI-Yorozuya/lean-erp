"""登入／登出／我是誰。session 認證：登入後每個動作都記得到誰在操作（架構圖・使用者模組）。"""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

# 門預設是關的：router 層掛 auth，之後新增的端點沒寫 auth 就是「要登入」。
# 反過來寫（router 不掛、每支自己掛）漏一支就是公開端點，而且從 code 上看不出來——
# 白名單漏列正是 ns-erp 2026-08-27 那顆 logout 匿名可打的成因。公開的只有下面兩支，
# 各自用 auth=None 明講。
router = Router(tags=['auth'], auth=django_auth)


class LoginIn(Schema):
    username: str
    password: str


class MeOut(Schema):
    username: str
    display_name: str
    role: str


@router.get('/csrf', auth=None)
def csrf(request):
    """發 csrftoken cookie。前端開站先 GET 這裡一次，之後每個 POST 帶 X-CSRFToken header。

    為什麼不干脆關掉：session 登入＋免 CSRF ＝任何網頁都能替你送單，這門不能開。
    """
    return {'csrftoken': get_token(request)}


@router.post('/login', auth=None)
def login_view(request, data: LoginIn):
    user = authenticate(request, username=data.username, password=data.password)
    if user is None:
        raise HttpError(401, '帳號或密碼不對')
    login(request, user)
    return {'ok': True, 'display_name': user.shown_name}


@router.post('/logout')
def logout_view(request):
    logout(request)
    return {'ok': True}


@router.get('/me', response=MeOut)
def me(request):
    u = request.user
    return {'username': u.username, 'display_name': u.shown_name, 'role': u.role}
