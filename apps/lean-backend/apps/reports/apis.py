"""報表分析的 API（系統總覽・頁面 stats_report）。老闆才進得來；老闆也只有這裡能進（rule_boss_view_only）。"""
import datetime as dt

from ninja import Router, Schema

from apps._common.roles import boss_only

from .queries import monthly_stats

router = Router(tags=['reports'], auth=boss_only)  # 報表分析：老闆


class StatsRow(Schema):
    month: dt.date          # 該月 1 號
    quote_count: int
    quote_total: int


@router.get('/stats', response=list[StatsRow])
def stats(request):
    """sp_stats 業績頁「查詢」：一個月一列，新的月份在上面；沒有送出報價單的月份不列。"""
    return monthly_stats()
