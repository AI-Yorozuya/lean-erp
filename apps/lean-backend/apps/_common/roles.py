"""模組的門：系統總覽 modules[].roles 決定誰進得去哪個模組。

- 銷售管理（客戶、商品、報價單）：業務
- 報表分析（業績）：老闆——老闆只能看業績，不能改報價單（rule_boss_view_only）

用法：router 層掛 `auth=only(Role.BOSS)`。沒登入回 401；登入了但角色不對回 403。
"""
from ninja.errors import HttpError
from ninja.security import SessionAuth

from apps.accounts.models import User

Role = User.Role


class RoleAuth(SessionAuth):
    def __init__(self, *roles):
        super().__init__()
        self.roles = set(roles)

    def authenticate(self, request, key):
        user = super().authenticate(request, key)
        if user is None:
            return None                     # 沒登入 → 401
        if user.role not in self.roles:
            raise HttpError(403, '你的角色不能用這個功能')
        return user


def only(*roles) -> RoleAuth:
    return RoleAuth(*roles)


sales_only = only(Role.SALESPERSON)
boss_only = only(Role.BOSS)
