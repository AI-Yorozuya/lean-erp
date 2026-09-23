"""修改紀錄：誰、何時、哪張單、改了什麼（架構圖・資料／操作紀錄模組）。

原則 2、3、4 都靠這一張表兌現：送出後改單、動別人的單、狀態退回，全部寫一筆。
報價單、訂單共用同一套，不各做一份（送出與收回.md）。
紀錄只增不改：沒有更新與刪除的 API，外鍵用 PROTECT——單據有紀錄就刪不掉。
"""
from django.conf import settings
from django.db import models

from apps._common.models import TimeStampedModel


class ChangeLog(TimeStampedModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name='changes', verbose_name='誰')
    quotation = models.ForeignKey('quotations.Quotation', on_delete=models.PROTECT, null=True, blank=True,
                                  related_name='logs', verbose_name='報價單')
    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, null=True, blank=True,
                              related_name='logs', verbose_name='訂單')
    action = models.CharField('動作', max_length=20)      # 送出、收回、改明細、點成交、推進…
    detail = models.TextField('改了什麼', blank=True, default='')

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            # 一筆紀錄只掛一張單：報價單或訂單，二選一
            models.CheckConstraint(
                condition=(models.Q(quotation__isnull=False, order__isnull=True)
                           | models.Q(quotation__isnull=True, order__isnull=False)),
                name='changelog_one_target'),
        ]

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.actor} {self.action}'


def record(actor, *, action, detail='', quotation=None, order=None) -> ChangeLog:
    """寫一筆紀錄。所有動作都走這一個入口，欄位才不會各寫各的。"""
    return ChangeLog.objects.create(actor=actor, action=action, detail=detail,
                                    quotation=quotation, order=order)
