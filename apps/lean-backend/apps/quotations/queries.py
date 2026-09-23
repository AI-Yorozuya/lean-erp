"""報價單列表（報價單列表.md）：狀態 tabs、盯單排序、查舊價。"""
from django.db.models import Count, F, Q

from .models import Quotation

S = Quotation.Status


def list_quotations(*, status: str = '', search: str = ''):
    qs = Quotation.objects.select_related('customer', 'owner').prefetch_related('items')
    if status:
        qs = qs.filter(status=status)
    if search:
        # 查舊價：客戶名或品名（比對明細快照的品名，不是商品主檔）
        qs = qs.filter(Q(customer__name__icontains=search) | Q(items__name__icontains=search)).distinct()

    if status == S.SENT and not search:
        # 盯單：掛越久排越上。過期不影響排序，只顯示。
        return qs.order_by('sent_on', 'id')
    # 其他 tab 與搜尋結果：送出日新到舊；沒送出過的（草擬）排最後，照建立時間新到舊
    return qs.order_by(F('sent_on').desc(nulls_last=True), '-created_at', '-id')


def status_counts() -> dict:
    counts = {s.value: 0 for s in S}
    for row in Quotation.objects.values('status').annotate(n=Count('id')):
        counts[row['status']] = row['n']
    counts['all'] = sum(counts.values())
    return counts
