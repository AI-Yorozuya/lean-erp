"""業績（系統總覽・資料 stats，規格 sp_stats）：每月業績從當月已送出的報價單算出來。

報價張數＝送出日期落在這個月的報價單張數；報價總額＝這些報價單的總額加總（總額＝品項加總，rule_total_sum）。
草稿沒有送出日期，不算。業績不存表：每次查詢現算，報價單改了業績就跟著對。
"""
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncMonth

from apps.quotations.models import Quotation, QuotationItem


def monthly_stats() -> list[dict]:
    sent = Quotation.objects.filter(status=Quotation.Status.SENT, sent_at__isnull=False)
    counts = {r['month']: r['n'] for r in
              sent.annotate(month=TruncMonth('sent_at')).values('month').annotate(n=Count('id'))}
    totals = {r['month']: r['total'] for r in
              QuotationItem.objects.filter(quotation__in=sent)
              .annotate(month=TruncMonth('quotation__sent_at')).values('month')
              .annotate(total=Sum(F('qty') * F('unit_price')))}
    return [{'month': m, 'quote_count': counts[m], 'quote_total': totals.get(m) or 0}
            for m in sorted(counts, reverse=True)]
