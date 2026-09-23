#!/usr/bin/env python3
"""總覽頁產生器——整條意圖驅動設計的「設計書」，一份 HTML。

正本＝intents/ 的 md 們；本頁是派生，頁面自己不存任何狀態。
從意圖站就能建：檔案還沒出生的站顯示待開始，頁面跟著站位長大。
mermaid 圖：fence 內容 hash 進 assets/ 快取，變了才重渲（mmdc parse 失敗＝出手前品質閘擋下）。

呈現形 v3（2026-08-27 全面重設計：活書版骨架＋戰情卷首＋速覽抽屜）：
- 身分＝一本「活的設計書」：深墨書封側欄（目錄＋搜尋＋列印鈕）＋單一連續文檔流，
  無任何互斥顯隱——Ctrl+F、深連結、上一頁全部誠實成立。
- 卷首・現況＝每日作戰台：出版狀態行（前三站蓋章閘門＋「逐片進行」框）＋
  下一步（只收今天能動手的）＋規格書一覽表。
- 第一章 意圖／第二章 架構＝長文閱讀面（正文 72ch 置中、表格與圖破格）；
  架構非主脊段自動收「深入 ▸」；主流程時間軸＝步驟×規格書對照，只掛書名 chip。
- 第三章 規格書＝每本書一個正式章節 inline 全文＋prev/next 翻書；
  快查走「速覽抽屜」（非模態、可 ‹› 翻本、麵包屑回上一本）。
- 附錄A 驗收清單＝分組（通則＋每本書）＋狀態/模組 chips 篩選＋列 inline 展開＋
  螢幕常駐簽核區；全過的組預設收合。
- 版權頁＝這頁怎麼生成的。
- 三條鐵律：口徑唯一（統計只出自 build_rollup）；同一筆資料全站最多兩處；一形一義。
- 狀態語彙：emoji 全退場，render 層映射成 ●✗○ 三形＋文字（md 正本不動）。
- 列印＝獨立 print-only DOM（#print-acc），永不受螢幕篩選影響；
  出貨條件：灰階印一張，全數條目、狀態可辨才算過。
- 一切機械派生，不硬編：
  模組與規格書狀態 ← 架構圖〈對照表〉；流程與步驟 ← 架構圖〈流程〉子段的 mermaid 節點（①②…）；
  步驟×規格書 ← 規格書檔頭「〈流程名〉①②」錨（多流程時各流程各自編號）；
  驗收自動錨 ← 規格書〈對應實作〉「測試：`path`」＋檔內 test_ac{n} ↔ 驗收第 n 條；
  原則守護 ← 架構圖〈原則〉表的「如何守住」欄；
  測試結果 ← assets/驗收結果.json（python3 intents/run-驗收.py 產）——沒跑過就標「未跑」，不假裝；
  手動驗收 ← 驗收條行尾標〔✅手動 YYYY-MM-DD〕（寫回 md 正本，不寫在頁上）；
  待辦 ← 失敗測試＋施工中規格書〈對應實作〉的 ⏳ 行＋原則未寫＋規格書 🔴 判斷點＋（架構未簽時）意圖⑤待回答。
跑法：python3 intents/gen-系統總覽.py
"""
import hashlib
import html
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
ASSETS = HERE / 'assets'

THEME = {"theme": "base", "themeVariables": {
    "primaryColor": "#EEEDFE", "primaryBorderColor": "#7F77DD",
    "primaryTextColor": "#26215C", "lineColor": "#5F5E5A",
    "textColor": "#26215C", "edgeLabelBackground": "#F4F4F2"}}

CIRC = {c: i + 1 for i, c in enumerate('①②③④⑤⑥⑦⑧⑨')}
CIRC_R = {v: k for k, v in CIRC.items()}


def render_mermaid(src: str) -> str:
    """fence → 內嵌 SVG（hash 快取；沒 mmdc 又沒快取＝硬錯，不吐爛頁）。
    圖保留原生寬：窄容器裡橫向捲、不硬縮到字看不見；點圖開 lightbox。"""
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
    # Mermaid CLI 預設每張圖都使用 my-svg；同頁內嵌多張會讓 style／marker ID 互相污染。
    s = s.replace('my-svg', f'mmd-{key}')
    natural = m.group(1) if (m := re.search(r'max-width:\s*([\d.]+)px', s[:600])) else None
    w = f' style="width:{natural}px"' if natural else ''
    return (f'<figure class="diagram breakout" data-zoom tabindex="0" role="button" '
            f'aria-label="放大圖"><div class="diagram-pan"{w}>{s}</div></figure>')


# ---------- 讀正本 ----------

def load(name):
    p = HERE / f'{name}.md'
    return p.read_text(encoding='utf-8') if p.exists() else None


def section(md, title):
    """## title 起、到下一個同級 ## 為止（含子 ###）。"""
    m = re.search(rf'^## {re.escape(title)}.*?$(.*?)(?=^## |\Z)', md or '', re.M | re.S)
    return m.group(0) if m else ''


def tables_in(block):
    """block 裡的每張 md 表 → list of rows（cells 原文，不含分隔列）。"""
    out, rows = [], []
    for ln in (block or '').splitlines():
        if ln.startswith('|'):
            if not re.match(r'^\|[\s\-|]+\|$', ln):
                rows.append([c.strip() for c in ln.strip('|').split('|')])
        elif rows:
            out.append(rows)
            rows = []
    if rows:
        out.append(rows)
    return out


intent_md = load('意圖定稿')
arch_md = load('架構圖')

m = re.search(r'✅ 已確認 (\d{4}-\d{2}-\d{2})', intent_md or '')
intent_date = m.group(1) if m else None
m = re.search(r'✅ 已簽核 (\d{4}-\d{2}-\d{2})', arch_md or '')
arch_date = m.group(1) if m else None

# 意圖⑤待回答（架構還沒簽核時＝擋在架構站前的待辦）
open_questions = [ln.lstrip('- ').strip()
                  for ln in section(intent_md, '⑤ 待回答').splitlines()
                  if ln.startswith('- ')] if intent_md else []

# 模組 ← 架構圖〈對照表〉
modules = []          # {name, data[], flow, principles[], books[(name,status)], note}
book_status = {}      # 規格書名 → 狀態字（對照表是唯一來源）
if arch_md:
    for tbl in tables_in(section(arch_md, '模組')):
        if not tbl or '模組' not in tbl[0][0]:
            continue
        for row in tbl[1:]:
            name = row[0].strip('*').strip()
            col5 = row[4] if len(row) > 4 else ''
            # 狀態括號一組共用：「[A](A.md)、[B](B.md)（✅ 已定稿）」＝A、B 都已定稿；
            # 組與組用；隔開。沒掛狀態括號的連結＝引用別本，不算本模組的書。
            books = []
            for grp in re.split(r'[；;]', col5):
                m = re.search(r'（([^（）]+)）\s*$', grp.strip())
                if not m:
                    continue
                st = m.group(1)
                books += [(b, st) for _, b in re.findall(r'\[([^\]]+)\]\(([^)]+?)\.md\)', grp)]
            for b, st in books:
                book_status[b] = st
            note = col5 if not books else ''
            modules.append({
                'name': name,
                'data': [d.strip() for d in re.sub(r'[*`]', '', row[1]).split('、') if d.strip()],
                'flow': row[2],
                'principles': [int(n) for n in re.findall(r'\d+', row[3] if len(row) > 3 else '')],
                'books': books, 'note': note,
            })
        break

# 原則 ← 架構圖〈原則〉表
principles = []       # {no, text, guard, how, tests[], testfile}
if arch_md:
    for tbl in tables_in(section(arch_md, '原則')):
        for row in tbl[1:]:
            if not row[0].strip().isdigit():
                continue
            how = row[3] if len(row) > 3 else ''
            principles.append({
                'no': int(row[0]), 'text': row[1], 'guard': row[2], 'how': how,
                'tests': re.findall(r'test_\w+', how),
                'testfile': (m.group(1) if (m := re.search(r'`([^`:]*tests\.py)', how)) else None),
            })
        break

# 流程 ← 架構圖〈流程〉的 ### 子段：一段＝一條流程；步驟＝該段 mermaid 節點裡的 ①②…
flows = []            # {name, body, steps: {n: 步驟文字}}
for m in re.finditer(r'^### (.+?)$\n(.*?)(?=^### |\Z)', section(arch_md, '流程') if arch_md else '', re.M | re.S):
    fname = re.split(r'[（(；;]', m.group(1))[0].strip()
    body = m.group(2)
    steps = {}
    for fence in re.findall(r'```mermaid\n(.*?)```', body, re.S):
        for lbl in re.findall(r'"([^"]*[①-⑨][^"]*)"', fence):
            c = re.search(r'[①-⑨]', lbl).group(0)
            text = re.sub(r'<br\s*/?>', ' ', lbl).replace(c, '', 1).strip(' ：:')
            steps.setdefault(CIRC[c], text)
    flows.append({'name': fname, 'body': body, 'steps': steps})


def parse_book(name):
    t = load(name)
    if t is None:
        return None
    head = t.splitlines()[2] if len(t.splitlines()) > 2 else ''
    module = m.group(1).strip() if (m := re.search(r'> 模組：([^／]+)／', head)) else ''
    action = ''
    if (m := re.search(r'／動作：(.+)$', head)):
        action = re.sub(r'（[^（）]*[①-⑨][^）]*）', '', m.group(1)).strip()
    flow_steps = {}
    for fname, digits in re.findall(r'([一-鿿A-Za-z0-9]+?)([①-⑨]+)', head):
        flow_steps.setdefault(fname, []).extend(CIRC[c] for c in digits)
    summary = ''
    if (m := re.search(r'##\s*這個動作在做什麼\s*\n+(.+)', t)):
        summary = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', m.group(1).strip())
    acc = []
    for item in re.findall(r'^\d+\.\s+(.+)$', section(t, '驗收'), re.M):
        manual = m.group(0) if (m := re.search(r'〔✅\s*手動[^〕]*〕', item)) else None
        acc.append({'text': item.replace(manual, '').strip() if manual else item,
                    'manual': manual})
    impl = section(t, '對應實作')
    testfile = m.group(1) if (m := re.search(r'測試：`([^`]+)`', impl)) else None
    pending = [re.sub(r'^- ', '', ln).strip() for ln in impl.splitlines()
               if ln.startswith('- ') and '⏳' in ln]
    decisions = [re.sub(r'^- ', '', ln).strip() for ln in section(t, '判斷點').splitlines()
                 if ln.startswith('- ') and '🔴' in ln]
    return {'name': name, 'md': t, 'module': module, 'action': action,
            'flow_steps': flow_steps, 'summary': summary, 'acc': acc,
            'testfile': testfile, 'pending': pending, 'decisions': decisions}


BOOKS = {}            # 名 → book dict（照對照表順序）
for mod in modules:
    for bname, _ in mod['books']:
        b = parse_book(bname)
        if b:
            BOOKS[bname] = b
# 在硬碟上、卻沒掛進對照表的書＝漂移，硬錯提醒（不默默漏）
for p in sorted(HERE.glob('*.md')):
    n = p.stem
    if n not in BOOKS and n not in ('意圖定稿', '架構圖'):
        sys.exit(f'規格書 {n}.md 沒掛在架構圖〈對照表〉——先回架構圖掛上（正本才是來源）')

# ---------- 測試對帳 ----------

def test_defs(relpath):
    p = ROOT / relpath
    return set(re.findall(r'def (test_\w+)', p.read_text(encoding='utf-8'))) if p.exists() else set()


for b in BOOKS.values():
    defs = test_defs(b['testfile']) if b['testfile'] else set()
    ac_map = {}
    for t in defs:
        if (m := re.match(r'test_ac(\d+)', t)):
            ac_map[int(m.group(1))] = t
    b['ac_map'] = ac_map

RESULTS, RAN_AT = {}, None
res_p = ASSETS / '驗收結果.json'
if res_p.exists():
    d = json.loads(res_p.read_text(encoding='utf-8'))
    RESULTS, RAN_AT = d.get('results', {}), d.get('ran_at')

for pr in principles:
    defs = test_defs(pr['testfile']) if pr['testfile'] else set()
    pr['tests'] = [t for t in pr['tests'] if not defs or t in defs]

# 測試結果比正本舊 → 卷首掛琥珀徽章提醒（機械比 mtime，不猜）
STALE = False
if res_p.exists():
    res_mtime = res_p.stat().st_mtime
    STALE = any(p.stat().st_mtime > res_mtime for p in HERE.glob('*.md'))

# ---------- 唯一口徑：狀態與統計 ----------
# 一條驗收（或一條原則）只會是下面六種之一；全站符號共三形（●✗○），色形雙編碼。

TOKENS = {  # state → (css tone, 詞, 形)
    'pass':     ('ok',   '通過',     '●'),
    'manual':   ('ok',   '手動過',   '●'),
    'fail':     ('fail', '未過',     '✗'),
    'written':  ('wait', '已寫未跑', '○'),
    'todo':     ('wait', '待驗',     '○'),
    'unwritten': ('wait', '未寫',    '○'),
}


def item_state(b, i, item):
    if item['manual']:
        return 'manual'
    t = b['ac_map'].get(i)
    if t:
        v = RESULTS.get(t)
        if v == 'pass':
            return 'pass'
        if v == 'fail':
            return 'fail'
        return 'written'
    return 'todo'


def principle_state(pr):
    if not pr['tests']:
        return 'unwritten'
    if not RESULTS:
        return 'written'
    return 'pass' if all(RESULTS.get(t) == 'pass' for t in pr['tests']) else 'fail'


def token(state, extra=''):
    tone, word, shape = TOKENS[state]
    return f'<span class="tok {tone}"><i>{shape}</i>{html.escape(extra or word)}</span>'


def manual_date(item):
    m = re.search(r'(\d{4}-)?(\d{2}-\d{2})', item['manual'] or '')
    return m.group(2) if m else ''


def build_rollup():
    zero = {'total': 0, 'pass': 0, 'manual': 0, 'fail': 0, 'written': 0, 'todo': 0, 'unwritten': 0}
    by_book = {}
    for bn, b in BOOKS.items():
        c = dict(zero)
        for i, item in enumerate(b['acc'], 1):
            c['total'] += 1
            c[item_state(b, i, item)] += 1
        c['verified'] = c['pass'] + c['manual']
        by_book[bn] = c
    books = {k: sum(v[k] for v in by_book.values()) for k in list(zero) + ['verified']}
    pr = dict(zero)
    for p in principles:
        pr['total'] += 1
        pr[principle_state(p)] += 1
    pr['verified'] = pr['pass']
    total = {k: books[k] + pr[k] for k in books}
    return {'by_book': by_book, 'books': books, 'principles': pr, 'all': total}


ROLLUP = build_rollup()


def full_count_sentence():
    """全稱句——全站凡出現總驗收數字，只准用這一句。"""
    a, b, p = ROLLUP['all'], ROLLUP['books'], ROLLUP['principles']
    return (f'已驗 {a["verified"]}／{a["total"]}'
            f'（規格書 {b["verified"]}／{b["total"]}・原則 {p["verified"]}／{p["total"]}）')


def book_stage(bn):
    """一本書走到哪：施工中／完工／排隊中（規格已定稿、還沒動工）。"""
    st = book_status.get(bn, '')
    if '施工中' in st:
        return ('busy', '施工中')
    c = ROLLUP['by_book'][bn]
    if c['total'] and c['verified'] == c['total']:
        return ('ok', '完工')
    return ('wait', '排隊中')


def stage_pill(bn):
    tone, word = book_stage(bn)
    return f'<span class="pill {tone}">{word}</span>'


active_books = [bn for bn in BOOKS if book_stage(bn)[1] == '施工中']

# 壓縮詞 → 白話（只在 render 層替換，md 正本不動）
GLOSSARY = [
    ('未切', '還沒立規格書'),
    ('不切本', '維持一般增刪查改、不另立規格書'),
]


def plain_note(text):
    out = text
    for k, v in GLOSSARY:
        out = out.replace(k, v)
    return out


def clean_pending(text):
    """施工缺口行 → 白話短句：剝 emoji 與狀態雜訊、壓平冒號。"""
    t = re.sub(r'[⏳✅🔴◐]', '', text).strip()
    t = re.sub(r'\s+', ' ', t).replace('： ', '：')
    if '：' in t:
        label, rest = t.split('：', 1)
        return f'{label}——{rest.strip()}'
    return t


# ---------- md → html ----------

def inline(s: str, plain_links=False) -> str:
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'〔([^〕]*)〕', r'<span class="note">〔\1〕</span>', s)

    def link(m):
        text, href = m.group(1), m.group(2)
        if plain_links:
            return text
        name = href.split('#')[0].removesuffix('.md')
        if name == '架構圖':
            return f'<a href="#sec-架構">{text}</a>'
        if name == '意圖定稿':
            return f'<a href="#sec-意圖">{text}</a>'
        if name in BOOKS:
            return f'<a href="#book-{name}">{text}</a>'
        return f'<a href="{href}">{text}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, s)


def md_to_html(text: str, book: str = None) -> str:
    """book 給了＝規格書內文：〈驗收〉的 ol 逐條掛 id（速覽/附錄A 錨定用）。"""
    out, i, lines = [], 0, text.splitlines()
    spec_open = False
    cur_h3 = ''
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
                       else f'<pre class="breakout"><code>{html.escape(body)}</code></pre>')
            continue
        if ln.startswith('# '):
            i += 1; continue
        if ln.startswith('### '):
            out.append(f'<h4>{inline(ln[4:])}</h4>')
        elif ln.startswith('## '):
            if spec_open:
                out.append('</div>'); spec_open = False
            cur_h3 = ln[3:].strip()
            out.append(f'<h3>{inline(ln[3:])}</h3>')
            if ln[3:].startswith('樣張'):
                out.append('<div class="specimen breakout">'); spec_open = True
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
            out.append(f'<div class="overflow breakout"><table><thead><tr>{head}</tr></thead>'
                       f'<tbody>{body}</tbody></table></div>')
            continue
        elif re.match(r'^(\d+\.|-) ', ln):
            tag = 'ol' if ln[0].isdigit() else 'ul'
            items, n = [], 0
            acc_ol = book and tag == 'ol' and cur_h3.startswith('驗收')
            while i < len(lines) and re.match(r'^(\d+\.|-) ', lines[i]):
                n += 1
                iid = f' id="acc-{book}-{n}"' if acc_ol else ''
                items.append(f'<li{iid}>' + inline(re.sub(r'^(\d+\.|-) ', '', lines[i])) + '</li>'); i += 1
            out.append(f'<{tag}>' + ''.join(items) + f'</{tag}>'); continue
        elif ln.strip():
            out.append(f'<p>{inline(ln)}</p>')
        i += 1
    if spec_open:
        out.append('</div>')
    return '\n'.join(out)


def preamble(md):
    """# 標題之後、第一個 ## 之前的引言（狀態 blockquote 等）。"""
    m = re.search(r'\A(.*?)(?=^## )', md or '', re.M | re.S)
    return m.group(1) if m else (md or '')


def plain_text(md):
    t = re.sub(r'```.*?```', ' ', md or '', flags=re.S)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = re.sub(r'[#>*`|—\-]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


# ---------- 卷首：出版狀態行 ----------

def gates_html():
    n = len(BOOKS)
    n_settled = sum(1 for st in book_status.values() if '已定稿' in st or '施工中' in st)
    gates = [
        ('意圖', '#sec-意圖',
         ('done', f'已確認 {intent_date[5:]}') if intent_date else
         (('busy', '收斂中') if intent_md else ('wait', '未開始'))),
        ('架構', '#sec-架構',
         ('done', f'已簽核 {arch_date[5:]}') if arch_date else
         (('busy', '草稿待簽') if arch_md else ('wait', '未開始'))),
        ('規格', '#sec-規格書',
         ('done', f'{n} 本定稿') if n and n_settled == n else
         (('busy', f'{n_settled}／{n} 本定稿') if n else ('wait', '未開始'))),
    ]
    cells = []
    for name, href, (tone, label) in gates:
        mark = '✓' if tone == 'done' else ('◌' if tone == 'wait' else '…')
        cells.append(f'<a class="gate {tone}" href="{href}">'
                     f'<span class="gate-mark">{mark}</span>'
                     f'<span class="gate-name">{name}</span>'
                     f'<span class="gate-note">{html.escape(label)}</span></a>')
    a = ROLLUP['all']
    if not BOOKS:
        piece = '<span class="piece-line">規格書出生後，這裡開始逐本施工與驗收。</span>'
    else:
        segs = [f'<a href="#sec-規格書">施工中 {len(active_books)} 本</a>' if active_books
                else '<span>目前沒有書在施工</span>',
                f'<a href="#sec-驗收">{full_count_sentence()}</a>']
        if a['fail']:
            segs.append(f'<a class="seg-fail" href="#sec-驗收?status=fail">'
                        f'<i>✗</i> {a["fail"]} 條測試未過</a>')
        elif RESULTS is not None and not RESULTS and (a['written'] or any(b["ac_map"] for b in BOOKS.values())):
            segs.append('<span class="seg-wait">測試未跑</span>')
        piece = '<span class="piece-line">' + '<span class="dotsep">・</span>'.join(segs) + '</span>'
    return (f'<div class="gates">{"".join(cells)}'
            f'<div class="piece"><span class="piece-tag">逐片進行（施工×驗收）</span>{piece}</div></div>')


# ---------- 卷首：下一步 ----------

def todos_html():
    todos = []  # (tone, html)
    if RESULTS:
        for bname, b in BOOKS.items():
            for i, _ in enumerate(b['acc'], 1):
                t = b['ac_map'].get(i)
                if t and RESULTS.get(t) == 'fail':
                    todos.append(('fail', f'修 <a href="#acc-{bname}-{i}">{bname}・驗收第 {i} 條</a>'
                                          f'——<code>{t}</code> 沒過'))
    for bname, b in BOOKS.items():
        for d in b['decisions']:
            todos.append(('fail', f'<a href="#book-{bname}">{bname}</a> 有判斷待拍：'
                                  f'{inline(re.sub(r"🔴", "", d).strip())}'))
    if not arch_date:
        for q in open_questions:
            todos.append(('busy', f'回答意圖⑤：{inline(q)}　<a class="todo-go" href="#sec-意圖">第一章 →</a>'))
        if arch_md:
            todos.append(('busy', '知識架構圖起草了、還沒簽核　<a class="todo-go" href="#sec-架構">第二章 →</a>'))
    for bname in active_books:
        for pend in BOOKS[bname]['pending']:
            todos.append(('busy', f'<a href="#book-{bname}">{bname}</a> 還缺：'
                                  f'{inline(clean_pending(pend))}'))
    unguarded = [p for p in principles if not p['tests']]
    if unguarded:
        nos = '、'.join(str(p['no']) for p in unguarded)
        todos.append(('wait', f'給原則 {nos} 補保護方式　<a class="todo-go" href="#arch-原則">第二章・原則 →</a>'))
    if not RESULTS and any(b['ac_map'] for b in BOOKS.values()):
        todos.append(('busy', '跑一輪測試：<code data-copy>python3 intents/run-驗收.py</code>'
                              '<button type="button" class="copybtn" data-copybtn>複製</button>'))
    if not todos:
        return ('<p class="todo-clear">沒有阻塞——從下面的一覽表挑一本排隊中的規格書開工。</p>')
    rows = ''.join(f'<li class="todo-{tone}">{body}</li>' for tone, body in todos)
    return f'<ol class="todo">{rows}</ol>'


# ---------- 規格書一覽表（卷首與第三章共用） ----------

def steps_label(b):
    return '・'.join(f'{fn}{"".join(CIRC_R[n] for n in sorted(ns))}'
                     for fn, ns in b['flow_steps'].items())


def ledger_html(idprefix):
    head = ('<div class="lrow lhead" aria-hidden="true"><span>規格書</span><span>模組</span>'
            '<span>狀態</span><span>驗收</span><span>主流程</span><span>施工缺口</span><span></span></div>')
    rows = []
    for bn, b in BOOKS.items():
        c = ROLLUP['by_book'][bn]
        tone, stage = book_stage(bn)
        gap = clean_pending(b['pending'][0]) if stage == '施工中' and b['pending'] else ''
        acc_txt = f'{c["verified"]}／{c["total"]} 過' if c['total'] else '—'
        acc_tone = 'ok' if c['total'] and c['verified'] == c['total'] else ('fail' if c['fail'] else 'wait')
        rows.append(
            f'<div class="lrow">'
            f'<a class="l-name" href="#book-{bn}">{bn}</a>'
            f'<span class="l-mod">{b["module"]}</span>'
            f'<span class="l-stage"><span class="pill {tone}">{stage}</span></span>'
            f'<a class="l-acc tok {acc_tone}" href="#grp-{bn}"><i>{"●" if acc_tone == "ok" else ("✗" if acc_tone == "fail" else "○")}</i>{acc_txt}</a>'
            f'<span class="l-steps">{steps_label(b) or "—"}</span>'
            f'<span class="l-gap">{html.escape(gap)}</span>'
            f'<button type="button" class="l-peek" data-peek="{bn}" aria-label="速覽 {bn}">速覽</button>'
            f'</div>')
    return f'<div class="ledger" id="{idprefix}-ledger">{head}{"".join(rows)}</div>'


def nonbook_html():
    nonbook = [(mo['name'], mo['note']) for mo in modules if mo['note']]
    if not nonbook:
        return ''
    lis = ''.join(f'<li><b>{html.escape(n)}</b>——{inline(plain_note(t))}</li>' for n, t in nonbook)
    return (f'<aside class="quiet"><b>沒有規格書的模組</b><ul>{lis}</ul></aside>')


# ---------- 第二章 架構（主脊／深入分層＋時間軸） ----------

SPINE_SECTIONS = ['這個系統是什麼', '模組', '流程', '原則', '現在不做']

arch_secs = []        # (label, full_title, 該段 md)
if arch_md:
    for m in re.finditer(r'^## (.+?)$(.*?)(?=^## |\Z)', arch_md, re.M | re.S):
        label = re.split(r'[（(；;]', m.group(1))[0].strip()
        arch_secs.append((label, m.group(1).strip(), m.group(0)))


def flow_map_html(f):
    """一條流程的「步驟 × 規格書」對照——時間軸只掛書名 chip，統計不進來（鐵律B）。"""
    if not f['steps']:
        return ''
    items = []
    for n in sorted(f['steps']):
        covers = [bn for bn, b in BOOKS.items() if n in b['flow_steps'].get(f['name'], [])]
        chips = ''.join(f'<a class="chip" href="#book-{bn}">{bn}</a>' for bn in covers) \
            or '<span class="chip chip-miss">尚無規格書</span>'
        items.append(f'<li><span class="fm-no">{CIRC_R[n]}</span>'
                     f'<span class="fm-text">{inline(f["steps"][n])}</span>'
                     f'<span class="fm-chips">{chips}</span></li>')
    unanchored = [bn for bn, b in BOOKS.items()
                  if f['name'] == flows[0]['name'] and not b['flow_steps']]
    extra = ''
    if unanchored:
        chips = ''.join(f'<a class="chip" href="#book-{bn}">{bn}</a>' for bn in unanchored)
        extra = (f'<li class="fm-extra"><span class="fm-no">＋</span>'
                 f'<span class="fm-text">不掛在流程步驟上、獨立驗收的書</span>'
                 f'<span class="fm-chips">{chips}</span></li>')
    return (f'<div class="flowmap"><p class="flowmap-cap">每一步由哪本規格書接住</p>'
            f'<ol>{"".join(items)}{extra}</ol></div>')


def arch_chapter_body():
    if not arch_md:
        return '<p class="empty">這一站還沒走到——檔案出生後重跑 gen 就會長出來。</p>'
    out = [f'<div class="docmeta">{md_to_html(preamble(arch_md))}</div>']
    for label, full_title, sec_md in arch_secs:
        anchor = f'arch-{label}'
        if label == '流程':
            inner = [f'<h3 data-spy id="{anchor}">{inline(full_title)}</h3>']
            for j, f in enumerate(flows):
                block = md_to_html(re.sub(r'^### .*$', '', f['body'], flags=re.M)) + flow_map_html(f)
                if j == 0:
                    inner.append(f'<h4>{html.escape(f["name"])}</h4>{block}')
                else:
                    inner.append(f'<details class="fold"><summary>{html.escape(f["name"])}'
                                 f'<span class="fold-hint">展開</span></summary>{block}</details>')
            out.append(''.join(inner))
        elif label in SPINE_SECTIONS:
            body = md_to_html(sec_md)
            body = re.sub(r'^<h3>', f'<h3 data-spy id="{anchor}">', body, count=1)
            out.append(body)
        else:
            body = md_to_html(re.sub(r'^## .*$', '', sec_md, count=1, flags=re.M))
            out.append(f'<details class="fold" id="{anchor}"><summary>{inline(full_title)}'
                       f'<span class="fold-hint">這段是給要下手改的人看的</span></summary>{body}</details>')
    return '\n'.join(out)


# ---------- 第三章：書章 ----------

def book_chapter(bn, idx):
    b = BOOKS[bn]
    c = ROLLUP['by_book'][bn]
    acc_link = (f'<a class="tok {"ok" if c["verified"] == c["total"] and c["total"] else "wait"}" '
                f'href="#grp-{bn}"><i>{"●" if c["verified"] == c["total"] and c["total"] else "○"}</i>'
                f'驗收 {c["verified"]}／{c["total"]} 過</a>') if c['total'] else ''
    names = list(BOOKS)
    i = names.index(bn)
    prev_a = f'<a href="#book-{names[i-1]}">‹ {names[i-1]}</a>' if i > 0 else '<span></span>'
    next_a = f'<a href="#book-{names[i+1]}">{names[i+1]} ›</a>' if i < len(names) - 1 else '<span></span>'
    return (f'<article class="book" id="book-{bn}" data-book="{bn}">'
            f'<header class="book-head" data-spy data-book-head="{bn}">'
            f'<p class="eyebrow">3.{idx}・{b["module"]}模組</p>'
            f'<h3 class="book-title">{bn}</h3>'
            f'<p class="book-meta">{stage_pill(bn)}{acc_link}</p></header>'
            f'<div class="prose">{md_to_html(b["md"], book=bn)}</div>'
            f'<nav class="book-foot">{prev_a}{next_a}</nav>'
            f'</article>')


# ---------- 附錄A：驗收清單 ----------

def acc_expand(bn, i, item, state):
    t = BOOKS[bn]['ac_map'].get(i)
    bits = []
    if t:
        v = RESULTS.get(t)
        judge = {'pass': '自動測試實跑通過', 'fail': '自動測試實跑沒過'}.get(v, '測試已寫，這輪還沒跑')
        bits.append(f'<p>{judge}：<code>{t}</code>（<code>{html.escape(BOOKS[bn]["testfile"] or "")}</code>）</p>')
    elif state == 'manual':
        bits.append(f'<p>人工核對通過（{manual_date(item)}），紀錄寫在規格書正本那一條的行尾。</p>')
    else:
        bits.append('<p>這條還沒有自動測試：能自動的補 <code>test_ac編號</code>，跑不了自動的（畫面、可用性）人工驗。</p>')
    bits.append(f'<p class="arow-links"><button type="button" class="chip" data-peek="{bn}" '
                f'data-anchor="acc-{bn}-{i}">速覽這本書・第 {i} 條</button>'
                f'<a class="chip" href="#acc-{bn}-{i}">在第三章開啟 →</a></p>')
    return ''.join(bits)


def acc_group(bn):
    b, c = BOOKS[bn], ROLLUP['by_book'][bn]
    rows = []
    for i, item in enumerate(b['acc'], 1):
        state = item_state(b, i, item)
        extra = manual_date(item) and f'手動過 {manual_date(item)}'
        rows.append(
            f'<div class="arow" data-state="{state}" data-mod="{b["module"]}" '
            f'data-search="{html.escape(re.sub(r"[*`〔〕]", "", item["text"]).lower())}">'
            f'<button type="button" class="arow-head" aria-expanded="false">'
            f'<span class="arow-no">{i}</span>'
            f'<span class="arow-text">{inline(item["text"], plain_links=True)}</span>'
            f'{token(state, extra)}</button>'
            f'<div class="arow-more" hidden>{acc_expand(bn, i, item, state)}</div></div>')
    all_ok = c['total'] and c['verified'] == c['total']
    return (f'<details class="agrp" id="grp-{bn}"{"" if all_ok else " open"}>'
            f'<summary><b>{bn}</b><span class="agrp-sub">{b["module"]}模組・{c["total"]} 條・'
            f'{c["verified"]}／{c["total"]} 過</span>{stage_pill(bn)}<span class="chev">›</span></summary>'
            f'{"".join(rows)}</details>')


def acc_principles_group():
    rows = []
    for pr in principles:
        state = principle_state(pr)
        tests = ' '.join(f'<code>{t}</code>' for t in pr['tests'])
        more = (f'<p>怎麼守：{inline(pr["guard"])}</p>'
                + (f'<p>自動測試：{tests}</p>' if tests else
                   '<p>還沒有保護方式——補上測試之前，這條原則只靠人記得。</p>')
                + '<p class="arow-links"><a class="chip" href="#arch-原則">→ 第二章・原則</a></p>')
        rows.append(
            f'<div class="arow" data-state="{state}" data-mod="原則" '
            f'data-search="{html.escape(re.sub(r"[*`]", "", pr["text"] + " " + pr["guard"]).lower())}">'
            f'<button type="button" class="arow-head" aria-expanded="false">'
            f'<span class="arow-no">{pr["no"]}</span>'
            f'<span class="arow-text">{inline(pr["text"], plain_links=True)}</span>'
            f'{token(state)}</button>'
            f'<div class="arow-more" hidden>{more}</div></div>')
    p = ROLLUP['principles']
    return (f'<details class="agrp" id="grp-原則" open>'
            f'<summary><b>通則（重要原則）</b><span class="agrp-sub">整個系統都要遵守・{p["total"]} 條・'
            f'{p["verified"]}／{p["total"]} 過</span><span class="chev">›</span></summary>'
            f'{"".join(rows)}</details>')


def acc_chips():
    a = ROLLUP['all']
    states = [('all', '全部', a['total'], ''),
              ('pass', '通過', a['pass'], 'ok'), ('manual', '手動過', a['manual'], 'ok'),
              ('open', '待驗', a['todo'] + a['written'], 'wait'),
              ('fail', '未過', a['fail'], 'fail'), ('unwritten', '未寫', a['unwritten'], 'wait')]
    def state_dot(tone):
        return f'<i class="dot {tone}"></i>' if tone else ''

    schips = ''.join(
        f'<button type="button" class="fchip{" active" if k == "all" else ""}" data-fstate="{k}" '
        f'aria-pressed="{"true" if k == "all" else "false"}">'
        f'{state_dot(tone)}{w} {n}</button>'
        for k, w, n, tone in states if n or k == 'all')
    mods = ['原則'] + [mo['name'] for mo in modules if mo['books']]
    mchips = '<button type="button" class="fchip active" data-fmod="all" aria-pressed="true">全部模組</button>' + ''.join(
        f'<button type="button" class="fchip" data-fmod="{m}" aria-pressed="false">{m}</button>'
        for m in dict.fromkeys(mods))
    return (f'<div class="accbar" id="accbar"><div class="fchips">{schips}</div>'
            f'<div class="fchips fchips-mod">{mchips}'
            f'<span class="accsearch"><input id="asearch" type="search" placeholder="搜驗收條文" '
            f'aria-label="搜驗收條文"><button type="button" class="clearbtn" id="aclear" hidden aria-label="清除">✕</button></span>'
            f'<span class="acount" id="acount"></span></div>'
            f'<p class="acclegend">通過＝自動測試實跑通過；手動過＝人工核對、紀錄在正本；待驗＝還沒驗，驗完才簽。</p></div>')


def signoff_html():
    a = ROLLUP['all']
    open_n = a['todo'] + a['written'] + a['unwritten']
    partial = (f'，本次屬<b>部分驗收</b>，其餘 {open_n} 條驗畢後另行補簽' if open_n else '，全數驗畢')
    return (f'<div class="signoff" id="signoff"><h4>簽核</h4>'
            f'<p>本人已逐條核對以上驗收項目：{full_count_sentence()}'
            f'{"、測試未過 " + str(a["fail"]) + " 條" if a["fail"] else ""}{partial}。</p>'
            f'<div class="sign-row"><span>需求方簽核：＿＿＿＿＿＿＿＿＿＿</span>'
            f'<span>日期：＿＿＿＿＿＿＿＿</span></div>'
            f'<p class="quiet-line">要紙本？<button type="button" class="chip" data-print>列印驗收單</button>'
            f'——列印永遠出完整清單，不受上面篩選影響。</p></div>')


# ---------- 列印專用 DOM（獨立派生，永不受螢幕狀態影響） ----------

PRINT_SHAPES = {'pass': '✓ 通過', 'manual': '✓手 手動過', 'fail': '✗ 未過',
                'written': '○ 待驗', 'todo': '○ 待驗', 'unwritten': '○ 未寫'}


def print_dom():
    a = ROLLUP['all']
    groups = []
    prows = ''.join(f'<tr><td class="pbox">□</td><td>{pr["no"]}</td>'
                    f'<td>{inline(pr["text"], plain_links=True)}</td>'
                    f'<td class="pst">{PRINT_SHAPES[principle_state(pr)]}</td><td class="pnote"></td></tr>'
                    for pr in principles)
    p = ROLLUP['principles']
    groups.append(f'<h3>通則（重要原則）——{p["verified"]}／{p["total"]} 過</h3>'
                  f'<table><thead><tr><th></th><th>條</th><th>條文</th><th>狀態</th><th>備註</th></tr></thead>'
                  f'<tbody>{prows}</tbody></table>')
    for bn, b in BOOKS.items():
        c = ROLLUP['by_book'][bn]
        rows = ''.join(
            f'<tr><td class="pbox">□</td><td>{i}</td>'
            f'<td>{inline(item["text"], plain_links=True)}</td>'
            f'<td class="pst">{PRINT_SHAPES[item_state(b, i, item)]}'
            f'{" " + manual_date(item) if item["manual"] else ""}</td><td class="pnote"></td></tr>'
            for i, item in enumerate(b['acc'], 1))
        groups.append(f'<h3>{bn}（{b["module"]}模組）——{c["verified"]}／{c["total"]} 過</h3>'
                      f'<table><thead><tr><th></th><th>條</th><th>條文</th><th>狀態</th><th>備註</th></tr></thead>'
                      f'<tbody>{rows}</tbody></table>')
    open_n = a['todo'] + a['written'] + a['unwritten']
    partial = (f'，本次屬<b>部分驗收</b>，其餘 {open_n} 條驗畢後另行補簽' if open_n else '，全數驗畢')
    ran = f'測試結果為 {RAN_AT} 實際執行' if RAN_AT else '本輪自動測試尚未執行'
    return (f'<div id="print-acc" aria-hidden="true">'
            f'<h1>報價單系統・驗收單</h1>'
            f'<p class="pmeta">{full_count_sentence()}・{ran}・'
            f'圖例：✓ 通過｜✓手 手動過｜✗ 未過｜○ 待驗／未寫（□ 供現場逐條勾選）</p>'
            f'{"".join(groups)}'
            f'<div class="psign"><p>本人已逐條核對以上驗收項目：{full_count_sentence()}{partial}。</p>'
            f'<div class="sign-row"><span>需求方簽核：＿＿＿＿＿＿＿＿＿＿</span>'
            f'<span>日期：＿＿＿＿＿＿＿＿</span></div></div></div>')


# ---------- 側欄（書封＋目錄）與行動版目錄 ----------

def toc_html(sheet=False):
    a = ROLLUP['all']
    arch_subs = ''.join(
        f'<a class="toc-sub" href="#arch-{label}">{label}</a>'
        for label, _t, _s in arch_secs)
    book_subs = ''.join(
        f'<a class="toc-sub toc-book" href="#book-{bn}"><i class="dot {book_stage(bn)[0]}"></i>{bn}</a>'
        for bn in BOOKS)
    items = [
        ('sec-卷首', '卷首・現況', '', ''),
        ('sec-意圖', '第一章　意圖', '✓' if intent_date else '', ''),
        ('sec-架構', '第二章　架構', '✓' if arch_date else '', arch_subs),
        ('sec-規格書', '第三章　規格書', '', book_subs),
        ('sec-驗收', f'附錄A　驗收清單', f'{a["verified"]}/{a["total"]}', ''),
        ('sec-版權', '版權頁', '', ''),
    ]
    def toc_mark(mark):
        return f'<em>{mark}</em>' if mark else ''

    def toc_subs(subs):
        return f'<div class="toc-subs">{subs}</div>' if subs else ''

    rows = ''.join(
        f'<div class="toc-item" data-toc="{sid}">'
        f'<a class="toc-link" href="#{sid}"><span>{name}</span>'
        f'{toc_mark(mark)}</a>'
        f'{toc_subs(subs)}</div>'
        for sid, name, mark, subs in items)
    return f'<nav class="toc{" toc-sheet" if sheet else ""}" aria-label="目錄">{rows}</nav>'


def searchbox_html(idsuffix):
    return (f'<div class="searchbox"><svg class="sicon" width="13" height="13" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2.4" stroke-linecap="round">'
            f'<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>'
            f'<input type="search" id="q-{idsuffix}" placeholder="搜整本書　⌘K" aria-label="搜整本書">'
            f'<div class="sresults" id="qr-{idsuffix}" hidden></div></div>')


def search_index():
    idx = []
    if intent_md:
        idx.append({'id': 'sec-意圖', 'src': '第一章', 'title': '意圖', 'text': plain_text(intent_md)})
    for label, _t, sec_md in arch_secs:
        idx.append({'id': f'arch-{label}', 'src': '第二章', 'title': label, 'text': plain_text(sec_md)})
    for bn, b in BOOKS.items():
        idx.append({'id': f'book-{bn}', 'src': '規格書', 'title': bn, 'text': plain_text(b['md'])})
        for i, item in enumerate(b['acc'], 1):
            idx.append({'id': f'acc-{bn}-{i}', 'src': bn, 'title': f'驗收第 {i} 條',
                        'text': plain_text(item['text'])})
    for pr in principles:
        idx.append({'id': 'grp-原則', 'src': '原則', 'title': f'第 {pr["no"]} 條',
                    'text': plain_text(pr['text'] + ' ' + pr['guard'])})
    return idx


# ---------- CSS ----------

CSS = '''
  :root {
    --cover:#211f1a; --cover-ink:#efe7d6; --cover-dim:#a89f8d;
    --paper:#faf7f1; --card:#ffffff; --inset:#efe9dc;
    --ink:#26241f; --ink-2:#5d5a52; --line:#e0d9c9;
    --accent:#4a43a8; --accent-soft:#eceafb;
    --ok:#1e7a46; --ok-bg:#e2f1e6; --busy:#8f3a12; --busy-bg:#f7e6d8;
    --wait:#5d5a52; --wait-bg:#ece8dc; --fail:#b3261e; --fail-bg:#fbe5e3;
    --fs-meta:12px; --fs-ui:14px; --fs-body:15px; --fs-h3:17px; --fs-h2:22px;
    --r-lg:10px; --r-sm:6px; --r-pill:999px;
    --elev-hover:0 2px 8px rgba(48,39,24,.06);
    --elev-overlay:0 24px 64px rgba(48,39,24,.18);
    --sidebar:clamp(228px,18vw,268px); --topbar:48px;
  }
  * { box-sizing:border-box; }
  /* 跨章距離動輒上萬 px，smooth 會變成數秒的動畫——跳轉一律瞬移，靠落點高亮定位 */
  body { margin:0; font-family:'PingFang TC','Noto Sans TC',Inter,system-ui,sans-serif;
         color:var(--ink); background:var(--paper); font-size:var(--fs-body); line-height:1.8;
         -webkit-font-smoothing:antialiased; }
  a { color:var(--accent); text-decoration-thickness:1px; text-underline-offset:3px; }
  a:hover { text-decoration-thickness:2px; }
  b { font-weight:650; }
  button { font:inherit; color:inherit; background:none; border:0; padding:0; cursor:pointer; }
  code { background:var(--inset); padding:2px 6px; border-radius:var(--r-sm);
         font-size:.86em; overflow-wrap:anywhere; }
  :focus-visible { outline:2px solid var(--accent); outline-offset:2px; border-radius:2px; }
  ::selection { background:var(--accent-soft); }
  [id] { scroll-margin-top:24px; }
  .agrp { scroll-margin-top:calc(var(--accbar-h,104px) + 14px); }

  /* ── 書封側欄 ─────────────────────────── */
  .sidebar { position:fixed; inset:0 auto 0 0; width:var(--sidebar); z-index:30;
             display:flex; flex-direction:column; background:var(--cover); color:var(--cover-ink);
             padding:26px 0 18px; }
  .cover-head { padding:0 22px 18px; }
  .cover-head .eyebrow { color:#c88f6b; margin:0 0 10px; }
  .cover-title { font-size:21px; font-weight:750; letter-spacing:.01em; margin:0; line-height:1.35; }
  .cover-sub { margin:6px 0 0; font-size:var(--fs-meta); color:var(--cover-dim); }
  .eyebrow { font-size:11px; font-weight:800; letter-spacing:.14em; text-transform:uppercase;
             font-family:Inter,system-ui,sans-serif; }
  .sidebar .searchbox { margin:0 16px 12px; }
  .toc { flex:1; overflow-y:auto; padding:4px 10px 12px; scrollbar-width:thin; }
  .toc-link { display:flex; align-items:baseline; justify-content:space-between; gap:8px;
              padding:8px 12px; border-radius:var(--r-sm); color:var(--cover-ink);
              font-size:13px; text-decoration:none; opacity:.82; }
  .toc-link:hover { opacity:1; background:rgba(239,231,214,.08); }
  .toc-item.current > .toc-link { opacity:1; background:rgba(239,231,214,.12); font-weight:700;
              box-shadow:inset 3px 0 0 #c88f6b; }
  .toc-link em { font-style:normal; font-size:11px; color:var(--cover-dim);
                 font-variant-numeric:tabular-nums; }
  .toc-subs { display:none; padding:2px 0 6px; }
  .toc-item.current .toc-subs { display:block; }
  .toc-sub { display:flex; align-items:center; gap:7px; padding:4px 12px 4px 24px;
             font-size:12px; color:var(--cover-dim); text-decoration:none; border-radius:var(--r-sm); }
  .toc-sub:hover { color:var(--cover-ink); }
  .toc-sub.current { color:var(--cover-ink); font-weight:600; }
  .dot { width:7px; height:7px; flex:none; border-radius:50%; display:inline-block; }
  .dot.ok { background:#6cbf8d; } .dot.busy { background:#e0946a; }
  .dot.wait { background:#8f897c; } .dot.fail { background:#e08a83; }
  .cover-foot { padding:14px 16px 0; border-top:1px solid rgba(239,231,214,.14); }
  .printbtn { display:flex; align-items:center; justify-content:center; gap:8px; width:100%;
              padding:10px; border:1px solid rgba(239,231,214,.3); border-radius:var(--r-lg);
              color:var(--cover-ink); font-size:13px; font-weight:650; }
  .printbtn:hover { background:rgba(239,231,214,.1); }
  .cover-note { margin:10px 2px 0; font-size:11px; line-height:1.7; color:var(--cover-dim); }

  /* 搜尋框（側欄＋行動抽屜共用） */
  .searchbox { position:relative; }
  .searchbox .sicon { position:absolute; left:11px; top:50%; translate:0 -50%; color:var(--cover-dim);
                      pointer-events:none; }
  .searchbox input { width:100%; height:34px; padding:0 10px 0 32px; font:inherit; font-size:13px;
                     color:var(--cover-ink); background:rgba(239,231,214,.09);
                     border:1px solid rgba(239,231,214,.16); border-radius:8px; }
  .searchbox input::placeholder { color:var(--cover-dim); }
  .searchbox input:focus { outline:2px solid #c88f6b; outline-offset:0; }
  .sresults { position:absolute; top:calc(100% + 6px); left:0; right:0; z-index:40; max-height:320px;
              overflow-y:auto; background:var(--card); color:var(--ink); border-radius:var(--r-lg);
              box-shadow:var(--elev-overlay); padding:6px; }
  .sresults a { display:block; padding:8px 10px; border-radius:var(--r-sm); text-decoration:none;
                color:var(--ink); font-size:13px; line-height:1.55; }
  .sresults a:hover, .sresults a.sel { background:var(--accent-soft); }
  .sresults .sr-src { font-size:11px; color:var(--ink-2); margin-right:6px; }
  .sresults mark { background:transparent; color:var(--accent); font-weight:700; }
  .sresults .sr-none { padding:10px; font-size:13px; color:var(--ink-2); }

  /* ── 行動版頂列 ───────────────────────── */
  .topbar { display:none; }

  /* ── 主欄 ────────────────────────────── */
  .main { margin-left:var(--sidebar); }
  .chapter { max-width:1080px; margin:0 auto; padding:56px clamp(22px,4.5vw,56px) 64px; }
  .chapter + .chapter { border-top:1px solid var(--line); }
  .ch-head { display:flex; align-items:baseline; gap:18px; margin:0 0 30px; }
  .chno { font-family:Inter,system-ui,sans-serif; font-size:44px; font-weight:250;
          color:var(--ink-2); opacity:.55; letter-spacing:.02em; line-height:1; }
  .ch-head h2 { font-size:var(--fs-h2); font-weight:750; margin:0; letter-spacing:.01em; }
  .ch-head .eyebrow { color:var(--ink-2); display:block; margin-bottom:6px; }
  h3 { font-size:var(--fs-h3); font-weight:700; margin:40px 0 12px; scroll-margin-top:24px; }
  h4 { font-size:var(--fs-ui); font-weight:700; margin:24px 0 8px; color:var(--ink); }
  p, li { font-size:var(--fs-body); }
  .empty { color:var(--ink-2); }
  .quiet { margin:26px 0 0; padding:14px 18px; background:var(--inset); border-radius:var(--r-lg);
           font-size:13px; color:var(--ink-2); }
  .quiet b { color:var(--ink); font-size:13px; }
  .quiet ul { margin:6px 0 0; padding-left:18px; }
  .quiet li { margin:3px 0; font-size:13px; }
  .note { color:var(--ink-2); font-size:.82em; font-weight:400; }

  /* 長文（意圖／架構／書內文）：72ch 置中、寬物破格 */
  .prose > * { max-width:720px; margin-left:auto; margin-right:auto; }
  .prose > .breakout { max-width:100%; }
  .prose blockquote, .docmeta blockquote { margin:14px auto; padding:10px 16px; background:var(--inset);
               border-left:3px solid var(--line); font-size:13px; color:var(--ink-2);
               border-radius:0 var(--r-sm) var(--r-sm) 0; line-height:1.8; }
  .docmeta { max-width:720px; margin:0 auto; }
  table { border-collapse:collapse; width:100%; font-size:13px; margin:12px 0; }
  th, td { border-bottom:1px solid var(--line); padding:9px 12px; text-align:left;
           vertical-align:top; overflow-wrap:anywhere; }
  th { font-size:var(--fs-meta); font-weight:700; color:var(--ink-2); white-space:nowrap;
       border-bottom-color:var(--ink-2); }
  td:first-child { white-space:nowrap; }
  .overflow { overflow-x:auto; }
  .overflow table { min-width:640px; }
  pre { background:var(--inset); border-radius:var(--r-lg); padding:14px 16px; overflow-x:auto; }
  pre code { background:none; padding:0; }
  .specimen { background:var(--card); border:1px solid var(--line); border-radius:var(--r-lg);
              padding:18px 24px; margin:12px auto 20px; }
  .diagram { margin:18px auto; border:1px solid var(--line); border-radius:var(--r-lg);
             background:var(--card); overflow:hidden; cursor:zoom-in; position:relative; }
  .diagram-pan { overflow-x:auto; padding:14px; max-width:100%; margin:0 auto; }
  .diagram svg { display:block; height:auto; max-width:none; }
  .diagram.fits .diagram-pan { display:flex; justify-content:center; }
  .diagram.scrollable::after { content:""; position:absolute; top:0; right:0; bottom:0; width:36px;
             background:linear-gradient(to right, rgba(255,255,255,0), var(--card)); pointer-events:none; }
  .fold { max-width:720px; margin:14px auto; border:1px solid var(--line); border-radius:var(--r-lg);
          background:var(--card); }
  .fold > summary { display:flex; align-items:baseline; gap:10px; padding:12px 16px; cursor:pointer;
          list-style:none; font-weight:700; font-size:var(--fs-ui); }
  .fold > summary::-webkit-details-marker { display:none; }
  .fold > summary::before { content:"▸"; color:var(--ink-2); transition:rotate .15s; }
  .fold[open] > summary::before { rotate:90deg; }
  .fold-hint { font-weight:400; font-size:var(--fs-meta); color:var(--ink-2); }
  .fold > :not(summary) { padding:0 18px; }
  .fold > :last-child { padding-bottom:14px; }

  /* ── 卷首 ────────────────────────────── */
  .badge-stale { display:inline-flex; align-items:center; gap:7px; margin:0 0 18px; padding:7px 13px;
                 background:#f6ecd2; color:#7a5b12; border-radius:var(--r-pill); font-size:13px; }
  .gates { display:flex; align-items:stretch; gap:0; margin:6px 0 0; flex-wrap:wrap; }
  .gate { display:flex; flex-direction:column; align-items:center; gap:3px; padding:14px 20px 12px;
          min-width:118px; text-decoration:none; color:var(--ink); position:relative; }
  .gate + .gate::before { content:""; position:absolute; left:-14px; top:29px; width:28px; height:1px;
          background:var(--line); }
  .gate-mark { width:30px; height:30px; display:grid; place-items:center; border-radius:50%;
               font-size:14px; font-weight:800; background:var(--wait-bg); color:var(--wait); }
  .gate.done .gate-mark { background:var(--ok); color:#fff; }
  .gate.busy .gate-mark { background:var(--busy); color:#fff; }
  .gate-name { font-size:var(--fs-ui); font-weight:700; margin-top:4px; }
  .gate-note { font-size:var(--fs-meta); color:var(--ink-2); font-variant-numeric:tabular-nums; }
  .gate.done .gate-note { color:var(--ok); }
  .gate.busy .gate-note { color:var(--busy); }
  .gate:hover .gate-name { color:var(--accent); }
  .piece { flex:1; min-width:300px; margin-left:16px; display:flex; flex-direction:column;
           justify-content:center; gap:4px; padding:12px 20px; background:var(--inset);
           border-radius:var(--r-lg); position:relative; }
  .piece::before { content:""; position:absolute; left:-15px; top:28px; width:14px; height:1px;
           border-top:1px dashed var(--ink-2); opacity:.5; }
  .piece-tag { font-size:var(--fs-meta); font-weight:700; color:var(--busy); }
  .piece-line { font-size:var(--fs-ui); line-height:1.7; }
  .piece-line a { color:var(--ink); font-weight:650; }
  .piece-line a:hover { color:var(--accent); }
  .dotsep { color:var(--ink-2); margin:0 2px; }
  .seg-fail { color:var(--fail) !important; }
  .seg-fail i { font-style:normal; }
  .seg-wait { color:var(--ink-2); }

  .todo { list-style:none; margin:10px 0 0; padding:0; display:flex; flex-direction:column; gap:8px;
          max-width:820px; }
  .todo li { display:flex; align-items:baseline; gap:12px; padding:12px 18px; background:var(--card);
             border:1px solid var(--line); border-radius:var(--r-lg); font-size:var(--fs-ui);
             line-height:1.7; }
  .todo li::before { content:""; flex:none; width:8px; height:8px; border-radius:50%;
             translate:0 -1px; }
  .todo-fail::before { background:var(--fail); }
  .todo-busy::before { background:var(--busy); }
  .todo-wait::before { background:var(--wait); }
  .todo-go { white-space:nowrap; font-weight:650; text-decoration:none; }
  .todo-clear { margin:10px 0 0; padding:13px 18px; border:1px dashed var(--line);
                border-radius:var(--r-lg); color:var(--ok); font-size:var(--fs-ui); max-width:820px; }
  .copybtn { margin-left:8px; font-size:var(--fs-meta); font-weight:650; color:var(--accent);
             border:1px solid var(--line); border-radius:var(--r-pill); padding:2px 10px; }
  .copybtn:hover { border-color:var(--accent); }

  /* 一覽表 */
  .ledger { margin-top:10px; border:1px solid var(--line); border-radius:var(--r-lg);
            background:var(--card); overflow:hidden; }
  .lrow { display:grid; grid-template-columns:minmax(120px,1.1fr) 64px 76px 92px minmax(80px,.7fr)
          minmax(140px,1.4fr) 52px; gap:12px; align-items:center; padding:11px 18px;
          border-top:1px solid var(--line); font-size:var(--fs-ui); }
  .lrow:first-child { border-top:0; }
  .lhead { padding-top:12px; padding-bottom:8px; font-size:var(--fs-meta); color:var(--ink-2);
           font-weight:700; background:var(--paper); }
  .l-name { font-weight:700; color:var(--ink); text-decoration:none; }
  .l-name:hover { color:var(--accent); }
  .l-mod, .l-steps { font-size:var(--fs-meta); color:var(--ink-2); }
  .l-gap { font-size:var(--fs-meta); color:var(--busy); line-height:1.55; }
  .l-peek { font-size:var(--fs-meta); font-weight:650; color:var(--accent); justify-self:end;
            padding:3px 10px; border:1px solid var(--line); border-radius:var(--r-pill); }
  .l-peek:hover { border-color:var(--accent); background:var(--accent-soft); }
  .pill { display:inline-block; font-size:var(--fs-meta); font-weight:650; padding:2px 10px;
          border-radius:var(--r-pill); white-space:nowrap; }
  .pill.ok { background:var(--ok-bg); color:var(--ok); }
  .pill.busy { background:var(--busy-bg); color:var(--busy); }
  .pill.wait { background:var(--wait-bg); color:var(--wait); }
  .tok { display:inline-flex; align-items:center; gap:6px; font-size:var(--fs-meta); font-weight:650;
         white-space:nowrap; text-decoration:none; }
  .tok i { font-style:normal; font-size:10px; translate:0 -1px; }
  .tok.ok { color:var(--ok); } .tok.fail { color:var(--fail); } .tok.wait { color:var(--wait); }
  a.tok:hover { text-decoration:underline; }

  /* 流程對照（第二章） */
  .flowmap { max-width:720px; margin:16px auto; }
  .flowmap-cap { font-size:var(--fs-meta); font-weight:700; color:var(--ink-2); margin:0 0 6px; }
  .flowmap ol { list-style:none; margin:0; padding:0; border:1px solid var(--line);
                border-radius:var(--r-lg); background:var(--card); }
  .flowmap li { display:flex; align-items:baseline; gap:12px; padding:9px 16px;
                border-top:1px solid var(--line); }
  .flowmap li:first-child { border-top:0; }
  .fm-no { flex:none; color:var(--accent); font-weight:700; }
  .fm-text { flex:1; min-width:0; font-size:var(--fs-ui); }
  .fm-chips { flex:none; display:flex; gap:6px; flex-wrap:wrap; justify-content:end; }
  .fm-extra { background:var(--paper); }
  .chip { display:inline-block; font-size:var(--fs-meta); font-weight:650; color:var(--accent);
          background:none; border:1px solid var(--line); border-radius:var(--r-pill);
          padding:2px 11px; text-decoration:none; cursor:pointer; }
  .chip:hover { border-color:var(--accent); background:var(--accent-soft); }
  .chip-miss { color:var(--busy); border-style:dashed; }

  /* 書章 */
  /* 不用 content-visibility：預估高與實高差太多，跨章錨點跳轉會漂移；誠實全渲染 */
  .book { border-top:1px dashed var(--line); margin-top:44px; padding-top:36px; }
  .book-head .eyebrow { color:var(--ink-2); margin:0 0 6px; }
  .book-title { font-size:var(--fs-h2); font-weight:750; margin:0 0 8px; }
  .book-meta { display:flex; align-items:center; gap:14px; margin:0 0 8px; }
  .book-foot { display:flex; justify-content:space-between; gap:16px; max-width:720px;
               margin:30px auto 0; padding-top:14px; border-top:1px solid var(--line);
               font-size:var(--fs-ui); }
  .book-foot a { text-decoration:none; font-weight:650; }

  /* 附錄A */
  .accbar { position:sticky; top:0; z-index:20; background:var(--paper); padding:10px 0 8px;
            border-bottom:1px solid var(--line); margin-bottom:14px; }
  .fchips { display:flex; flex-wrap:wrap; gap:7px; align-items:center; }
  .fchips-mod { margin-top:7px; }
  .fchip { display:inline-flex; align-items:center; gap:7px; font-size:13px; font-weight:600;
           color:var(--ink-2); padding:4px 13px; border:1px solid var(--line);
           border-radius:var(--r-pill); background:var(--card);
           font-variant-numeric:tabular-nums; }
  .fchip:hover { border-color:var(--ink-2); color:var(--ink); }
  .fchip.active { background:var(--ink); border-color:var(--ink); color:var(--paper); }
  .fchip.active .dot { outline:1px solid var(--paper); outline-offset:1px; }
  .accsearch { position:relative; margin-left:auto; display:flex; align-items:center; }
  .accsearch input { width:200px; height:32px; padding:0 30px 0 12px; font:inherit; font-size:13px;
                     border:1px solid var(--line); border-radius:var(--r-pill); background:var(--card); }
  .accsearch input:focus { outline:2px solid var(--accent); outline-offset:-1px; }
  .clearbtn { position:absolute; right:8px; color:var(--ink-2); font-size:12px; }
  .acount { font-size:var(--fs-meta); color:var(--ink-2); white-space:nowrap;
            font-variant-numeric:tabular-nums; }
  .acclegend { margin:8px 0 0; font-size:var(--fs-meta); color:var(--ink-2); }
  .accempty { padding:22px 18px; color:var(--ink-2); font-size:var(--fs-ui); }
  .accempty button { color:var(--accent); font-weight:650; text-decoration:underline; }

  .agrp { margin:0 0 12px; border:1px solid var(--line); border-radius:var(--r-lg);
          background:var(--card); }
  .agrp > summary { display:flex; align-items:baseline; gap:12px; padding:13px 18px; cursor:pointer;
          list-style:none; position:sticky; top:var(--accbar-h,104px); background:var(--card); z-index:5;
          border-radius:var(--r-lg); }
  .agrp[open] > summary { border-bottom:1px solid var(--line); border-radius:var(--r-lg) var(--r-lg) 0 0; }
  .agrp > summary::-webkit-details-marker { display:none; }
  .agrp > summary b { font-size:15px; }
  .agrp-sub { font-size:var(--fs-meta); color:var(--ink-2); font-variant-numeric:tabular-nums; }
  .agrp .chev { margin-left:auto; color:var(--ink-2); transition:rotate .15s; }
  .agrp[open] .chev { rotate:90deg; }
  .arow { border-top:1px solid var(--line); }
  .arow:first-of-type { border-top:0; }
  .arow-head { display:flex; align-items:baseline; gap:14px; width:100%; text-align:left;
               padding:12px 18px; }
  .arow-head:hover { background:var(--paper); }
  .arow-no { flex:none; width:22px; font-size:var(--fs-meta); color:var(--ink-2); text-align:right;
             font-variant-numeric:tabular-nums; }
  .arow-text { flex:1; min-width:0; font-size:var(--fs-ui); line-height:1.7; }
  .arow-head .tok { flex:none; margin-left:auto; }
  .arow-more { padding:2px 18px 14px 54px; font-size:13px; color:var(--ink-2); background:var(--paper); }
  .arow-more p { margin:6px 0; font-size:13px; }
  .arow-links { display:flex; gap:8px; flex-wrap:wrap; }
  .flash { animation:flash 2s ease-out; }
  @keyframes flash { 0%,60% { background:#e3def6; box-shadow:inset 3px 0 0 var(--accent); }
                     100% { background:transparent; } }

  .signoff { margin:34px 0 0; padding:22px 26px; border:1px solid var(--line);
             border-radius:var(--r-lg); background:var(--card); max-width:820px; }
  .signoff h4 { margin:0 0 8px; }
  .signoff p { font-size:var(--fs-ui); margin:0 0 6px; }
  .sign-row { display:flex; gap:44px; flex-wrap:wrap; margin-top:20px; font-size:var(--fs-ui); }
  .quiet-line { margin-top:16px; font-size:var(--fs-meta); color:var(--ink-2); }

  /* 版權頁 */
  .colophon p { font-size:var(--fs-ui); color:var(--ink-2); max-width:720px; }
  .colophon code { font-size:.9em; }

  /* 速覽抽屜 */
  dialog { border:0; padding:0; }
  .peek { position:fixed; inset:0 0 0 auto; margin:0; width:min(600px,94vw); height:100dvh;
          max-height:100dvh; background:var(--paper); box-shadow:var(--elev-overlay);
          display:none; flex-direction:column; border-left:1px solid var(--line); }
  .peek[open] { display:flex; }
  .peek-head { flex:none; display:flex; align-items:center; gap:10px; padding:12px 18px;
               border-bottom:1px solid var(--line); background:var(--card); }
  .peek-crumb { font-size:var(--fs-meta); color:var(--accent); display:none; }
  .peek-crumb.on { display:inline; }
  .peek-title { font-size:15px; font-weight:750; margin-right:auto; }
  .peek-nav { display:flex; gap:2px; }
  .peek-nav button, .peek-close { width:30px; height:30px; display:grid; place-items:center;
               border:1px solid var(--line); border-radius:var(--r-sm); color:var(--ink-2); }
  .peek-nav button:hover, .peek-close:hover { color:var(--ink); border-color:var(--ink-2); }
  .peek-open-full { font-size:var(--fs-meta); font-weight:650; color:var(--accent);
               text-decoration:none; margin-right:6px; white-space:nowrap; }
  .peek-body { flex:1; overflow-y:auto; padding:6px 26px 40px; }
  .peek-body .book { border-top:0; margin-top:0; padding-top:10px; }
  .peek-body .book-foot { display:none; }
  .peek-hint { flex:none; padding:8px 18px; border-top:1px solid var(--line); font-size:11px;
               color:var(--ink-2); background:var(--card); }

  /* lightbox */
  .lightbox { margin:auto; background:var(--card); border-radius:var(--r-lg);
              box-shadow:var(--elev-overlay); width:min(96vw,1400px); max-height:92vh;
              display:none; flex-direction:column; }
  .lightbox[open] { display:flex; }
  .lightbox::backdrop { background:rgba(33,31,26,.55); }
  .lb-head { flex:none; display:flex; justify-content:flex-end; padding:10px 14px; gap:6px; }
  .lb-body { overflow:auto; padding:0 22px 26px; }
  .lb-body svg { max-width:none; }

  /* 行動版目錄 sheet */
  .sheet { margin:auto auto 0; width:100vw; max-width:100vw; max-height:82dvh; background:var(--cover);
           color:var(--cover-ink); border-radius:16px 16px 0 0; display:none; flex-direction:column; }
  .sheet[open] { display:flex; }
  .sheet::backdrop { background:rgba(33,31,26,.45); }
  .sheet-head { flex:none; display:flex; align-items:center; justify-content:space-between;
                padding:14px 20px 6px; }
  .sheet-head b { font-size:15px; }
  .sheet-close { color:var(--cover-dim); font-size:15px; padding:4px 8px; }
  .sheet .searchbox { margin:6px 16px 10px; }
  .sheet .toc { overflow-y:auto; padding-bottom:14px; }
  .sheet .toc-subs { display:block; }
  .sheet .printbtn { margin:8px 16px 16px; width:auto; }

  /* ── 響應式 ──────────────────────────── */
  @media (max-width:900px) {
    .sidebar { display:none; }
    .main { margin-left:0; }
    .topbar { display:flex; position:sticky; top:0; z-index:30; height:var(--topbar);
              align-items:center; gap:12px; padding:0 16px; background:var(--cover);
              color:var(--cover-ink); }
    .topbar-menu { display:flex; align-items:center; gap:8px; font-size:14px; font-weight:650;
              color:var(--cover-ink); }
    .topbar-now { margin-left:auto; font-size:13px; color:var(--cover-dim); white-space:nowrap;
              overflow:hidden; text-overflow:ellipsis; }
    .chapter { padding:34px 18px 44px; }
    .gates { flex-direction:column; align-items:stretch; gap:8px; }
    .gate { flex-direction:row; align-items:center; gap:12px; padding:8px 4px; min-width:0; }
    .gate + .gate::before { display:none; }
    .gate-mark { width:26px; height:26px; font-size:12px; }
    .gate-name { margin:0; }
    .gate-note { margin-left:auto; }
    .piece { margin-left:0; }
    .piece::before { display:none; }
    .lrow { grid-template-columns:minmax(0,1fr) auto auto; row-gap:4px; padding:12px 14px; }
    .lhead { display:none; }
    .l-mod, .l-steps { display:none; }
    .l-gap { grid-column:1 / -1; }
    .l-peek { grid-column:1 / -1; justify-self:end; }
    [id] { scroll-margin-top:calc(var(--topbar) + 16px); }
    .accbar { position:static; }
    .agrp { scroll-margin-top:calc(var(--topbar) + 16px); }
    .agrp > summary { top:var(--topbar); }
    .accsearch { margin-left:0; width:100%; }
    .accsearch input { width:100%; font-size:16px; }
    .searchbox input { font-size:16px; }
    .arow-more { padding-left:18px; }
    .sign-row { gap:20px; }
  }

  /* ── 列印：只出驗收單 ─────────────────── */
  #print-acc { display:none; }
  @media print {
    body > .sidebar, body > .topbar, body > .main, dialog { display:none !important; }
    body { background:#fff; }
    #print-acc { display:block; font-size:12pt; color:#000; }
    #print-acc h1 { font-size:18pt; margin:0 0 4pt; }
    #print-acc .pmeta { font-size:9.5pt; color:#333; margin:0 0 14pt; }
    #print-acc h3 { font-size:12pt; margin:14pt 0 4pt; page-break-after:avoid; }
    #print-acc table { width:100%; border-collapse:collapse; }
    #print-acc th, #print-acc td { border:1px solid #999; padding:4pt 6pt; font-size:10pt;
                                   vertical-align:top; }
    #print-acc th { background:#eee; }
    #print-acc tr { page-break-inside:avoid; }
    #print-acc .pbox { width:16pt; text-align:center; font-size:11pt; }
    #print-acc .pst { white-space:nowrap; width:52pt; }
    #print-acc .pnote { width:70pt; }
    #print-acc .psign { margin-top:22pt; page-break-inside:avoid; }
    #print-acc .sign-row { display:flex; gap:40pt; margin-top:16pt; }
    #print-acc code { background:none; padding:0; font-size:9pt; }
    #print-acc .note { color:#555; font-size:9pt; }
  }
'''

# ---------- JS ----------

JS_TMPL = '''
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const BOOK_ORDER=__BOOK_ORDER__;
const SEARCH=__SEARCH_INDEX__;

/* ── 路由：#id 或 #id?query ── */
function ensureVisible(el){
  for(let d=el.closest('details'); d; d=d.parentElement?.closest('details')) d.open=true;
}
function flash(el){ el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash'); }
function go(hash){
  let [id,qs]=(hash||'').replace(/^#/,'').split('?');
  if(!id) return;
  try{ id=decodeURIComponent(id); qs=qs&&decodeURIComponent(qs); }catch(_){}
  if(qs) applyQuery(new URLSearchParams(qs));
  const el=document.getElementById(id);
  if(!el) return;
  ensureVisible(el);
  el.scrollIntoView({block:'start',behavior:'instant'});
  if(/^(acc|grp|book|arch)-/.test(id)) flash(el);
}
function applyQuery(q){
  const st=q.get('status'), mod=q.get('mod');
  if(st) setChip('fstate', st);
  if(mod) setChip('fmod', mod);
}
addEventListener('hashchange',()=>{ closePeek(false); go(location.hash); });
addEventListener('DOMContentLoaded',()=>{ if(location.hash) setTimeout(()=>go(location.hash),60); });

/* ── scrollspy：目錄高亮＋行動版章名（側欄與行動版目錄兩份都要亮） ── */
const spyItems={};
$$('.toc-item').forEach(it=>(spyItems[it.dataset.toc]??=[]).push(it));
/* 觀察「佔住視窗中帶」的 section／書本身（不是標題）——瞬移跳進章中段也會亮對 */
let curChapter='';
const BAND={rootMargin:'-40% 0px -55% 0px'};
function setChapter(ch){
  if(!ch||ch===curChapter) return;
  curChapter=ch;
  $$('.toc-item.current').forEach(x=>x.classList.remove('current'));
  (spyItems[ch]||[]).forEach(x=>x.classList.add('current'));
  const name=(spyItems[ch]||[])[0]?.querySelector('.toc-link span')?.textContent||'';
  const nowEl=$('#topbar-now'); if(nowEl) nowEl.textContent=name;
}
const chapterSpy=new IntersectionObserver(es=>{
  for(const e of es) if(e.isIntersecting) setChapter(e.target.id);
},BAND);
$$('.main > section[id]').forEach(s=>chapterSpy.observe(s));
function markSub(id){
  $$('.toc-sub.current').forEach(x=>x.classList.remove('current'));
  if(id) $$('.toc-sub[href="#'+CSS.escape(id)+'"]').forEach(l=>l.classList.add('current'));
}
const bookSpy=new IntersectionObserver(es=>{
  for(const e of es) if(e.isIntersecting) markSub('book-'+e.target.dataset.book);
},BAND);
$$('article.book').forEach(b=>bookSpy.observe(b));
const archSpy=new IntersectionObserver(es=>{
  for(const e of es) if(e.isIntersecting) markSub(e.target.id);
},{rootMargin:'-8% 0px -80% 0px'});
$$('#sec-架構 [data-spy], #sec-架構 details[id]').forEach(el=>archSpy.observe(el));

/* 附錄A sticky 疊放：量 accbar 實際高度，組頭跟著貼齊 */
const accbarEl=$('#accbar');
function setBarH(){ if(accbarEl) document.documentElement.style.setProperty('--accbar-h',accbarEl.offsetHeight+'px'); }
setBarH(); addEventListener('resize',setBarH);

/* ── 附錄A 篩選 ── */
const OPEN_STATES={open:['todo','written']};
let fstate='all', fmod='all';
function setChip(kind,val){
  window[kind==='fstate'?'fstate':'fmod'];
  if(kind==='fstate') fstate=val; else fmod=val;
  $$('.fchip[data-'+kind+']').forEach(c=>{
    const on=c.dataset[kind]===val;
    c.classList.toggle('active',on); c.setAttribute('aria-pressed',on);
  });
  filterAcc();
}
$$('.fchip').forEach(c=>c.addEventListener('click',()=>{
  if(c.dataset.fstate) setChip('fstate',c.dataset.fstate);
  else setChip('fmod',c.dataset.fmod);
}));
const asearch=$('#asearch'), aclear=$('#aclear');
asearch?.addEventListener('input',()=>{ aclear.hidden=!asearch.value; filterAcc(); });
aclear?.addEventListener('click',()=>{ asearch.value=''; aclear.hidden=true; filterAcc(); });
function filterAcc(){
  const q=(asearch?.value||'').trim().toLowerCase();
  let shown=0;
  $$('.agrp').forEach(g=>{
    let vis=0;
    $$('.arow',g).forEach(r=>{
      const okS=fstate==='all'||r.dataset.state===fstate||(OPEN_STATES[fstate]||[]).includes(r.dataset.state);
      const okM=fmod==='all'||r.dataset.mod===fmod;
      const okQ=!q||r.dataset.search.includes(q)||r.textContent.toLowerCase().includes(q);
      const ok=okS&&okM&&okQ;
      r.style.display=ok?'':'none'; if(ok) vis++;
    });
    g.style.display=vis?'':'none';
    if(vis&&(q||fstate!=='all'||fmod!=='all')) g.open=true;
    shown+=vis;
  });
  const total=$$('.arow').length;
  $('#acount').textContent='顯示 '+shown+'／'+total+' 條';
  $('#accempty')?.remove();
  if(!shown){
    const d=document.createElement('div'); d.id='accempty'; d.className='accempty';
    d.innerHTML='沒有符合條件的驗收條——<button type="button">清除篩選</button>';
    d.querySelector('button').onclick=resetAcc;
    $('#acclist').append(d);
  }
}
function resetAcc(){ if(asearch){asearch.value='';aclear.hidden=true;} setChip('fstate','all'); setChip('fmod','all'); }
filterAcc();

/* ── 驗收列展開 ── */
$$('.arow-head').forEach(btn=>btn.addEventListener('click',()=>{
  const more=btn.nextElementSibling, open=btn.getAttribute('aria-expanded')==='true';
  btn.setAttribute('aria-expanded',!open); more.hidden=open;
}));

/* ── 速覽抽屜 ── */
const peek=$('#peek'), peekBody=$('#peek-body'), peekTitle=$('#peek-title'),
      peekCrumb=$('#peek-crumb'), peekFull=$('#peek-full');
let peekName=null, crumbs=[];
function renderPeek(name, anchor){
  peekName=name;
  const src=document.getElementById('book-'+name);
  peekBody.innerHTML='';
  const clone=src.cloneNode(true);
  $$('[id]',clone).forEach(el=>el.id='pk-'+el.id);
  peekBody.append(clone);
  peekTitle.textContent=name;
  peekFull.href='#book-'+name;
  peekCrumb.classList.toggle('on',crumbs.length>0);
  if(crumbs.length) peekCrumb.textContent='← 回 '+crumbs[crumbs.length-1];
  peekBody.scrollTop=0;
  if(anchor){ const t=document.getElementById('pk-'+anchor);
    if(t){ t.scrollIntoView({block:'center'}); flash(t); } }
}
function openPeek(name, anchor){
  crumbs=[];
  renderPeek(name, anchor);
  if(!peek.open){ peek.show(); history.pushState({peek:1},''); }
}
function closePeek(viaHistory=true){
  if(!peek.open) return;
  peek.close(); peekBody.innerHTML=''; peekName=null; crumbs=[];
  if(viaHistory&&history.state&&history.state.peek) history.back();
}
addEventListener('popstate',()=>{ if(peek.open){ peek.close(); peekBody.innerHTML=''; peekName=null; crumbs=[]; }});
$('#peek-close').addEventListener('click',()=>closePeek());
function peekStep(d){
  const i=BOOK_ORDER.indexOf(peekName);
  const next=BOOK_ORDER[i+d];
  if(next){ crumbs=[]; renderPeek(next); }
}
$('#peek-prev').addEventListener('click',()=>peekStep(-1));
$('#peek-next').addEventListener('click',()=>peekStep(1));
peekCrumb.addEventListener('click',()=>{ const back=crumbs.pop(); if(back) renderPeek(back); });
peekBody.addEventListener('click',e=>{
  const a=e.target.closest('a[href^="#book-"],a[href^="#pk-"]');
  if(!a) return;
  const href=a.getAttribute('href');
  if(href.startsWith('#book-')){
    e.preventDefault();
    crumbs.push(peekName);
    renderPeek(decodeURIComponent(href.slice(6)));
  }
});
document.addEventListener('click',e=>{
  const p=e.target.closest('[data-peek]');
  if(p){ openPeek(p.dataset.peek, p.dataset.anchor); return; }
  if(peek.open && !e.target.closest('.peek') && !e.target.closest('[data-peek]')) closePeek();
});
addEventListener('keydown',e=>{
  if(e.key==='Escape'&&peek.open){ closePeek(); }
  if(peek.open&&e.key==='ArrowLeft') peekStep(-1);
  if(peek.open&&e.key==='ArrowRight') peekStep(1);
});

/* ── 圖 lightbox ── */
const lb=$('#lightbox'), lbBody=$('#lb-body');
$$('.diagram').forEach(d=>{
  const pan=$('.diagram-pan',d), svg=$('svg',pan);
  if(svg&&pan.scrollWidth<=pan.clientWidth+4) d.classList.add('fits');
  else d.classList.add('scrollable');
  d.addEventListener('click',()=>{
    lbBody.innerHTML=''; lbBody.append(svg.cloneNode(true)); lb.showModal();
  });
  d.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); d.click(); }});
});
$('#lb-close').addEventListener('click',()=>lb.close());
lb.addEventListener('click',e=>{ if(e.target===lb) lb.close(); });

/* ── 全域搜尋 ── */
function bindSearch(input, results){
  let sel=-1;
  function render(){
    const q=input.value.trim().toLowerCase();
    if(q.length<2){ results.hidden=true; results.innerHTML=''; return; }
    const hits=[];
    for(const it of SEARCH){
      const hay=(it.title+' '+it.text).toLowerCase();
      const pos=hay.indexOf(q);
      if(pos<0) continue;
      hits.push({it,pos});
      if(hits.length>=30) break;
    }
    hits.sort((a,b)=>(a.it.title.toLowerCase().includes(q)?0:1)-(b.it.title.toLowerCase().includes(q)?0:1));
    const top=hits.slice(0,8);
    results.innerHTML=top.length?top.map(({it})=>{
      const t=it.text, p=t.toLowerCase().indexOf(q);
      const s=p<0?'':t.slice(Math.max(0,p-16),p)+'<mark>'+t.substr(p,q.length)+'</mark>'+t.slice(p+q.length,p+q.length+24);
      return '<a href="#'+it.id+'"><span class="sr-src">'+it.src+'・'+it.title+'</span>'+s+'</a>';
    }).join(''):'<div class="sr-none">找不到「'+input.value+'」</div>';
    results.hidden=false; sel=-1;
  }
  input.addEventListener('input',render);
  input.addEventListener('keydown',e=>{
    const links=$$('a',results);
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){
      e.preventDefault(); sel=Math.max(0,Math.min(links.length-1,sel+(e.key==='ArrowDown'?1:-1)));
      links.forEach((l,i)=>l.classList.toggle('sel',i===sel)); links[sel]?.scrollIntoView({block:'nearest'});
    }
    if(e.key==='Enter'&&links.length){ (links[Math.max(sel,0)]).click(); }
    if(e.key==='Escape'){ results.hidden=true; input.blur(); }
  });
  results.addEventListener('click',()=>{ results.hidden=true; input.value='';
    $('#sheet')?.open&&$('#sheet').close(); });
  document.addEventListener('click',e=>{ if(!e.target.closest('.searchbox')) results.hidden=true; });
}
bindSearch($('#q-side'),$('#qr-side'));
const qm=$('#q-mobile'); if(qm) bindSearch(qm,$('#qr-mobile'));
addEventListener('keydown',e=>{
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){ e.preventDefault(); $('#q-side')?.focus(); }
  if(e.key==='/'&&!/INPUT|TEXTAREA/.test(document.activeElement.tagName)){
    e.preventDefault(); ($('#q-side')||qm)?.focus(); }
});

/* ── 行動版目錄 sheet ── */
const sheet=$('#sheet');
$('#topbar-menu')?.addEventListener('click',()=>sheet.showModal());
$('#sheet-close')?.addEventListener('click',()=>sheet.close());
sheet?.addEventListener('click',e=>{ if(e.target===sheet) sheet.close(); });
sheet?.addEventListener('click',e=>{ if(e.target.closest('a')) sheet.close(); });

/* ── 列印 ── */
$$('[data-print]').forEach(b=>b.addEventListener('click',()=>print()));
addEventListener('beforeprint',()=>{ resetAcc(); $$('.agrp').forEach(g=>g.open=true); });

/* ── 複製 chip ── */
$$('[data-copybtn]').forEach(b=>b.addEventListener('click',()=>{
  const code=b.previousElementSibling?.textContent||'';
  navigator.clipboard?.writeText(code).then(()=>{ b.textContent='已複製'; setTimeout(()=>b.textContent='複製',1600); });
}));
'''


# ---------- 組頁 ----------

def build_page():
    a = ROLLUP['all']
    ran = f'測試結果跑於 {RAN_AT}' if RAN_AT else '自動測試還沒跑過'
    stale_badge = ('<p class="badge-stale">⚠ 正本 md 比測試結果新——數字可能過期，'
                   '重跑 <code>python3 intents/run-驗收.py</code></p>') if STALE else ''

    intent_body = (f'<div class="docmeta">{md_to_html(preamble(intent_md))}</div>'
                   f'{md_to_html(re.sub(re.escape(preamble(intent_md)), "", intent_md, count=1))}'
                   ) if intent_md else '<p class="empty">這一站還沒走到——檔案出生後重跑 gen 就會長出來。</p>'

    books_html = ''.join(book_chapter(bn, i) for i, bn in enumerate(BOOKS, 1)) \
        or '<p class="empty">還沒有規格書——第一本出生後重跑 gen 就會長出來。</p>'

    sidebar = (
        f'<aside class="sidebar">'
        f'<div class="cover-head"><p class="eyebrow">Intent-driven Design</p>'
        f'<h1 class="cover-title">報價單系統</h1>'
        f'<p class="cover-sub">設計書・活文件</p></div>'
        f'{searchbox_html("side")}'
        f'{toc_html()}'
        f'<div class="cover-foot">'
        f'<button type="button" class="printbtn" data-print>列印驗收單</button>'
        f'<p class="cover-note">本頁由 intents/*.md 自動產生——要改內容請改 md 正本。{html.escape(ran)}。</p>'
        f'</div></aside>')

    topbar = (f'<div class="topbar"><button type="button" class="topbar-menu" id="topbar-menu">'
              f'☰ 目錄</button><span class="topbar-now" id="topbar-now">卷首・現況</span></div>')

    sec_front = (
        f'<section class="chapter" id="sec-卷首">'
        f'<header class="ch-head"><div><span class="eyebrow">卷首</span>'
        f'<h2>現況</h2></div></header>'
        f'{stale_badge}'
        f'{gates_html()}'
        f'<h3 data-spy>下一步</h3>'
        f'{todos_html()}'
        f'<h3 data-spy>規格書一覽</h3>'
        f'{ledger_html("front")}'
        f'</section>')

    sec_intent = (
        f'<section class="chapter" id="sec-意圖">'
        f'<header class="ch-head"><span class="chno">01</span><div>'
        f'<span class="eyebrow">第一章</span><h2>意圖——要做什麼、為誰做</h2></div></header>'
        f'<div class="prose">{intent_body}</div></section>')

    sec_arch = (
        f'<section class="chapter" id="sec-架構">'
        f'<header class="ch-head"><span class="chno">02</span><div>'
        f'<span class="eyebrow">第二章</span><h2>架構——整個系統一頁看完</h2></div></header>'
        f'<div class="prose">{arch_chapter_body()}</div></section>')

    sec_books = (
        f'<section class="chapter" id="sec-規格書">'
        f'<header class="ch-head"><span class="chno">03</span><div>'
        f'<span class="eyebrow">第三章</span><h2>規格書——一本書講一個動作</h2></div></header>'
        f'{ledger_html("ch3")}'
        f'{nonbook_html()}'
        f'{books_html}</section>')

    sec_acc = (
        f'<section class="chapter" id="sec-驗收">'
        f'<header class="ch-head"><span class="chno">A</span><div>'
        f'<span class="eyebrow">附錄</span><h2>驗收清單——{full_count_sentence()}</h2></div></header>'
        f'{acc_chips()}'
        f'<div id="acclist">{acc_principles_group()}'
        f'{"".join(acc_group(bn) for bn in BOOKS)}</div>'
        f'{signoff_html()}</section>')

    gen_cmds = ('<p>重新產頁：<code>python3 intents/gen-系統總覽.py</code>；'
                '跑驗收：<code>python3 intents/run-驗收.py</code>。</p>')
    sec_colophon = (
        f'<section class="chapter colophon" id="sec-版權">'
        f'<header class="ch-head"><div><span class="eyebrow">版權頁</span>'
        f'<h2>這一頁怎麼來的</h2></div></header>'
        f'<p>這整本設計書由 <code>intents/</code> 的 markdown 正本自動派生——進度、統計、'
        f'驗收狀態全部是算出來的，頁面自己不存任何狀態。要改內容，改 md 正本再重跑一次產生器；'
        f'直接改這頁的 HTML 沒有意義，下一次生成就會被蓋掉。</p>'
        f'<p>{html.escape(ran)}；手動驗收記在規格書正本該條行尾，頁面只是投影。</p>'
        f'{gen_cmds}'
        f'<p>Lean Stack・System Design Review</p></section>')

    peek_dlg = (
        f'<dialog class="peek" id="peek" aria-labelledby="peek-title">'
        f'<div class="peek-head">'
        f'<button type="button" class="peek-crumb" id="peek-crumb"></button>'
        f'<b class="peek-title" id="peek-title"></b>'
        f'<a class="peek-open-full" id="peek-full" href="#">在第三章開啟 →</a>'
        f'<span class="peek-nav"><button type="button" id="peek-prev" aria-label="上一本">‹</button>'
        f'<button type="button" id="peek-next" aria-label="下一本">›</button></span>'
        f'<button type="button" class="peek-close" id="peek-close" aria-label="關閉">✕</button></div>'
        f'<div class="peek-body" id="peek-body"></div>'
        f'<p class="peek-hint">速覽＝快查用；←→ 換一本，Esc 關閉。要細讀請「在第三章開啟」。</p>'
        f'</dialog>')

    lightbox = (f'<dialog class="lightbox" id="lightbox"><div class="lb-head">'
                f'<button type="button" class="peek-close" id="lb-close" aria-label="關閉">✕</button></div>'
                f'<div class="lb-body" id="lb-body"></div></dialog>')

    sheet = (f'<dialog class="sheet" id="sheet"><div class="sheet-head"><b>報價單系統・設計書</b>'
             f'<button type="button" class="sheet-close" id="sheet-close">關閉</button></div>'
             f'{searchbox_html("mobile")}'
             f'{toc_html(sheet=True)}'
             f'<button type="button" class="printbtn" data-print>列印驗收單</button></dialog>')

    idx_json = json.dumps(search_index(), ensure_ascii=False).replace('</', '<\\/')
    order_json = json.dumps(list(BOOKS), ensure_ascii=False)
    js = JS_TMPL.replace('__BOOK_ORDER__', order_json).replace('__SEARCH_INDEX__', idx_json)

    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>報價單系統・設計書</title>
<style>{CSS}</style></head><body>
{sidebar}
{topbar}
<main class="main">
{sec_front}
{sec_intent}
{sec_arch}
{sec_books}
{sec_acc}
{sec_colophon}
</main>
{print_dom()}
{peek_dlg}
{lightbox}
{sheet}
<script>{js}</script>
</body></html>"""


page = build_page()
(HERE / '系統總覽.html').write_text(page, encoding='utf-8')
a = ROLLUP['all']
ran_note = f'測試結果跑於 {RAN_AT}' if RAN_AT else '測試結果未跑（run-驗收.py）'
print(f'✅ 系統總覽.html（{len(page)//1024}KB）｜模組 {len(modules)}・規格書 {len(BOOKS)}・'
      f'驗收條 {a["total"]}（已驗 {a["verified"]}）｜{ran_note}'
      + ('｜⚠ 正本比測試結果新' if STALE else ''))
