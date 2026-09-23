"""報價單 PDF（送出與收回.md 的樣張）。總額印當下現算的數字，不另外存一份。

中文字型要「內嵌」進 PDF：只寫字型名、讓檢視器自己找字，Preview 會對錯字變亂碼。
字型檔不進 repo——Docker 映像裝 fonts-wqy-zenhei；不在 Docker 裡跑時找本機現成的，
也可以用環境變數 PDF_FONT_PATH 指定一個 TrueType 字型（.ttf／.ttc）。
"""
import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT = 'QuoteFont'
FONT_CANDIDATES = [
    os.environ.get('PDF_FONT_PATH', ''),
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',   # Docker 映像
    '/Library/Fonts/Arial Unicode.ttf',               # macOS
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
]


def _register_font():
    for path in FONT_CANDIDATES:
        if path and os.path.exists(path):
            kw = {'subfontIndex': 0} if path.endswith('.ttc') else {}
            pdfmetrics.registerFont(TTFont(FONT, path, **kw))   # 只內嵌用到的字，檔案不會肥
            return path
    raise RuntimeError('找不到中文字型：Docker 映像要裝 fonts-wqy-zenhei，或設 PDF_FONT_PATH')


FONT_PATH = _register_font()

H1 = ParagraphStyle('h1', fontName=FONT, fontSize=18, leading=24)
BODY = ParagraphStyle('body', fontName=FONT, fontSize=10.5, leading=15)


def _money(v) -> str:
    return f'{int(v):,}'


def _qty(v) -> str:
    return f'{int(v)}' if v == int(v) else f'{v.normalize():f}'


def render_quotation(q) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm,
                            title=f'報價單 {q.no}', author='lean-erp')
    sent = f'{q.sent_on:%Y-%m-%d}' if q.sent_on else '（草擬，尚未送出）'
    story = [
        Paragraph(f'報價單　{q.no}', H1),
        Paragraph(f'送出日　{sent}', BODY),
        Spacer(1, 6 * mm),
    ]

    head = Table([
        ['客戶', q.customer.name],
        ['電話', q.customer.phone],
        ['有效期限', f'{q.valid_until:%Y-%m-%d}' if q.valid_until else '—'],
        ['付款條件', q.payment_terms or '—'],
    ], colWidths=[28 * mm, 130 * mm])
    head.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), FONT, 10.5),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story += [head, Spacer(1, 6 * mm)]

    rows = [['品名', '數量', '單價', '小計']]
    for it in q.items.all():
        rows.append([it.name, _qty(it.qty), _money(it.unit_price), _money(it.subtotal)])
    rows.append(['總額', '', '', _money(q.total)])
    items = Table(rows, colWidths=[82 * mm, 22 * mm, 26 * mm, 30 * mm], repeatRows=1)
    items.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), FONT, 10.5),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, colors.HexColor('#0f172a')),
        ('LINEBELOW', (0, 1), (-1, -2), 0.3, colors.HexColor('#cbd5e1')),
        ('LINEABOVE', (0, -1), (-1, -1), 0.8, colors.HexColor('#0f172a')),
        ('FONT', (0, -1), (-1, -1), FONT, 12),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(items)
    if q.note:
        story += [Spacer(1, 6 * mm), Paragraph(f'備註　{q.note}', BODY)]

    doc.build(story)
    return buf.getvalue()
