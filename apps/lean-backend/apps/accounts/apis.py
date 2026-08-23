"""登入／登出／我是誰。session 認證：登入後每個動作都記得到誰在操作（架構圖・使用者模組）。"""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

router = Router(tags=['auth'])


class LoginIn(Schema):
    username: str
    password: str


class MeOut(Schema):
    username: str
    display_name: str


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


@router.post('/logout', auth=django_auth)
def logout_view(request):
    logout(request)
    return {'ok': True}


@router.get('/me', auth=django_auth, response=MeOut)
def me(request):
    return {'username': request.user.username, 'display_name': request.user.shown_name}
