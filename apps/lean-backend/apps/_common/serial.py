"""單號：字母－日期－三碼流水（Q-20260901-003），同日連號不重複。

靠 DB unique 約束＋撞號重試——兩個人同秒開單，慢的那個撞
IntegrityError 再取號一次。只有「撞單號」值得重試，別的 IntegrityError 立刻往上丟。
"""
import datetime as dt

from django.db import IntegrityError, transaction

MAX_RETRY = 3


def next_no(model, letter: str, today: dt.date | None = None) -> str:
    prefix = f'{letter}-{(today or dt.date.today()):%Y%m%d}-'
    last = (model.objects.filter(no__startswith=prefix)
            .order_by('-no').values_list('no', flat=True).first())
    seq = int(last.rsplit('-', 1)[1]) + 1 if last else 1
    return f'{prefix}{seq:03d}'


def is_no_collision(exc: IntegrityError, model) -> bool:
    """這顆 IntegrityError 是不是撞單號？（postgres 對 unique=True 的自動命名：<table>_no_key）"""
    constraint = f'{model._meta.db_table}_no_key'
    diag = getattr(getattr(exc, '__cause__', None), 'diag', None)
    return constraint in (getattr(diag, 'constraint_name', None) or str(exc))


def create_with_no(model, letter: str, build):
    """取號並在同一個 transaction 裡建單。build(no) 負責建主檔與明細，回傳主檔。"""
    for attempt in range(MAX_RETRY):
        try:
            with transaction.atomic():
                return build(next_no(model, letter))
        except IntegrityError as e:
            if not is_no_collision(e, model) or attempt == MAX_RETRY - 1:
                raise
    raise AssertionError('unreachable')
