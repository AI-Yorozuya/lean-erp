"""報價單 PDF（sp_pdf）：PDF 上的數字照報價單，總額、免運都是當下現算。

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


def render_quotation(q) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm, title=f'報價單 {q.no}')
    story = [Paragraph(f'報價單　{q.no}', H1), Spacer(1, 6 * mm)]

    head = Table([
        ['客戶', q.customer.name, '日期', f'{q.date:%Y-%m-%d}'],
        ['聯絡人', q.customer.contact or '—', '業務', q.sales_name],
    ], colWidths=[20 * mm, 70 * mm, 20 * mm, 50 * mm])
    head.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), FONT, 10.5),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#64748b')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story += [head, Spacer(1, 6 * mm)]

    rows = [['型號', '品名', '數量', '單價', '小計']]
    for it in q.items.select_related('product'):
        rows.append([it.product.model, it.product.name, str(it.qty), _money(it.unit_price), _money(it.subtotal)])
    rows.append(['', '運費', '', '', '免運' if q.free_shipping else '運費另計'])
    rows.append(['', '總額', '', '', _money(q.total)])
    items = Table(rows, colWidths=[26 * mm, 62 * mm, 18 * mm, 26 * mm, 28 * mm], repeatRows=1)
    items.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), FONT, 10.5),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, colors.HexColor('#0f172a')),
        ('LINEBELOW', (0, 1), (-1, -3), 0.3, colors.HexColor('#cbd5e1')),
        ('LINEABOVE', (0, -2), (-1, -2), 0.8, colors.HexColor('#0f172a')),
        ('FONT', (0, -1), (-1, -1), FONT, 12),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(items)
    doc.build(story)
    return buf.getvalue()
