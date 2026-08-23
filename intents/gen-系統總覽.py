#!/usr/bin/env python3
"""總覽頁產生器——整條意圖驅動設計的知識層投影，一份 HTML。

正本＝intents/ 的 md 們；本頁是派生。從意圖站就能建：檔案還沒出生的站顯示 ⏳，
頁面跟著站位長大（狀態住檔案——判站邏輯同 /next：看檔案在不在、檔頭簽了沒）。
mermaid 圖：fence 內容 hash 進 assets/ 快取，變了才重渲（mmdc parse 失敗＝出手前品質閘擋下）。
跑法：python3 gen-總覽.py
"""
import hashlib
import html
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
ASSETS = HERE / 'assets'

MODULES = [  # 規格書照模組分群（模組管邊界、動作管施工；群內照主流程順序）
    ('報價單模組', [
        ('建立報價單', '✅ 施工中'),
        ('送出與收回', '✅ 已定稿'),
        ('報價單列表', '✅ 已定稿'),
        ('點結果',   '✅ 已定稿'),
    ]),
    ('訂單模組', [
        ('轉成訂單', '✅ 已定稿'),
        ('訂單推進', '✅ 已定稿'),
    ]),
]
BOOKS = [b for _, bs in MODULES for b in bs]  # 攤平（狀態計算與互鏈用）
BUILD_STATUS = {'施工站': '◐ 建立報價單後端完成、缺畫面', '驗收': '✗ 未跑'}

THEME = {"theme": "base", "themeVariables": {
    "primaryColor": "#EEEDFE", "primaryBorderColor": "#7F77DD",
    "primaryTextColor": "#26215C", "lineColor": "#5F5E5A",
    "textColor": "#26215C", "edgeLabelBackground": "#F4F4F2"}}


def render_mermaid(src: str) -> str:
    """fence → 內嵌 SVG（hash 快取；沒 mmdc 又沒快取＝硬錯，不吐爛頁）。"""
    ASSETS.mkdir(exist_ok=True)
    key = hashlib.sha256(src.encode()).hexdigest()[:10]
    svg = ASSETS / f'mmd-{key}.svg'
    if not svg.exists():
        mmd = ASSETS / f'mmd-{key}.mmd'
        cfg = ASSETS / '_theme.json'
        mmd.write_text(src, encoding='utf-8')
        cfg.write_text(json.dumps(THEME), encoding='utf-8')
        r = subprocess.run(['npx', '--yes', '@mermaid-js/mermaid-cli',
                            '-i', str(mmd), '-o', str(svg), '-c', str(cfg), '-b', 'transparent'],
                           capture_output=True, text=True)
        if r.returncode != 0 or not svg.exists():
            sys.exit(f'mermaid parse/render 失敗（品質閘）：{r.stderr[-400:]}')
    s = svg.read_text(encoding='utf-8')
    s = re.sub(r'<svg ', '<svg width="100%" ', s, count=1) if 'width="100%"' not in s[:400] else s
    return f'<div class="diagram">{s}</div>'


def inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'〔([^〕]*)〕', r'<span class="note">〔\1〕</span>', s)  # 樣張規則註解
    def link(m):
        text, href = m.group(1), m.group(2)
        name = href.removesuffix('.md')
        if href.startswith('架構圖'):
            return f'<a href="#" onclick="show(\'架構圖\');return false">{text}</a>'
        if href.startswith('意圖定稿'):
            return f'<a href="#" onclick="show(\'意圖定稿\');return false">{text}</a>'
        if any(name == b for b, _ in BOOKS):
            return f'<a href="#" onclick="showBook(\'{name}\');return false">{text}</a>'
        return f'<a href="{href}">{text}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, s)


def md_to_html(text: str) -> str:
    out, i, lines = [], 0, text.splitlines()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('```'):
            lang = ln[3:].strip()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                buf.append(lines[i]); i += 1
            i += 1
            body = '\n'.join(buf)
            out.append(render_mermaid(body) if lang == 'mermaid'
                       else f'<pre><code>{html.escape(body)}</code></pre>')
            continue
        if ln.startswith('# '):
            i += 1; continue
        if ln.startswith('### '):
            out.append(f'<h4>{inline(ln[4:])}</h4>')
        elif ln.startswith('## '):
            if getattr(md_to_html, '_spec_open', False):
                out.append('</div>')
                md_to_html._spec_open = False
            out.append(f'<h3>{inline(ln[3:])}</h3>')
            if ln[3:].startswith('樣張'):
                out.append('<div class="specimen">')
                md_to_html._spec_open = True
        elif ln.startswith('> '):
            buf = []
            while i < len(lines) and lines[i].startswith('>'):
                buf.append(inline(lines[i].lstrip('> '))); i += 1
            out.append('<blockquote>' + '<br>'.join(buf) + '</blockquote>'); continue
        elif ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                if not re.match(r'^\|[\s\-|]+\|$', lines[i]):
                    rows.append([inline(c.strip()) for c in lines[i].strip('|').split('|')])
                i += 1
            head = ''.join(f'<th>{c}</th>' for c in rows[0])
            body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows[1:])
            out.append(f'<div class="overflow"><table><thead><tr>{head}</tr></thead>'
                       f'<tbody>{body}</tbody></table></div>')
            continue
        elif re.match(r'^(\d+\.|-) ', ln):
            tag = 'ol' if ln[0].isdigit() else 'ul'
            items = []
            while i < len(lines) and re.match(r'^(\d+\.|-) ', lines[i]):
                items.append('<li>' + inline(re.sub(r'^(\d+\.|-) ', '', lines[i])) + '</li>'); i += 1
            out.append(f'<{tag}>' + ''.join(items) + f'</{tag}>'); continue
        elif ln.strip():
            out.append(f'<p>{inline(ln)}</p>')
        i += 1
    if getattr(md_to_html, '_spec_open', False):
        out.append('</div>')
        md_to_html._spec_open = False
    return '\n'.join(out)


def load(name):
    p = HERE / f'{name}.md'
    return p.read_text(encoding='utf-8') if p.exists() else None


def station_status():
    intent = load('意圖定稿'); arch = load('架構圖')
    s1 = ('✅' if intent and '✅ 已確認' in intent else ('◐' if intent else '⏳'))
    s2 = ('✅' if arch and '✅ 已簽核' in arch else ('◐ 草稿' if arch else '⏳'))
    done = sum(1 for _, st in BOOKS if (HERE / f'{_}.md').exists())
    s3 = f'◐ {done}/{len(BOOKS)} 本' if done else '⏳'
    if done == len(BOOKS):
        s3 = f'✅ {len(BOOKS)} 本定稿' if all('待 review' not in st for _, st in BOOKS) else f'◐ 待 review'
    return [('意圖', s1), ('架構', s2), ('規格', s3),
            ('施工', BUILD_STATUS['施工站']), ('驗收', BUILD_STATUS['驗收'])]


def decision_points():
    pts = []
    for name, _ in BOOKS:
        t = load(name)
        if not t:
            continue
        m = re.search(r'## 判斷點.*?(?=\n## )', t, re.S)
        if m:
            pts += [(name, inline(re.sub(r'^- ', '', ln.strip())))
                    for ln in m.group(0).splitlines() if '🔴' in ln]
    return pts


PLACEHOLDER = '<p class="empty">⏳ 這一站還沒走到——檔案出生後重跑 gen 就會長出來。</p>'

intent_html = md_to_html(load('意圖定稿')) if load('意圖定稿') else PLACEHOLDER
arch_html = md_to_html(load('架構圖')) if load('架構圖') else PLACEHOLDER

book_groups, book_panes = [], []
first = True
for mod_name, mod_books in MODULES:
    btns = []
    for name, st in mod_books:
        t = load(name)
        body = md_to_html(t) if t else PLACEHOLDER
        cls = ' active' if first else ''
        btns.append(f'<button class="tab sub{cls}" id="bbtn-{name}" '
                    f'onclick="showBook(\'{name}\')">{name}<span class="st">{html.escape(st)}</span></button>')
        book_panes.append(f'<section class="bpane{cls}" id="bpane-{name}">{body}</section>')
        first = False
    book_groups.append(f'<div class="modgroup"><span class="modlabel">{mod_name}</span>'
                       f'<div class="modtabs">{"".join(btns)}</div></div>')

pts = decision_points()
pts_html = ('<div class="decisions"><h2>🔴 待拍的判斷點（其餘內容都是已簽核架構圖的投影）</h2><ul>'
            + ''.join(f'<li><b>{n}</b>：{t}</li>' for n, t in pts) + '</ul></div>') if pts else ''

strip = ''.join(f'<span class="station"><b>{n}</b> {html.escape(s)}</span>' for n, s in station_status())

page = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>報價單系統 — 總覽</title>
<style>
  :root {{ --ink:#2C2C2A; --line:#D8D6CF; --paper:#FAFAF7; --accent:#7F77DD; --soft:#EEEDFE; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:'PingFang TC','Noto Sans TC',sans-serif; color:var(--ink);
         background:var(--paper); line-height:1.75; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:32px 24px 80px; }}
  h1 {{ font-size:22px; margin:0 0 4px; }}
  .meta {{ color:#6b6a64; font-size:13px; margin-bottom:10px; }}
  .strip {{ display:flex; flex-wrap:wrap; gap:8px; margin:0 0 20px; font-size:13px; }}
  .station {{ background:#fff; border:1px solid var(--line); border-radius:20px; padding:3px 12px; }}
  .decisions {{ background:#FFF8E6; border:1px solid #E7C96A; border-radius:10px;
                padding:12px 18px; margin:0 0 18px; }}
  .decisions h2 {{ font-size:14px; margin:0 0 6px; }}
  .decisions li {{ margin:4px 0; font-size:14px; }}
  .tabs {{ display:flex; flex-wrap:wrap; gap:6px; border-bottom:2px solid var(--line); }}
  .tab {{ border:1px solid var(--line); border-bottom:none; background:#f1efe8;
          border-radius:8px 8px 0 0; padding:8px 16px; font-size:15px; cursor:pointer; color:var(--ink); }}
  .tab.active {{ background:#fff; border-color:var(--accent); font-weight:700; }}
  .tab .st {{ display:block; font-size:11px; font-weight:400; color:#8a887f; }}
  .pane {{ display:none; background:#fff; border:1px solid var(--line); border-top:none;
           border-radius:0 0 10px 10px; padding:10px 26px 28px; }}
  .pane.active {{ display:block; }}
  .groups {{ margin-top:14px; display:flex; flex-direction:column; gap:10px; }}
  .modgroup {{ display:flex; align-items:flex-start; gap:10px; }}
  .modlabel {{ flex:0 0 90px; font-size:13px; font-weight:700; color:#55534c;
               border-left:4px solid var(--accent); padding:6px 0 6px 8px; }}
  .modtabs {{ display:flex; flex-wrap:wrap; gap:6px; }}
  .tab.sub {{ font-size:13.5px; padding:6px 12px; border-radius:8px; border-bottom:1px solid var(--line); }}
  .bpane {{ display:none; padding-top:6px; }}
  .bpane.active {{ display:block; }}
  h3 {{ font-size:16px; border-left:4px solid var(--accent); padding-left:8px; margin:24px 0 8px; }}
  h4 {{ font-size:14.5px; margin:18px 0 6px; }}
  blockquote {{ margin:12px 0; padding:8px 14px; background:var(--soft);
                border-left:3px solid var(--accent); font-size:13.5px; border-radius:0 6px 6px 0; }}
  table {{ border-collapse:collapse; width:100%; font-size:14px; margin:10px 0; }}
  th,td {{ border:1px solid var(--line); padding:6px 10px; text-align:left; }}
  th {{ background:#f1efe8; }}
  code {{ background:#f1efe8; padding:1px 5px; border-radius:4px; font-size:13px; }}
  .overflow {{ overflow-x:auto; }}
  .diagram {{ margin:14px 0; }}
  .diagram svg {{ max-width:100%; height:auto; }}
  .empty {{ color:#8a887f; }}
  .specimen {{ background:#fff; border:1px solid #cfcdc4; border-radius:6px;
               box-shadow:0 1px 5px rgba(0,0,0,.07); padding:14px 20px; margin:10px 0 16px; }}
  .specimen table {{ margin:8px 0; }}
  .note {{ color:#8a887f; font-size:12px; font-weight:400; }}
</style></head><body><div class="wrap">
<h1>報價單系統 — 總覽</h1>
<div class="meta">意圖驅動設計知識層一頁投影 · 正本＝intents/ 的 md 們，本頁派生（改 md → 跑 <code>gen-總覽.py</code> 重生）</div>
<div class="strip">{strip}</div>
<div class="tabs">
  <button class="tab active" id="btn-意圖定稿" onclick="show('意圖定稿')">意圖定稿<span class="st">✅ 已確認</span></button>
  <button class="tab" id="btn-架構圖" onclick="show('架構圖')">知識架構圖<span class="st">✅ 已簽核</span></button>
  <button class="tab" id="btn-規格書" onclick="show('規格書')">功能規格書<span class="st">六本</span></button>
</div>
<section class="pane active" id="pane-意圖定稿">{intent_html}</section>
<section class="pane" id="pane-架構圖">{arch_html}</section>
<section class="pane" id="pane-規格書">
  {pts_html}
  <div class="groups">{''.join(book_groups)}</div>
  {''.join(book_panes)}
</section>
<script>
function show(n) {{
  document.querySelectorAll('.pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab:not(.sub)').forEach(t => t.classList.remove('active'));
  document.getElementById('pane-' + n).classList.add('active');
  document.getElementById('btn-' + n).classList.add('active');
}}
function showBook(n) {{
  show('規格書');
  document.querySelectorAll('.bpane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab.sub').forEach(t => t.classList.remove('active'));
  document.getElementById('bpane-' + n).classList.add('active');
  document.getElementById('bbtn-' + n).classList.add('active');
}}
</script>
</div></body></html>"""

(HERE / '系統總覽.html').write_text(page, encoding='utf-8')
print(f'✅ 系統總覽.html（{len(page)//1024}KB）')
