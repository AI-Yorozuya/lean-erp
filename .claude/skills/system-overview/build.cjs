#!/usr/bin/env node
// 系統總覽產生器：讀 系統總覽.json，出 系統總覽.html（一頁式、自足、不載函式庫）。
// 用法：node build.cjs <json 檔或專案資料夾> [輸出 html]
//   node build.cjs 專案/                → 專案/系統總覽.html
//   node build.cjs 範例.json 範例.html
// 正本是 json：AI 改 json、重跑；人看 html，html 不手改。
// 版面 token 照 lean-admin（shadcn neutral、Inter、圓角 6px、卡片 border＋shadow-sm、頁標題 18px semibold），
// 課程語意色只留三種標記（近黑／灰／橘）和泳道的人藍、系統綠、第二個人橘。
'use strict';
const fs = require('fs'), path = require('path');

const arg = process.argv[2];
if (!arg) { console.error('用法：node build.cjs <系統總覽.json 或專案資料夾> [輸出.html]'); process.exit(1); }
let src = arg;
if (fs.existsSync(arg) && fs.statSync(arg).isDirectory()) src = path.join(arg, '系統總覽.json');
const out = process.argv[3] || (fs.statSync(arg).isDirectory() ? path.join(arg, '系統總覽.html') : src.replace(/\.json$/, '.html'));
const J = JSON.parse(fs.readFileSync(src, 'utf8'));
J.principles = (J.principles || []).map((p, i) => ({ id: p.id || `rule_${p.module}_${i + 1}`, ...p }));
J.specs = J.specs || [];
J.tests = J.tests || [];
for (const S of J.specs) if (S.accept && !J.tests.some(t => t.spec === S.id)) {
  if (S.accept.ok) J.tests.push({ id: `${S.id}_ok`, spec: S.id, kind: 'ok', text: S.accept.ok, guards: [] });
  if (S.accept.no) J.tests.push({ id: `${S.id}_no`, spec: S.id, kind: 'no', text: S.accept.no, guards: [] });
}

// 狀態只寫一處：帶 state 的選項欄位（或 id 叫 status 的）就是狀態；流程的 from／to 寫選項 id
for (const d of J.data || []) {
  const fs = (d.fields || []).filter(f => f && typeof f === 'object');
  const sf = fs.find(f => f.state) || fs.find(f => f.id === 'status' && f.options);
  d.states = sf && sf.options ? sf.options.map(o => typeof o === 'object' ? o : { text: o, id: o }) : [];
}

// ── 一個東西一個名字：資料、頁、步驟、規格的 id 全站不重名，重了不出頁 ──
(function checkNames() {
  const seen = new Map(), dup = [];
  (J.flows || []).forEach(f => { const d = (J.data || []).find(x => x.id === f.data); f.steps.forEach(st => ['from', 'to'].forEach(k => { if (st[k] && !(d && d.states.some(o => o.id === st[k]))) dup.push(`流程 ${f.data} 的步驟 ${st.id} 寫的狀態 ${st[k]} 不在 ${f.data} 的狀態選項裡`); })); });
  const add = (id, what) => { if (!id) return; if (seen.has(id)) dup.push(`${id}（${seen.get(id)} 與 ${what}）`); else seen.set(id, what); };
  (J.roles || []).forEach(r => add(r.id, '角色 ' + r.name));
  (J.modules || []).forEach(m => add(m.id, '模組 ' + m.name));
  (J.data || []).forEach(d => add(d.id, '資料 ' + d.name));
  (J.pages || []).forEach(p => add(p.id, '頁 ' + p.name));
  (J.flows || []).forEach(f => f.steps.forEach(st => add(st.id, '步驟 ' + st.label)));
  (J.specs || []).forEach(sp => add(sp.id, '規格 ' + sp.title));
  (J.principles || []).forEach(p => add(p.id, '原則 ' + p.text));
  (J.tests || []).forEach(t => add(t.id, '驗收 ' + t.text));
  (J.data || []).forEach(d => { const seen2 = new Set(); (d.fields || []).forEach(f => { if (f && typeof f === 'object' && f.id) { if (seen2.has(f.id)) dup.push(`${d.id}.${f.id}（${d.name} 的欄位重複）`); seen2.add(f.id); } }); });
  (J.data || []).forEach(d => (d.fields || []).forEach(f => { if (f && typeof f === 'object' && f.ref && !(J.data || []).some(x => x.id === f.ref)) dup.push(`${d.id}.${f.id || f.text} 引用的 ${f.ref} 不存在`); }));
  (J.specs || []).forEach(S => {
    if (Array.isArray(S.fields)) S.fields.forEach(x => { const [di, fi] = String(x.ref).split('.'); const d = (J.data || []).find(y => y.id === di); if (!d || !d.fields.some(f => f && typeof f === 'object' && f.id === fi)) dup.push(`規格 ${S.id} 寫到的欄位 ${x.ref} 在資料頁找不到`); });
    (S.calc_rules || []).forEach(r => { if (!(J.principles || []).some((p, i) => (p.id || `rule_${p.module}_${i + 1}`) === r)) dup.push(`規格 ${S.id} 依據的原則 ${r} 不存在`); });
  });
  if (dup.length) { console.error('資料檔有問題，不出頁：\n  ' + dup.join('\n  ')); process.exit(1); }
})();

// ── 小工具 ──────────────────────────────────────────────
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const cell = v => typeof v === 'object' && v !== null ? v : { text: v, mark: 'src' };
const tagHtml = (c, cls) => c.tag ? `<span class="tag">${esc(c.tag)}</span>` : '';
const li = (c, extra = '') => { c = cell(c); return `<li class="${c.mark || 'src'}${extra}">${esc(c.text)}${tagHtml(c)}</li>`; };
const cjkW = (s, px) => { let w = 0; for (const ch of String(s)) w += /[⺀-﫿＀-￯]/.test(ch) ? px : px * 0.58; return w; };
const byId = (arr, id) => arr.find(x => x.id === id);

const LANE = { system: { name: '系統', c: '#059669', bg: '#ecfdf5' } };
const roleColor = i => ['#2563eb', '#c2410c', '#7c3aed', '#0d9488', '#db2777', '#b45309', '#4f46e5', '#65a30d', '#475569'][i % 9];
const roleBg = i => ['#eff6ff', '#fff7ed', '#f5f3ff', '#f0fdfa', '#fdf2f8', '#fffbeb', '#eef2ff', '#f7fee7', '#f8fafc'][i % 9];
J.roles.forEach((r, i) => { LANE[r.id] = { name: r.name, c: roleColor(i), bg: roleBg(i) }; });

const dataOf = m => J.data.filter(d => d.module === m.id);
const pagesOf = m => J.pages.filter(p => dataOf(m).some(d => d.id === p.data));
const KIND = { list: '列表頁', detail: '詳細頁', widget: '互動元件', report: '報表頁' };
const pageById = id => byId(J.pages, id);
const prinOf = m => J.principles.filter(p => p.module === m.id);
const flowsOf = m => (J.flows || []).filter(f => dataOf(m).some(d => d.id === f.data));
const specsOf = m => flowsOf(m).flatMap(f => f.steps.filter(s => s.spec).map(s => byId(J.specs, s.spec))).filter(Boolean);
const pageCount = m => pagesOf(m).filter(p => p.kind !== 'widget').length;
const moduleOfData = id => J.modules.find(m => dataOf(m).some(d => d.id === id));

// ── 2. 流程層：泳道圖（只有帶狀態的資料才畫） ──
let MK = 0;
function swimlane(f) {
  const mk = 'la' + (++MK);
  // 直的泳道：角色是欄，步驟往下走（流程長就往下長）
  const lanes = f.lanes, LW = 300, LG = 6, Y0 = 16, RH = 96, BW = 200, BH = 46;
  const laneX = id => lanes.indexOf(id) * (LW + LG);
  const steps = f.steps.map(s => ({ ...s }));
  const S = id => steps.find(s => s.id === id);
  steps.forEach((s, i) => { const prev = s.after ? S(s.after) : steps[i - 1]; s.prev = prev; s.row = s.row != null ? s.row : (prev ? prev.row + 1 : 0); });
  const nrow = Math.max(...steps.map(s => s.row)) + 1;
  const VH = 40 + Y0 + nrow * RH;
  steps.forEach(s => { s.x = laneX(s.lane) + (LW - BW) / 2; s.y = 40 + Y0 + s.row * RH; s.cx = s.x + BW / 2; s.cy = s.y + BH / 2; });
  const states = byId(J.data, f.data).states || [];
  const stTxt = s => { const o = states.find(o => o.id === s.to); return o ? o.text : s.to; };
  const VW = Math.max(lanes.length * (LW + LG) - LG, ...steps.filter(s => s.to).map(s => s.cx + 8 + cjkW(stTxt(s), 11) + 20 + 8));
  let g = `<svg viewBox="0 0 ${VW} ${VH}" width="${VW}" role="img" aria-label="泳道圖：${esc(byId(J.data, f.data).name)}">
<defs><marker id="${mk}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#64748b"/></marker></defs>\n`;
  lanes.forEach(id => { const L = LANE[id]; g += `<rect x="${laneX(id)}" y="0" width="${LW}" height="${VH}" fill="${L.bg}" rx="6"/><text x="${laneX(id) + LW / 2}" y="26" text-anchor="middle" font-size="14" font-weight="700" fill="${L.c}">${esc(L.name)}</text>\n`; });
  g += `<g font-size="13" font-weight="600" fill="#0f172a">`;
  for (const s of steps) {
    const L = LANE[s.lane];
    if (s.spec) g += `<g class="specbox" data-spec="${s.spec}" style="cursor:pointer">`;
    g += `<rect x="${s.x}" y="${s.y}" width="${BW}" height="${BH}" rx="6" fill="#fff" stroke="${L.c}" stroke-width="1.5"${s.dashed ? ' stroke-dasharray="4 3"' : ''}/>`;
    if (s.spec) g += `<circle cx="${s.x + BW - 10}" cy="${s.y + BH - 10}" r="4" fill="${L.c}"/>`;
    if (s.page) { const pg = pageById(s.page); g += `<text x="${s.cx}" y="${s.y + 20}" text-anchor="middle">${esc(s.label)}</text><text x="${s.cx}" y="${s.y + 36}" text-anchor="middle" font-size="10" font-weight="400" fill="#64748b">${esc(pg ? pg.name : s.page)}</text>`; }
    else g += `<text x="${s.cx}" y="${s.cy + 5}" text-anchor="middle">${esc(s.label)}</text>`;
    if (s.spec) g += `</g>`;
  }
  g += `</g>\n<g fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#${mk})">`;
  for (const s of steps) {
    const p = s.prev; if (!p) continue;
    if (p.lane === s.lane) g += `<path d="M${p.cx} ${p.y + BH} L${s.cx} ${s.y - 2}"/>`;
    else { const right = s.cx > p.cx; g += `<path d="M${right ? p.x + BW : p.x} ${p.cy} L${s.cx} ${p.cy} L${s.cx} ${s.y - 2}"/>`; }
  }
  g += `</g>\n<g font-size="11" fill="#0f172a">`;
  for (const s of steps) {
    if (!s.to) continue;
    const txt = stTxt(s);
    // 按下這顆之後才進這個狀態：標籤壓在它下面那段線的正中間
    const nx = steps.find(t => t.prev === s && t.lane === s.lane);
    const w = cjkW(txt, 11) + 20, x = s.cx - w / 2, y = (nx ? (s.y + BH + nx.y) / 2 : s.y + BH + (RH - BH) / 2) - 9;
    if (!nx) g += `<path d="M${s.cx} ${s.y + BH} L${s.cx} ${y}" stroke="#64748b" stroke-width="1.5" fill="none"/>`;
    g += `<rect x="${x}" y="${y}" width="${w}" height="18" rx="9" fill="#fff" stroke="${s.lock ? '#c2410c' : '#e2e8f0'}"/><text x="${x + w / 2}" y="${y + 13}" text-anchor="middle"${s.lock ? ' fill="#c2410c"' : ''}>${esc(txt)}</text>`;
  }
  g += `</g></svg>`;
  return { svg: g, steps };
}

function flowBlock(f) {
  const { svg, steps } = swimlane(f);
  const dn = byId(J.data, f.data);
  let h = `<h4 class="ftitle">${esc(dn.name)}<code>${esc(dn.id)}</code></h4><div class="lane">${svg}</div>`;
  const sp = steps.filter(s => s.spec);
  if (sp.length) {

  }
  return h;
}
// ── 資料關係圖：一張圖畫完所有資料。方塊＝資料（名字加欄位），線＝誰引用誰，線旁一句白話 ──
function dataMap(m) {
  const mk = 'dh' + (++MK);
  // 一模組一張圖。方塊＝資料；線＝誰引用誰（直角走、線在方塊底下）。
  // 小圖（≤6 種資料、每個方塊進線 ≤2）線旁直接寫白話；大圖改成線上編號，白話列在圖底下。
  const own = dataOf(m);
  const ext = [];
  for (const d of own) for (const r of (d.refs || [])) { const t = byId(J.data, r.to); if (t && !own.includes(t) && !ext.includes(t)) ext.push(t); }
  const DATA = [...own, ...ext.map(t => ({ id: t.id, name: t.name, fields: [], refs: [], ghost: true, module: t.module }))];
  const has = id => DATA.some(d => d.id === id);
  const edges = [];
  for (const d of own) for (const r of (d.refs || [])) if (has(r.to) && r.to !== d.id) edges.push({ from: d.id, to: r.to, text: r.text, part: !!r.part });
  const selfRefs = own.flatMap(d => (d.refs || []).filter(r => r.to === d.id).map(r => ({ d, r })));
  const parentOf = {}; for (const e of edges) if (e.part && !parentOf[e.from]) parentOf[e.from] = e.to;
  // 深度：沒引用別人的排左；遇到循環就停（visiting）
  const depth = {}, visiting = new Set();
  const dep = id => {
    if (depth[id] != null) return depth[id];
    if (visiting.has(id)) return 0;
    visiting.add(id);
    const outs = edges.filter(e => e.from === id && !e.part);
    let d = outs.length ? 1 + Math.max(...outs.map(e => dep(e.to))) : 0;
    if (parentOf[id]) d = Math.max(d, dep(parentOf[id]));
    visiting.delete(id); depth[id] = d; return d;
  };
  DATA.forEach(d => dep(d.id));
  const cols = {}, placed = new Set();
  const place = d => { if (placed.has(d.id)) return; placed.add(d.id); (cols[depth[d.id]] = cols[depth[d.id]] || []).push(d); DATA.filter(x => parentOf[x.id] === d.id).forEach(place); };
  DATA.filter(d => !parentOf[d.id]).forEach(place); DATA.forEach(place);
  const inCount = {}; edges.forEach(e => { inCount[e.to] = (inCount[e.to] || 0) + 1; });
  const numbered = own.length > 6 || Object.values(inCount).some(n => n > 2);
  const W = 240, LH = 20, PAD = 12, HEAD = 34, ROWGAP = numbered ? 40 : 56, TOP = 16;
  const GAP = numbered ? 400 : 560;
  const hOf = d => d.ghost ? HEAD : HEAD + PAD + Math.max(d.fields.length, 1) * LH;
  const box = {}, colH = {};
  const maxDepth = Math.max(...Object.keys(cols).map(Number));
  for (const [k, list] of Object.entries(cols)) colH[k] = list.reduce((n, d) => n + hOf(d), 0) + (list.length - 1) * ROWGAP;
  const totalH = Math.max(...Object.values(colH));
  for (const [k, list] of Object.entries(cols)) {
    let y = TOP + (numbered ? 0 : (totalH - colH[k]) / 2);
    for (const d of list) { box[d.id] = { x: 60 + (maxDepth - (maxDepth - k)) * GAP, y, w: W, h: hOf(d) }; y += hOf(d) + ROWGAP; }
  }
  const VW = 60 + maxDepth * GAP + W + (numbered ? 60 : 420), VH = TOP + totalH + 16;
  let lines = '', labels = '', boxes = '';
  const list = [];
  // 出線：從來源左緣均分出發；進線：在目標右緣均分落點
  const outs = {}, ins = {};
  edges.filter(e => !e.part || box[e.to].x !== box[e.from].x).forEach(e => { (outs[e.from] = outs[e.from] || []).push(e); (ins[e.to] = ins[e.to] || []).push(e); });
  for (const arr of Object.values(ins)) arr.sort((p, q) => box[p.from].y - box[q.from].y);
  const label = (x, y, text, anchor) => { const tw = cjkW(text, 11) + 16; const lx = anchor === 'end' ? x - tw : x; return `<rect x="${lx}" y="${y - 10}" width="${tw}" height="20" rx="4" fill="#fff" stroke="#e2e8f0"/><text x="${lx + tw / 2}" y="${y + 4}" text-anchor="middle" font-size="11" fill="#0f172a">${esc(text)}</text>\n`; };
  const badge = (x, y, n) => `<circle cx="${x}" cy="${y}" r="9" fill="#fff" stroke="#64748b"/><text x="${x}" y="${y + 4}" text-anchor="middle" font-size="10" font-weight="700" fill="#0f172a">${n}</text>`;
  for (const [from, arr] of Object.entries(outs)) {
    const a = box[from];
    arr.sort((p, q) => box[p.to].y - box[q.to].y).forEach((e, i) => {
      const b = box[e.to], k = ins[e.to].indexOf(e), nIn = ins[e.to].length;
      const y1 = a.y + a.h * (i + 1) / (arr.length + 1);
      const y2 = b.y + (numbered ? Math.min(b.h - 8, 14 + k * 22) : b.h * (k + 1) / (nIn + 1));
      const x2 = b.x + b.w + 2, jx = a.x - 24 - i * 8;
      lines += `<path d="M${a.x} ${y1} L${jx} ${y1} L${jx} ${y2} L${x2} ${y2}" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#${mk})"/>`;
      if (numbered) { list.push(e); labels += badge(x2 + 20, y2, list.length); }
      else labels += label(x2 + 12, y2 - 16, e.text, 'start');
    });
  }
  // 從屬：子資料在母資料正下方，線走左邊空白，不穿過兄弟方塊
  const kids = {};
  edges.filter(e => e.part && box[e.to].x === box[e.from].x).forEach(e => (kids[e.to] = kids[e.to] || []).push(e));
  for (const [pid, arr] of Object.entries(kids)) {
    const pb = box[pid];
    arr.forEach((e, i) => {
      const cb = box[e.from], x = pb.x - 12 - i * 6, yc = cb.y + 17, yp = pb.y + pb.h - 10 - i * 6;
      lines += `<path d="M${cb.x} ${yc} L${x} ${yc} L${x} ${yp} L${pb.x - 2} ${yp}" fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#${mk})"/>`;
      if (numbered) { list.push(e); labels += badge(x, (yc + yp) / 2, list.length); }
      else labels += label(pb.x + 16, (pb.y + pb.h + cb.y) / 2, e.text, 'start');
    });
  }
  for (const d of DATA) {
    const b = box[d.id];
    if (d.ghost) { const mm = byId(J.modules, d.module); boxes += `<g><rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="6" fill="#fff" stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="5 4"/><text x="${b.x + 12}" y="${b.y + 22}" font-size="14" font-weight="700" fill="#64748b">${esc(d.name)}</text><text x="${b.x + b.w - 12}" y="${b.y + 22}" text-anchor="end" font-size="11" fill="#94a3b8">${esc(mm ? mm.name : '')}</text></g>\n`; continue; }
    boxes += `<g id="dm-${d.id}"><rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="6" fill="#f8fafc" stroke="#059669" stroke-width="1.5"/>`;
    boxes += `<text x="${b.x + 12}" y="${b.y + 22}" font-size="14" font-weight="700" fill="#059669">${esc(d.name)}</text><text x="${b.x + b.w - 12}" y="${b.y + 22}" text-anchor="end" font-size="11" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" fill="#64748b">${esc(d.id)}</text>`;
    boxes += `<line x1="${b.x}" y1="${b.y + HEAD}" x2="${b.x + b.w}" y2="${b.y + HEAD}" stroke="#e2e8f0"/>`;
    d.fields.forEach((f, i) => { const c = cell(f); const col = c.mark === 'ai' ? '#8a94a6' : c.mark === 'dec' ? '#c2410c' : '#0f172a'; boxes += `<text x="${b.x + 12}" y="${b.y + HEAD + PAD + i * LH + 2}" font-size="12" fill="${col}">${esc(c.text)}</text>`; });
    boxes += `</g>\n`;
  }
  const svg = `<svg viewBox="0 0 ${VW} ${VH}" width="${VW}" height="${VH}" role="img" aria-label="資料關係圖"><defs><marker id="${mk}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10z" fill="#64748b"/></marker></defs>\n${lines}\n${boxes}\n${labels}</svg>`;
  const legend = list.length ? `<ol class="rels">${list.map(e => `<li><b>${esc(byId(J.data, e.from).name)} → ${esc(byId(J.data, e.to).name)}</b>：${esc(e.text)}</li>`).join('')}</ol>` : '';
  const selfs = selfRefs.length ? `<ul class="note" style="padding-left:18px">${selfRefs.map(({ d, r }) => `<li>${esc(d.name)} → ${esc(d.name)}：${esc(r.text)}</li>`).join('')}</ul>` : '';
  return svg + legend + selfs;
}

const sub = (m, k) => `<h3 id="${k}-${m.id}">${esc(m.name)}</h3>`;
const tdc = c => { c = cell(c); return `<td class="${c.mark || 'src'}">${esc(c.text)}${c.tag ? `<span class="tag">${esc(c.tag)}</span>` : ''}</td>`; };

// ── 資料頁：先一張表條列所有資料，再一模組一張卡畫關係 ──
const optText = o => typeof o === 'object' ? o.text : o;
const fieldRows = d => d.fields.map(f => { const c = cell(f); const st = c.options || null; return { c, st, n: st && st.length ? st.length : 1 }; });
const TYPES = ['文字', '數字', '金額', '日期', '選項', '是否', '引用'];
const typeCell = c => c.type ? esc(c.type) : '<span class="none">—</span>';
const optCell = (r, k) => {
  if (r.st) return esc(optText(r.st[k]));
  if (r.c.ref) { const t = byId(J.data, r.c.ref); return `<a class="lnk" href="#/data/d-row-${esc(r.c.ref)}">${esc(t ? t.name : r.c.ref)}</a>`; }
  return '';
};
const DBT = { '文字': 'string', '數字': 'int', '金額': 'decimal', '日期': 'date', '是否': 'bool', '選項': 'enum', '引用': 'fk' };
const dbType = r => {
  const c = r.c; if (c.dbtype) return esc(c.dbtype);
  const t = DBT[c.type]; if (!t) return '';
  if (t === 'enum' && r.st) return `enum(${r.st.map(o => typeof o === 'object' && o.id ? esc(o.id) : '?').join(', ')})`;
  if (t === 'fk' && c.ref) return `fk → ${esc(c.ref)}`;
  return t;
};
const noteCell = c => [c.calc ? '系統算出' : '', c.mark && c.mark !== 'src' && c.tag ? c.tag : ''].filter(Boolean).map(x => `<small>${esc(x)}</small>`).join('<br>');
const dataTable = `<div class="card tbl"><table>
<tr><th class="mcol">模組</th><th>資料</th><th>欄位</th><th>型別</th><th class="c">必填</th><th class="c">唯一</th><th>選項</th><th>備註</th><th>程式名</th><th>程式型別</th></tr>
${(() => { const cnt = {}; J.data.forEach(d => { const id = moduleOfData(d.id).id; cnt[id] = (cnt[id] || 0) + fieldRows(d).reduce((n, r) => n + r.n, 0); }); const seen = new Set(); return J.data.map(d => { const m = moduleOfData(d.id); const firstM = !seen.has(m.id); seen.add(m.id); const FR = fieldRows(d); const dn = FR.reduce((n, r) => n + r.n, 0); let out = [], first = true;
  for (const r of FR) for (let k = 0; k < r.n; k++) {
    let row = `<tr${first ? ` id="d-row-${d.id}"` : ''}${k === 0 && r.c.id ? ` data-anchor="f-${d.id}.${r.c.id}"` : ''} data-m="${m.id}">`;
    if (first && firstM) row += `<td rowspan="${cnt[m.id]}" class="grp">${esc(m.name)}</td>`;
    if (first) row += `<td rowspan="${dn}" class="key ${d.mark || 'src'}"${d.mark && d.mark !== 'src' && d.tag ? ` title="${esc(d.tag)}"` : ''}>${esc(d.name)}</td>`;
    const mk = r.c.mark || 'src';
    if (k === 0) row += `<td rowspan="${r.n}" class="${mk}">${esc(r.c.text)}</td><td rowspan="${r.n}" class="nowrap">${typeCell(r.c)}</td><td rowspan="${r.n}" class="c">${r.c.required ? '✓' : ''}</td><td rowspan="${r.n}" class="c">${r.c.unique ? '✓' : ''}</td>`;
    row += `<td>${optCell(r, k)}</td>`;
    if (k === 0) row += `<td rowspan="${r.n}" class="${mk}">${noteCell(r.c)}</td><td rowspan="${r.n}" class="code">${esc(d.id)}${r.c.id ? '.' + esc(r.c.id) : ''}</td><td rowspan="${r.n}" class="code">${dbType(r)}</td>`;
    out.push(row + '</tr>'); first = false;
  }
  return out.join('\n'); }).join('\n'); })()}
<tr class="emptyrow" hidden><td colspan="99">沒有資料</td></tr>
</table></div>`;
const dataView = `<section class="view fill" data-view="data" data-title="資料" data-sub="">
${dataTable}
</section>`;

// ── 關係頁：一個模組一張資料關係圖（這個模組的資料＋它引用到的別模組資料）。
//    線各走各的軌道：出口、入口高度錯開；欄與欄之間每條線一條直軌；跨欄的線走圖上方的通道。線會交叉，不會重疊。
function relMapModule(m) {
  const own = dataOf(m);
  if (!own.length) return '';
  const ghosts = [];
  for (const d of own) for (const r of (d.refs || [])) { const t = byId(J.data, r.to); if (t && !own.includes(t) && !ghosts.includes(t)) ghosts.push(t); }
  const N = {}; own.forEach(d => N[d.id] = { d, ghost: false }); ghosts.forEach(d => N[d.id] = { d, ghost: true });
  const edges = [];
  for (const d of own) for (const r of (d.refs || [])) if (N[r.to] && r.to !== d.id) edges.push({ from: d.id, to: r.to, text: r.text, part: !!r.part && !N[r.to].ghost });
  const small = edges.length <= 8;
  const W = 220, LH = 18, HEAD = 32, PAD = 10;
  const hOf = id => N[id].ghost ? HEAD + 8 : HEAD + PAD + Math.max(N[id].d.fields.length, 1) * LH;
  // 欄：別模組的在最左；自己的照引用深度往右；從屬的跟母資料同欄
  const parentOf = {}; edges.forEach(e => { if (e.part && !parentOf[e.from]) parentOf[e.from] = e.to; });
  const dep = {}, vis = new Set();
  const depth = id => {
    if (dep[id] != null) return dep[id];
    if (N[id].ghost) return (dep[id] = 0);
    if (vis.has(id)) return 1;
    vis.add(id);
    const outs = edges.filter(e => e.from === id && !e.part);
    let v = outs.length ? 1 + Math.max(...outs.map(e => depth(e.to))) : (ghosts.length ? 1 : 0);
    if (parentOf[id]) v = Math.max(v, depth(parentOf[id]));
    vis.delete(id); return (dep[id] = v);
  };
  Object.keys(N).forEach(depth);
  Object.keys(parentOf).forEach(id => { dep[id] = dep[parentOf[id]]; });
  const ncol = Math.max(...Object.values(dep)) + 1;
  const cols = Array.from({ length: ncol }, () => []);
  // 每欄排序：照它引用的對象在左欄的位置平均（重心法），子資料緊跟母資料
  const order = {};
  for (let c = 0; c < ncol; c++) {
    const ids = Object.keys(N).filter(id => dep[id] === c && !(parentOf[id] && dep[parentOf[id]] === c));
    const bc = id => { const t = edges.filter(e => e.from === id && order[e.to] != null).map(e => order[e.to]); return t.length ? t.reduce((x, y) => x + y, 0) / t.length : 1e6 + ids.indexOf(id); };
    ids.sort((x, y) => bc(x) - bc(y));
    const out = [];
    const push = id => { out.push(id); Object.keys(parentOf).filter(k => parentOf[k] === id && dep[k] === c).forEach(push); };
    ids.forEach(push);
    out.forEach((id, i) => order[id] = i + c * 1000);
    cols[c] = out;
  }
  const col = id => dep[id];
  // 路線種類與每個縫的軌道數（縫 g 在第 g-1 欄與第 g 欄之間；縫 0 在最左）
  edges.forEach(e => {
    if (e.part && col(e.from) === col(e.to)) { e.kind = 'part'; e.gaps = [col(e.to)]; }
    else if (col(e.from) === col(e.to) + 1) { e.kind = 'adj'; e.gaps = [col(e.from)]; }
    else { e.kind = 'long'; e.gaps = [col(e.from), col(e.to) + 1]; }
  });
  const gapTracks = {}; edges.forEach(e => e.gaps.forEach(g => (gapTracks[g] = gapTracks[g] || []).push(e)));
  const TR = 12, BASE = small ? 300 : 90;
  const gapW = g => BASE + (gapTracks[g] || []).length * TR;
  const colX = []; let x = gapW(0);
  for (let c = 0; c < ncol; c++) { colX[c] = x; x += W + gapW(c + 1); }
  const longs = edges.filter(e => e.kind === 'long');
  const TOP = 30 + longs.length * 10;
  const RG = small ? 60 : 26;
  const box = {};
  let VH = 0;
  cols.forEach((ids, c) => { let y = TOP; ids.forEach(id => { box[id] = { x: colX[c], y, w: W, h: hOf(id) }; y += hOf(id) + RG; }); VH = Math.max(VH, y - RG); });
  const VW = x - gapW(ncol) + 40;
  // 軌道 x：每個縫從右往左一條一條分
  const trackX = new Map();
  for (const [g, list] of Object.entries(gapTracks)) {
    const right = g < ncol ? colX[g] : x;
    list.forEach((e, i) => trackX.set(e.id = e.id || Symbol(), trackX.get(e.id) || {}) );
    list.forEach((e, i) => { const t = trackX.get(e.id); t[g] = right - 16 - i * TR; });
  }
  // 出口、入口的高度：同一個方塊同一側錯開
  const SP = small ? 26 : 12;
  const slot = (id, list) => { const b = box[id]; const n = list.length; const sp = Math.min(SP, (b.h - 20) / Math.max(n, 1)); return list.map((e, i) => b.y + 14 + i * Math.max(sp, 6)); };
  const outL = {}, inR = {}, inL = {}, partOut = {};
  edges.forEach(e => {
    if (e.kind === 'part') { (partOut[e.from] = partOut[e.from] || []).push(e); (inL[e.to] = inL[e.to] || []).push(e); }
    else { (outL[e.from] = outL[e.from] || []).push(e); (inR[e.to] = inR[e.to] || []).push(e); }
  });
  for (const [id, list] of Object.entries(outL)) { list.sort((p, q) => box[p.to].y - box[q.to].y); slot(id, list).forEach((y, i) => list[i].y1 = y); }
  for (const [id, list] of Object.entries(inR)) { list.sort((p, q) => box[p.from].y - box[q.from].y); slot(id, list).forEach((y, i) => list[i].y2 = y); }
  for (const [id, list] of Object.entries(inL)) { slot(id, list).forEach((y, i) => list[i].y2 = box[id].y + box[id].h - 10 - i * 8); }
  for (const [id, list] of Object.entries(partOut)) list.forEach((e, i) => e.y1 = box[id].y + 14 + i * 6);
  let lane = 0, el = '', lb = '';
  const mk = 'rm' + (++MK);
  for (const e of edges) {
    const a = box[e.from], b = box[e.to], t = trackX.get(e.id);
    let d;
    if (e.kind === 'part') { const tx = t[col(e.to)]; d = `M${a.x} ${e.y1} H${tx} V${e.y2} H${b.x - 2}`; }
    else if (e.kind === 'adj') { const tx = t[col(e.from)]; d = `M${a.x} ${e.y1} H${tx} V${e.y2} H${b.x + b.w + 2}`; }
    else { const t1 = t[col(e.from)], t2 = t[col(e.to) + 1], cy = TOP - 20 - (lane++) * 10; d = `M${a.x} ${e.y1} H${t1} V${cy} H${t2} V${e.y2} H${b.x + b.w + 2}`; }
    el += `<path class="ed" data-f="${e.from}" data-t="${e.to}" d="${d}" fill="none" stroke="#94a3b8" stroke-width="1.4" stroke-linejoin="round" marker-end="url(#${mk})"/>`;
    if (small) {
      const tw = cjkW(e.text, 12) + 14;
      const lx = e.kind === 'part' ? b.x + 8 : b.x + b.w + 12, ly = e.kind === 'part' ? (b.y + b.h + a.y) / 2 : e.y2 - 13;
      lb += `<g class="el" data-f="${e.from}" data-t="${e.to}"><rect x="${lx}" y="${ly - 10}" width="${tw}" height="20" rx="4" fill="#fff" stroke="#cbd5e1"/><text x="${lx + tw / 2}" y="${ly + 4}" text-anchor="middle" font-size="12" fill="#0f172a">${esc(e.text)}</text></g>`;
    }
  }
  let bx = '';
  for (const id of Object.keys(N)) {
    const b = box[id], d = N[id].d;
    if (N[id].ghost) { const mm = moduleOfData(id); bx += `<g class="bx" data-id="${id}"><rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="6" fill="#fff" stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="5 4"/><text x="${b.x + 10}" y="${b.y + 24}" font-size="14" font-weight="700" fill="#64748b">${esc(d.name)}</text><text x="${b.x + b.w - 10}" y="${b.y + 24}" text-anchor="end" font-size="11" fill="#94a3b8">${esc(mm.name)}</text></g>`; continue; }
    bx += `<g class="bx" data-id="${id}"><rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="6" fill="#fff" stroke="#059669" stroke-width="1.5"/><text x="${b.x + 10}" y="${b.y + 21}" font-size="14" font-weight="700" fill="#059669">${esc(d.name)}</text><text x="${b.x + b.w - 10}" y="${b.y + 21}" text-anchor="end" font-size="10" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" fill="#64748b">${esc(id)}</text><line x1="${b.x}" y1="${b.y + HEAD}" x2="${b.x + b.w}" y2="${b.y + HEAD}" stroke="#e2e8f0"/>`;
    d.fields.forEach((f, i) => { const c = cell(f); const cc = c.mark === 'ai' ? '#8a94a6' : c.mark === 'dec' ? '#c2410c' : '#0f172a'; bx += `<text x="${b.x + 10}" y="${b.y + HEAD + PAD + i * LH + 4}" font-size="12" fill="${cc}">${esc(c.text)}</text>`; });
    bx += `</g>`;
  }
  const svg = `<svg class="relsvg" data-w="${VW}" data-h="${VH + 20}" data-small="${small ? 1 : 0}" xmlns="http://www.w3.org/2000/svg"><defs><marker id="${mk}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="context-stroke"/></marker></defs><g class="eds">${el}</g><g class="bxs">${bx}</g><g class="els">${lb}</g></svg>`;
  const allE = J.data.flatMap(d => (d.refs || []).filter(r => byId(J.data, r.to) && r.to !== d.id).map(r => ({ from: d.id, to: r.to, text: r.text })));
  const info = Object.keys(N).map(id => {
    const d = N[id].d, outs = allE.filter(e => e.from === id), ins = allE.filter(e => e.to === id), self = (d.refs || []).filter(r => r.to === id);
    const li = e => { const o = e.from === id ? e.to : e.from; return `<li><a data-go="${o}">${esc(byId(J.data, o).name)}</a>${moduleOfData(o).id !== m.id ? `<span class="tag">${esc(moduleOfData(o).name)}</span>` : ''}：${esc(e.text)}</li>`; };
    return `<div class="info" data-info="${id}" hidden><h4>${esc(d.name)}<code>${esc(id)}</code></h4><p class="note">${esc(moduleOfData(id).name)}・<a href="#/data/d-row-${id}">看欄位</a></p>${outs.length ? `<h5>它引用</h5><ul>${outs.map(li).join('')}</ul>` : ''}${ins.length ? `<h5>引用它的</h5><ul>${ins.map(li).join('')}</ul>` : ''}${self.length ? `<h5>引用自己</h5><ul>${self.map(r => `<li>${esc(r.text)}</li>`).join('')}</ul>` : ''}${(d.rels || []).length ? `<h5>其他約束</h5><ul>${d.rels.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}</div>`;
  }).join('');
  return `<div class="relwrap" data-m="${m.id}">${svg}
<div class="zoom"><button type="button" data-z="in" title="放大">＋</button><button type="button" data-z="out" title="縮小">－</button><button type="button" data-z="fit" title="符合畫面">⤢</button></div>
<div class="relpanel"><p class="note relhint">點一種資料，看它引用誰、誰引用它。滾輪縮放，拖曳移動。</p>${info}</div></div>`;
}
const relView = `<section class="view fill" data-view="rel" data-title="關係" data-sub="" hidden>${J.modules.map(relMapModule).join('\n')}<p class="empty" hidden>沒有資料</p></section>`;

// ── 頁面頁：每頁一列（模組、頁面、種類、資料、動作） ──
const actionsOf = p => {
  const rows = [];
  for (const f of (J.flows || [])) for (const st of f.steps) if (st.page === p.id && !st.dashed) rows.push({ label: st.label, opens: st.opens, spec: st.spec });
  for (const x of (p.actions || [])) { const a = typeof x === 'object' ? x : { label: x }; if (!rows.some(r => r.label === a.label)) rows.push(a); }
  return rows;
};
const wcell = w => w ? `<span class="${w.mark || 'src'}">${esc(w.name)}</span>` : '<span class="none">—</span>';
const wcode = w => w ? esc(w.id) : '';
const pageView = `<section class="view fill" data-view="page" data-title="頁面" data-sub="" hidden>
<div class="card tbl"><table class="pages">
<tr><th class="mcol">模組</th><th>頁面</th><th>資料</th><th>動作</th><th>互動元件</th><th>頁面程式名</th><th>元件程式名</th></tr>
${(() => { const PG = J.pages.filter(p => p.kind !== 'widget'); const rowsOf = p => Math.max(1, actionsOf(p).length); const mrows = {}; PG.forEach(p => { const id = moduleOfData(p.data).id; mrows[id] = (mrows[id] || 0) + rowsOf(p); }); const seen = new Set(); return PG.map(p => {
  const m = moduleOfData(p.data), acts = actionsOf(p); const firstM = !seen.has(m.id); seen.add(m.id);
  const loose = J.pages.filter(w => w.kind === 'widget' && (w.used_by || []).includes(p.id) && !acts.some(a => a.opens === w.id));
  const rows = acts.length ? acts : [{ label: null }];
  const n = rows.length;
  const head = `${firstM ? `<td rowspan="${mrows[m.id]}" class="grp">${esc(m.name)}</td>` : ''}<td rowspan="${n}" class="key ${p.mark || 'src'}">${esc(p.name)}</td><td rowspan="${n}">${esc(byId(J.data, p.data).name)}</td>`;
  return rows.map((r, i) => `<tr${i === 0 ? ` id="page-${p.id}"` : ''} data-m="${m.id}" class="${i === n - 1 ? 'last' : ''}">${i === 0 ? head : ''}<td>${!r.label ? '<span class="none">—</span>' : r.spec ? `<a class="act" data-spec-open="${r.spec}" title="看規格">${esc(r.label)}</a>` : esc(r.label)}</td><td>${r.opens ? wcell(pageById(r.opens)) : (i === 0 && loose.length ? loose.map(wcell).join('<br>') : '<span class="none">—</span>')}</td>${i === 0 ? `<td rowspan="${n}" class="code">${esc(p.id)}</td>` : ''}<td class="code">${r.opens ? wcode(pageById(r.opens)) : (i === 0 && loose.length ? loose.map(wcode).join('<br>') : '')}</td></tr>`).join('\n');
}).join('\n'); })()}
<tr class="emptyrow" hidden><td colspan="99">沒有資料</td></tr>
</table></div>
</section>`;

// ── 流程頁：先一張表條列所有按鈕（箭頭），再泳道 ──
const allSteps = (J.flows || []).flatMap(f => f.steps.map(s => ({ ...s, data: byId(J.data, f.data).name, m: moduleOfData(f.data).id })));
const flowView = `<section class="view" data-view="flow" data-title="流程" data-sub="" hidden>
${J.modules.filter(m => flowsOf(m).length).map(m => `<div class="card blk" data-m="${m.id}">${sub(m, 'flow')}${flowsOf(m).map(flowBlock).join('')}</div>`).join('\n')}
<p class="empty" hidden>沒有資料</p>
</section>`;

// ── 原則頁：一張表 ──
const ruleView = `<section class="view fill" data-view="rule" data-title="原則" data-sub="" hidden>
<div class="card tbl"><table>
<tr><th class="mcol">模組</th><th>原則</th><th>備註</th><th>程式名</th></tr>
${J.principles.map((p, i, arr) => { const first = i === 0 || arr[i - 1].module !== p.module; const n = arr.filter(x => x.module === p.module).length; return `<tr id="rule-${p.id}" data-m="${p.module}">${first ? `<td rowspan="${n}" class="grp">${esc(byId(J.modules, p.module).name)}</td>` : ''}<td class="${p.mark || 'src'}">${esc(p.text)}</td><td class="${p.mark || 'src'}">${p.mark && p.mark !== 'src' && p.tag ? `<small>${esc(p.tag)}</small>` : ''}</td><td class="code">${esc(p.id)}</td></tr>`; }).join('\n')}
<tr class="emptyrow" hidden><td colspan="99">沒有資料</td></tr>
</table></div>
</section>`;

// ── 規格頁：一塊規格六項，一項一列 ──
const SPEC_ITEMS = [['action', '動作'], ['fields', '欄位'], ['calc', '計算'], ['permission', '權限'], ['response', '回應'], ['accept', '驗收']];
const stepOfSpec = id => {
  for (const f of (J.flows || [])) for (const st of f.steps) if (st.spec === id) return { st, f, roles: [st.lane] };
  for (const p of J.pages) for (const a of (p.actions || [])) if (typeof a === 'object' && a.spec === id) { const m = moduleOfData(p.data); return { st: { label: a.label, page: p.id }, f: { data: p.data }, roles: a.roles || p.roles || (m && m.roles) || [] }; }
  return null;
};
// 規格每一項回指總覽：欄位從資料頁帶、權限從權限算、計算掛原則
const fieldByRef = ref => { const [di, fi] = String(ref).split('.'); const d = byId(J.data, di); const f = d && d.fields.map(cell).find(c => c.id === fi); return d && f ? { d, f } : null; };
const specVal = (S, k) => {
  if (k === 'fields') {
    if (!Array.isArray(S.fields)) return esc(S.fields || '—');
    return S.fields.map(x => { const r = fieldByRef(x.ref); if (!r) return ''; const bits = [r.f.type, r.f.required ? '必填' : '選填', r.f.unique ? '不能重複' : ''].filter(Boolean).join('、'); return `<div class="fr"><a class="lnk" href="#/data/f-${esc(x.ref)}">${esc(r.d.name)}・${esc(r.f.text)}</a><span class="fm">${esc(bits)}</span>${x.note ? `：${esc(x.note)}` : ''}</div>`; }).join('');
  }
  if (k === 'permission') { const o = stepOfSpec(S.id); const rs = o ? o.roles.map(id => byId(J.roles, id)).filter(Boolean) : []; return rs.length ? `${rs.map(r => esc(r.name)).join('、')}<span class="fm">來自權限頁</span>` : esc(S.permission || '—'); }
  if (k === 'calc') { const rs = (S.calc_rules || []).map(id => byId(J.principles, id)).filter(Boolean); return esc(S.calc || '—') + (rs.length ? `<div class="gd">依據：${rs.map(g => `<a class="lnk ${g.mark || 'src'}" href="#/rule/rule-${g.id}">${esc(g.text)}</a>`).join('、')}</div>` : ''); }
  return esc(S[k] || '—');
};
const modIdx = id => J.modules.findIndex(m => m.id === id);
const specView = `<section class="view fill" data-view="spec" data-title="規格" data-sub="" hidden>
${(J.specs || []).length ? `<div class="card tbl"><table>
<tr><th class="mcol">模組</th><th>規格</th><th>頁面</th><th>項目</th><th>內容</th><th>程式名</th></tr>
${(() => { const cnt = {}; const rows = J.specs.map(S => { const o = stepOfSpec(S.id); const m = o ? moduleOfData(o.f.data) : J.modules[0]; cnt[m.id] = (cnt[m.id] || 0) + SPEC_ITEMS.length; return { S, o, m }; }).sort((x, y) => modIdx(x.m.id) - modIdx(y.m.id)); const seen = new Set();
  return rows.map(({ S, o, m }) => SPEC_ITEMS.map(([k, label], i) => {
    const firstM = !seen.has(m.id); if (i === 0) seen.add(m.id);
    const ts = J.tests.filter(t => t.spec === S.id);
    const val = k !== 'accept' ? specVal(S, k) : (ts.length ? ts.map(t => { const gs = (t.guards || []).map(g => byId(J.principles, g)).filter(Boolean); return `<div class="tt"><span class="${t.kind}">${t.kind === 'ok' ? '正常' : '不能出錯'}</span>：${esc(t.text)}${gs.length ? `<div class="gd">守護：${gs.map(g => `<span class="${g.mark || 'src'}">${esc(g.text)}</span>`).join('、')}</div>` : ''}</div>`; }).join('') : '<span class="none">還沒有驗收</span>');
    const pg = o && o.st.page ? pageById(o.st.page) : null;
    return `<tr${i === 0 ? ` id="spec-${S.id}"` : ''} data-m="${m.id}">${i === 0 && firstM ? `<td rowspan="${cnt[m.id]}" class="grp">${esc(m.name)}</td>` : ''}${i === 0 ? `<td rowspan="${SPEC_ITEMS.length}" class="key">${esc(o ? o.st.label : S.title)}</td><td rowspan="${SPEC_ITEMS.length}" class="nowrap">${pg ? esc(pg.name) : '<span class="none">—</span>'}</td>` : ''}<td class="nowrap">${label}</td><td>${val}</td>${i === 0 ? `<td rowspan="${SPEC_ITEMS.length}" class="code">${esc(S.id)}</td>` : ''}</tr>`;
  }).join('\n')).join('\n'); })()}
<tr class="emptyrow" hidden><td colspan="99">沒有資料</td></tr>
</table></div>` : `<div class="card blk"><span class="none">還沒有規格。挑一顆會改資料的按鈕，寫它的六項。</span></div>`}
</section>`;

// ── 規格對話框：從頁面動作、泳道方塊點進來，不離開原頁 ──
const specDialog = `<div class="dmask" id="specdlg" hidden><div class="dlg" role="dialog" aria-modal="true">
${(J.specs || []).map(S => {
  const o = stepOfSpec(S.id); const pg = o && o.st.page ? pageById(o.st.page) : null;
  const ts = J.tests.filter(t => t.spec === S.id);
  return `<div class="spd" data-spec="${S.id}" hidden>
<div class="dh"><div><h3>${esc(o ? o.st.label : S.title)}</h3><p class="note">${pg ? esc(pg.name) : ''}</p></div><button type="button" class="x" data-close title="關閉">✕</button></div>
<div class="db"><dl>${SPEC_ITEMS.filter(([k]) => k !== 'accept').map(([k, l]) => `<dt>${l}</dt><dd>${specVal(S, k)}</dd>`).join('')}
<dt>驗收</dt><dd>${ts.length ? ts.map(t => { const gs = (t.guards || []).map(g => byId(J.principles, g)).filter(Boolean); return `<div class="tt"><span class="${t.kind}">${t.kind === 'ok' ? '正常' : '不能出錯'}</span>：${esc(t.text)}${gs.length ? `<div class="gd">守護：${gs.map(g => `<span class="${g.mark || 'src'}">${esc(g.text)}</span>`).join('、')}</div>` : ''}</div>`; }).join('') : '<span class="none">還沒有驗收</span>'}</dd></dl></div>
<div class="df"><code>${esc(S.id)}</code><a class="lnk" href="#/spec/spec-${S.id}" data-close>到規格頁</a></div>
</div>`; }).join('\n')}
</div></div>`;

// ── 權限頁：一個動作一列，每個角色一欄 ──
const permRows = [];
for (const p of J.pages.filter(p => p.kind !== 'widget')) {
  const m = moduleOfData(p.data);
  const viewRoles = p.roles || m.roles || [];
  permRows.push({ m, p, label: '查看', roles: viewRoles });
  for (const a of actionsOf(p)) {
    let roles = a.roles;
    if (!roles) { for (const f of (J.flows || [])) for (const st of f.steps) if (st.page === p.id && st.label === a.label) roles = [st.lane]; }
    permRows.push({ m, p, label: a.label, roles: roles || viewRoles });
  }
}
const permView = `<section class="view fill" data-view="perm" data-title="權限" data-sub="" hidden>
<div class="card tbl"><table>
<tr><th class="mcol">模組</th><th>頁面</th><th>動作</th>${J.roles.map((r, i) => `<th class="c" style="color:${roleColor(i)}">${esc(r.name)}</th>`).join('')}<th>頁面程式名</th></tr>
${(() => { const cntM = {}, cntP = {}; permRows.forEach(r => { cntM[r.m.id] = (cntM[r.m.id] || 0) + 1; cntP[r.p.id] = (cntP[r.p.id] || 0) + 1; }); const sm = new Set(), sp = new Set();
  return permRows.map(r => { const fm = !sm.has(r.m.id), fp = !sp.has(r.p.id); sm.add(r.m.id); sp.add(r.p.id);
    return `<tr data-m="${r.m.id}">${fm ? `<td rowspan="${cntM[r.m.id]}" class="grp">${esc(r.m.name)}</td>` : ''}${fp ? `<td rowspan="${cntP[r.p.id]}" class="key">${esc(r.p.name)}</td>` : ''}<td>${esc(r.label)}</td>${J.roles.map(ro => `<td class="c">${r.roles.includes(ro.id) ? '✓' : ''}</td>`).join('')}${fp ? `<td rowspan="${cntP[r.p.id]}" class="code">${esc(r.p.id)}</td>` : ''}</tr>`; }).join('\n'); })()}
<tr class="emptyrow" hidden><td colspan="99">沒有資料</td></tr>
</table></div>
</section>`;

// 版本動到的東西：程式名 → 中文名＋連到哪一頁
const resolveRef = id => {
  if (id.includes('.')) { const [di, fi] = id.split('.'); const d = byId(J.data, di); const f = d && d.fields.map(cell).find(c => c.id === fi); return d && f ? { label: `${d.name}・${f.text}`, href: `#/data/f-${id}` } : null; }
  let x;
  if ((x = byId(J.data, id))) return { label: x.name, href: `#/data/d-row-${id}` };
  if ((x = byId(J.principles, id))) return { label: x.text, href: `#/rule/rule-${id}` };
  if ((x = byId(J.pages, id))) return x.kind === 'widget' ? { label: x.name, href: `#/page/page-${(x.used_by || [])[0] || ''}` } : { label: x.name, href: `#/page/page-${id}` };
  if ((x = byId(J.specs, id))) { const o = stepOfSpec(id); return { label: `規格：${o ? o.st.label : x.title}`, spec: id }; }
  if ((x = byId(J.tests, id))) { const o = stepOfSpec(x.spec); return { label: `驗收：${o ? o.st.label : x.spec}（${x.kind === 'ok' ? '正常' : '不能出錯'}）`, spec: x.spec }; }
  if ((x = byId(J.roles, id))) return { label: `角色：${x.name}`, href: '#/perm' };
  if ((x = byId(J.modules, id))) return { label: `模組：${x.name}`, href: '#/data' };
  for (const f of (J.flows || [])) { const st = f.steps.find(t => t.id === id); if (st) return { label: `流程：${st.label}`, href: '#/flow' }; }
  return null;
};
const badRefs = J.releases.flatMap(r => (r.changes || []).filter(id => !resolveRef(id)).map(id => `${r.v} 動到的 ${id} 不存在`));
if (badRefs.length) { console.error('版本紀錄有問題，不出頁：\n  ' + badRefs.join('\n  ')); process.exit(1); }
const chg = id => { const x = resolveRef(id); return x.spec ? `<a class="act" data-spec-open="${x.spec}">${esc(x.label)}</a>` : `<a class="act" href="${x.href}">${esc(x.label)}</a>`; };
const releasesView = `<section class="view" data-view="releases" data-title="版本" data-sub="" hidden>
<div class="card tbl"><table><tr><th>版本</th><th>日期</th><th>改了什麼</th><th>動到哪些</th><th>誰決定的</th></tr>
${J.releases.map(r => `<tr><td class="key">${esc(r.v)}</td><td class="nowrap">${esc(r.date)}</td><td>${esc(r.what)}</td><td class="chgs">${(r.changes || []).length ? r.changes.map(chg).join('') : '<span class="none">—</span>'}</td><td>${esc(r.who)}</td></tr>`).join('\n')}
</table></div>
</section>`;



// ── 計數：AI 推的、拍板的各幾條；第一條在哪一頁，讓計數點得過去 ──
const marked = [];
J.data.forEach(d => { if (d.mark && d.mark !== 'src') marked.push({ mark: d.mark, href: `#/data/d-row-${d.id}` }); d.fields.forEach(f => { const c = cell(f); if (c.mark && c.mark !== 'src') marked.push({ mark: c.mark, href: `#/data/d-row-${d.id}` }); }); });
J.principles.forEach(p => { if (p.mark && p.mark !== 'src') marked.push({ mark: p.mark, href: `#/rule/rule-${p.id}` }); });
J.pages.forEach(p => { if (p.mark && p.mark !== 'src') marked.push({ mark: p.mark, href: `#/page/page-${p.id}` }); });
const firstOf = mk => { const x = marked.find(y => y.mark === mk); return x ? x.href : '#/data'; };
const nAi = marked.filter(x => x.mark === 'ai').length, nDec = marked.filter(x => x.mark === 'dec').length;
const nPages = J.modules.reduce((n, m) => n + pageCount(m), 0);

// ── 版面：照 lean-admin 的 AppShell（側欄 w-44 白底、品牌列 h-14、選單 p-2 rounded-md text-sm、頂 bar h-14、內容 p-5）與設計 token ──
const CSS = `
:root{--radius:.375rem;--background:oklch(.96 .004 247.858);--foreground:oklch(.129 .042 264.695);--card:oklch(1 0 0);--muted:oklch(.968 .007 247.896);--muted-foreground:oklch(.554 .046 257.417);--primary:oklch(.208 .042 265.755);--primary-foreground:oklch(.984 .003 247.858);--border:oklch(.929 .013 255.508);--destructive:oklch(.577 .245 27.325);
--blue:#2563eb;--green:#059669;--orange:#c2410c;--gray:#8a94a6;--r-sm:calc(var(--radius) - 4px);--r-md:calc(var(--radius) - 2px);--r-lg:var(--radius);--shadow-sm:0 1px 3px 0 rgb(0 0 0/.1),0 1px 2px -1px rgb(0 0 0/.1)}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--background);color:var(--foreground);font:14px/1.55 Inter,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}
a{color:inherit;text-decoration:none}
.shell{display:flex;height:100vh;width:100vw;overflow:hidden}
aside{width:176px;flex:none;display:flex;flex-direction:column;overflow:hidden;border-right:1px solid var(--border);background:var(--card)}
.brand{height:56px;flex:none;display:flex;align-items:center;gap:12px;padding:0 20px;border-bottom:1px solid var(--border)}
.brand i{width:32px;height:32px;border-radius:8px;background:var(--primary);color:var(--primary-foreground);display:grid;place-items:center;font-size:13px;font-weight:700;font-style:normal;flex:none}
.brand b{font-size:15px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
nav{flex:1;display:flex;flex-direction:column;gap:2px;overflow:auto;padding:8px}
nav a{display:flex;align-items:center;gap:12px;padding:8px 12px;border-radius:var(--r-md);font-size:14px;color:var(--muted-foreground);white-space:nowrap;transition:background .15s,color .15s}
nav a:hover{background:var(--muted);color:var(--foreground)}
nav a.on{background:var(--muted);color:var(--foreground);font-weight:500}
nav a svg{width:16px;height:16px;flex:none}
.foot{padding:16px;font-size:12px;color:var(--muted-foreground);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.right{flex:1;min-width:0;display:flex;flex-direction:column;overflow:hidden}
header{height:56px;flex:none;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:0 24px;border-bottom:1px solid var(--border);background:var(--card)}
header h1{font-size:18px;margin:0;line-height:1;font-weight:600;letter-spacing:-.01em}
header .sub{margin-left:12px;font-size:13px;color:var(--muted-foreground)}
.sel{position:relative}
.selbtn{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 10px 0 12px;border:1px solid var(--border);border-radius:var(--r-md);background:var(--card);color:var(--foreground);font:inherit;font-size:13px;cursor:pointer;box-shadow:var(--shadow-sm)}
.selbtn:hover{background:var(--muted)}.selbtn svg{width:14px;height:14px;color:var(--muted-foreground)}
.sel .menu{position:absolute;top:calc(100% + 6px);left:0;z-index:20;min-width:140px;padding:4px;border:1px solid var(--border);border-radius:var(--r-md);background:var(--card);box-shadow:0 10px 15px -3px rgb(0 0 0/.1),0 4px 6px -4px rgb(0 0 0/.1)}
.sel .menu a{display:block;padding:7px 10px;border-radius:var(--r-sm);font-size:13px;cursor:pointer;white-space:nowrap}
.sel .menu a:hover{background:var(--muted)}.sel .menu a.on{font-weight:500;background:var(--muted)}
[data-m].dim{display:none}svg [data-m].dim{display:block;opacity:.12}
.count{display:flex;gap:8px;flex:none;flex-wrap:wrap}
.count a{border:1px solid var(--border);border-radius:999px;padding:3px 12px;font-size:13px;white-space:nowrap;color:var(--muted-foreground);background:var(--card)}
.count b{font-weight:600;color:var(--foreground)}
.count a.ai{color:var(--gray);border-color:var(--gray)}.count a.ai b{color:var(--gray)}
.count a.dec{color:var(--orange);border-color:var(--orange)}.count a.dec b{color:var(--orange)}
main{flex:1;min-width:0;overflow:auto;padding:20px;background:#fbfcfe;display:flex;flex-direction:column}
.emptyrow td{color:var(--muted-foreground);text-align:center;padding:28px 12px}.empty{color:var(--muted-foreground);font-size:14px;text-align:center;padding:28px 0;margin:0}
.view{flex:none}.view.fill{flex:1;min-height:0;display:flex;flex-direction:column}
.view[hidden]{display:none!important}
.view.fill>.tbl{flex:1;min-height:0;overflow:auto}
.view.fill>.tbl::-webkit-scrollbar{width:6px;height:6px}.view.fill>.tbl::-webkit-scrollbar-thumb{background:rgb(15 23 42/.35);border-radius:99px}
.tbl th{position:sticky;top:0;z-index:3;background:var(--card)}
.tbl td .stk{position:sticky;top:calc(var(--thh, 40px) + 9px)}
.view.fill>.relwrap{height:auto}.view.fill>.relwrap:not(.dim){flex:1;min-height:0}
.view.fill>.card.blk{flex:none}
main::-webkit-scrollbar{width:4px;height:4px}main::-webkit-scrollbar-thumb{background:rgb(15 23 42/.6);border-radius:99px}
.view{width:100%}
.h{font-size:12px;color:var(--muted-foreground);font-weight:600;letter-spacing:.12em;text-transform:uppercase;margin:24px 0 6px}.view>.h:first-child{margin-top:0}
.card{border:1px solid var(--border);border-radius:var(--r-lg);background:var(--card);box-shadow:var(--shadow-sm)}
.tbl{overflow:hidden}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--border);margin:0 0 16px}
.mbar{flex:none;position:sticky;top:-20px;z-index:10;background:#fbfcfe;margin:-20px -20px 16px;padding:14px 20px 12px;border-bottom:1px solid var(--border)}
.mbar[hidden]{display:none}
.relwrap{position:relative;height:calc(100vh - 110px);border:1px solid var(--border);border-radius:var(--r-lg);background:#fff;box-shadow:var(--shadow-sm);overflow:hidden}
svg.relsvg{width:100%;height:100%;display:block;cursor:grab;user-select:none}svg.relsvg.drag{cursor:grabbing}
.relwrap.dim{display:none}
svg.relsvg .bx{cursor:pointer}
svg.relsvg[data-small="0"] .el{display:none}
svg.relsvg.focus .bx,svg.relsvg.focus .cl{opacity:.18}svg.relsvg.focus .ed{opacity:.06}
svg.relsvg.focus .bx.on,svg.relsvg.focus .ed.on{opacity:1}svg.relsvg.focus .ed.on{stroke:#0f172a;stroke-width:2}
svg.relsvg.focus .el:not(.on){opacity:.1}
svg.relsvg .bx.sel rect{stroke-width:3}
.zoom{position:absolute;left:12px;top:12px;display:flex;flex-direction:column;gap:4px}
.zoom button{width:32px;height:32px;border:1px solid var(--border);border-radius:var(--r-md);background:var(--card);box-shadow:var(--shadow-sm);cursor:pointer;font-size:16px;color:var(--foreground)}
.zoom button:hover{background:var(--muted)}
.relpanel{position:absolute;right:12px;top:12px;width:300px;max-height:calc(100% - 24px);overflow:auto;background:var(--card);border:1px solid var(--border);border-radius:var(--r-lg);box-shadow:var(--shadow-sm);padding:12px 14px;font-size:13px}
.relpanel .note{margin:0}.relpanel h4{margin:0 0 4px;font-size:15px}.relpanel h4 code{margin-left:8px;font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted-foreground);font-weight:400}
.relpanel h5{margin:12px 0 4px;font-size:12px;color:var(--muted-foreground);font-weight:600}.relpanel ul{padding-left:16px}.relpanel li{margin:3px 0}
.relpanel a{text-decoration:underline;text-decoration-color:var(--border);text-underline-offset:3px;cursor:pointer}
.selbtn .lbl{color:var(--muted-foreground)}.selbtn b{font-weight:600}
th.mcol,td.grp,.blk>h3{display:none}
.tab{padding:8px 14px;font-size:14px;color:var(--muted-foreground);border-bottom:2px solid transparent;margin-bottom:-1px;cursor:pointer}
.tab:hover{color:var(--foreground)}.tab.on{color:var(--foreground);font-weight:500;border-bottom-color:var(--primary)}
td.grp{font-weight:500;color:var(--muted-foreground);vertical-align:top}

.blk{padding:16px 20px 18px;margin-bottom:12px}
.blk h3{margin:0 0 12px;font-size:15px;font-weight:600}
.ov{padding:22px 24px 18px}
.purpose{margin:0 0 6px;color:var(--muted-foreground)}
.dmap{overflow-x:auto}.dmap svg{display:block;max-width:none}
ol.rels{margin:12px 0 0;padding-left:26px;font-size:13px;columns:2;column-gap:32px}ol.rels li{break-inside:avoid;margin:2px 0}ol.rels b{font-weight:600}
.legend{display:flex;gap:18px;justify-content:center;color:var(--muted-foreground);font-size:12px;flex-wrap:wrap}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:middle}
ul{margin:0;padding-left:18px}li{margin:4px 0}
.src{color:var(--foreground)}.ai{color:var(--gray)}.dec{color:var(--orange)}.none{color:var(--muted-foreground)}
.tag{font-size:12px;color:var(--muted-foreground);margin-left:6px;white-space:nowrap}.ai .tag{color:var(--gray)}.dec .tag{color:var(--orange)}
.note{font-size:13px;color:var(--muted-foreground);margin:8px 0 12px}
.ent{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.obj{border:1px solid var(--green);border-radius:var(--r-lg);background:#f8fafc;padding:10px 12px}
.obj h4{margin:0 0 6px;font-size:14px;color:var(--green);display:flex;gap:8px;align-items:baseline}.obj h4 small{color:var(--muted-foreground);font-weight:400;font-size:12px}
.obj ul{padding-left:16px;font-size:13px}
.rel{grid-column:1/-1;font-size:13px;color:var(--muted-foreground)}.rel b{color:var(--foreground);font-weight:600}
.ent.linked{grid-template-columns:1fr 130px 1fr}
.link{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;font-size:12px;color:var(--foreground);text-align:center}
.link i{display:block;width:100%;height:1px;background:var(--muted-foreground);position:relative}
.link i::after{content:"";position:absolute;right:-1px;top:-4px;border:4px solid transparent;border-left:6px solid var(--muted-foreground)}
.lane{margin:0 0 20px;overflow:auto}
.ftitle{margin:4px 0 8px;font-size:14px;font-weight:600}.ftitle code{margin-left:8px;font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted-foreground);font-weight:400}.lane svg{display:block;height:auto;max-width:100%}
.btns{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13px;color:var(--muted-foreground);margin:10px 0 4px}
.btn{display:inline-block;border:1px solid var(--border);color:var(--foreground);border-radius:var(--r-md);padding:2px 10px;font-size:12px;cursor:pointer;background:var(--card);box-shadow:var(--shadow-sm)}
.btn.on{background:var(--primary);color:var(--primary-foreground);border-color:var(--primary)}
.spec{border:1px solid var(--border);border-radius:var(--r-lg);padding:12px 16px;margin:4px 0 8px;font-size:13px;background:var(--card);box-shadow:var(--shadow-sm)}
.spec h5{margin:0 0 8px;font-size:13px;color:var(--foreground)}
.spec dl{margin:0;display:grid;grid-template-columns:52px 1fr;gap:6px 12px}.spec dt{color:var(--muted-foreground);font-weight:600}.spec dd{margin:0}
.spec .ok,td .ok{color:var(--green)}.spec .no,td .no{color:var(--destructive)}
a.act{cursor:pointer;}
td.chgs a.act{margin:2px 6px 2px 0}
.dmask{position:fixed;inset:0;background:rgb(15 23 42/.4);display:grid;place-items:center;z-index:50;padding:16px}.dmask[hidden]{display:none}
.dlg{width:720px;max-width:100%;max-height:calc(100vh - 48px);display:flex;flex-direction:column;background:var(--card);border-radius:var(--r-lg);box-shadow:0 20px 25px -5px rgb(0 0 0/.1),0 8px 10px -6px rgb(0 0 0/.1)}
.spd{display:flex;flex-direction:column;min-height:0}.spd[hidden]{display:none}
.dh{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:18px 20px 10px;border-bottom:1px solid var(--border)}.dh h3{margin:0;font-size:16px;font-weight:600}.dh .note{margin:4px 0 0}
.x{border:0;background:none;font-size:16px;color:var(--muted-foreground);cursor:pointer;width:28px;height:28px;border-radius:var(--r-md)}.x:hover{background:var(--muted)}
.db{padding:14px 20px;overflow:auto}.db dl{margin:0;display:grid;grid-template-columns:52px 1fr;gap:10px 14px;font-size:14px}.db dt{color:var(--muted-foreground);font-weight:600}.db dd{margin:0}
.fr{margin:0 0 4px}.fm{margin-left:6px;font-size:12px;color:var(--muted-foreground)}
.tt{margin:0 0 8px}.tt:last-child{margin:0}.gd{font-size:12px;color:var(--muted-foreground);margin-top:2px}
td .tt{margin:0 0 6px}
.dlg .ok{color:var(--green)}.dlg .no{color:var(--destructive)}
.df{display:flex;justify-content:space-between;align-items:center;padding:10px 20px 14px;border-top:1px solid var(--border);font-size:13px}.df code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted-foreground)}
a.act{display:inline-block;padding:0 8px;margin:-1px 0;border:1px solid var(--border);border-radius:var(--r-md);background:var(--card);line-height:22px}a.act:hover{background:var(--muted);border-color:oklch(.87 .02 255)}
a.lnk{text-decoration:underline;text-decoration-color:var(--border);text-underline-offset:3px}a.lnk:hover{text-decoration-color:currentColor}
table{width:100%;margin:0;border-collapse:separate;border-spacing:0;font-size:14px;clip-path:inset(0 1px 0 0)}
.view:not(.fill) .tbl table{clip-path:inset(0 1px 1px 0)}
th,td{padding:9px 12px;text-align:left;vertical-align:top;border:0;border-right:1px solid var(--border);border-bottom:1px solid var(--border)}
th{white-space:nowrap;color:var(--muted-foreground);font-weight:500;font-size:13px;height:40px;background:var(--card)}

td.key{white-space:nowrap;font-weight:500}td.code{font:12px/1.9 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted-foreground);white-space:nowrap}td.grp{white-space:nowrap}td.c,th.c{text-align:center}td code{margin-left:8px;font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted-foreground);font-weight:400;white-space:nowrap}td.nowrap{white-space:nowrap}
tr.hit td{background:#fff7ed}
.spec-row td{background:#fbfcfe}
.specbox.on rect{fill:#f1f5f9}
@media (max-width:767px){.shell{flex-direction:column;height:auto;overflow:visible}aside{width:auto;border-right:0;border-bottom:1px solid var(--border)}nav{flex-direction:row;flex-wrap:wrap}main{overflow:visible}.ent.linked{grid-template-columns:1fr}header .sub{display:none}}
`;

const ICON = {
  overview: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  data: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg>',
  page: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>',
  flow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="6" height="6" rx="1"/><rect x="15" y="14" width="6" height="6" rx="1"/><path d="M9 7h4a2 2 0 0 1 2 2v5"/></svg>',
  spec: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l2 2 4-4"/><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 17h8"/></svg>',
  perm: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="4"/><path d="M2 21v-1a6 6 0 0 1 12 0v1"/><rect x="15" y="12" width="7" height="6" rx="1"/><path d="M16.5 12v-2a2 2 0 0 1 4 0v2"/></svg>',
  test: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
  rel: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/><rect x="15" y="3" width="6" height="6" rx="1"/><path d="M9 6h6M18 9v6"/></svg>',
  rule: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z"/><path d="M9 12l2 2 4-4"/></svg>',
  proto: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 21h8M12 18v3"/></svg>',
  releases: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/></svg>'
};
const NAV = [['data', '資料'], ['rel', '關係'], ['page', '頁面'], ['spec', '規格'], ['perm', '權限'], ['flow', '流程'], ['rule', '原則'], ['releases', '版本']];

const html = `<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(J.system.name)}｜系統總覽</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>${CSS}</style></head>
<body>
<!-- 由 build.cjs 從 系統總覽.json 產生；正本是 json，不手改這個檔 -->
<div class="shell">
<aside>
  <a class="brand" href="#/data"><i>總</i><b>${esc(J.system.name)}${/[A-Za-z0-9]$/.test(J.system.name) ? ' ' : ''}總覽</b></a>
  <nav>
${NAV.map(([id, name]) => `    <a href="#/${id}" data-nav="${id}">${ICON[id]}${name}</a>`).join('\n')}
  </nav>
  <div class="foot">${esc(J.releases[0] ? J.releases[0].v + ' · ' + J.releases[0].date : '')}</div>
</aside>
<div class="right">
  <main>
<div class="mbar" id="mbar"><div class="sel" id="modsel"><button type="button" class="selbtn"><span class="lbl">模組</span><b id="modsel-txt"></b><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg></button>
  <div class="menu" hidden>${J.modules.map(m => `<a data-m="${m.id}">${esc(m.name)}</a>`).join('')}</div></div></div>
${dataView}
${relView}
${pageView}
${flowView}
${specView}
${permView}
${ruleView}
${releasesView}

  </main>
${specDialog}
</div>
</div>
<script>
(function(){
  const views=[...document.querySelectorAll('.view')], navs=[...document.querySelectorAll('nav a')], main=document.querySelector('main');
  let route=function(){
    const p=(location.hash.replace(/^#\\/?/,'')||'data').split('/');
    let v=views.find(x=>x.dataset.view===p[0]); if(!v)v=views[0];
    views.forEach(x=>x.hidden=x!==v);
    navs.forEach(a=>a.classList.toggle('on',a.dataset.nav===v.dataset.view));
    document.querySelectorAll('.hit').forEach(t=>t.classList.remove('hit'));
    main.scrollTop=0;
    if(p[1]){const t=document.getElementById(p[1])||document.querySelector('[data-anchor="'+p[1]+'"]'); if(t){t.classList.add('hit'); t.scrollIntoView({block:'center'});}}
  }
  const MODS=[...document.querySelectorAll('#modsel .menu a')].map(a=>a.dataset.m);
  let curM=MODS[0]; try{const v=localStorage.getItem('ovModule'); if(v&&MODS.includes(v))curM=v;}catch(e){}
  const menu=document.querySelector('#modsel .menu'), txt=document.getElementById('modsel-txt'), mbar=document.getElementById('mbar');
  function applyM(){
    document.querySelectorAll('.view [data-m]').forEach(el=>el.classList.toggle('dim',el.dataset.m!==curM)); if(window.relFit)window.relFit();
    views.forEach(v=>{const e=v.querySelector('.emptyrow,.empty'); if(e)e.hidden=[...v.querySelectorAll('[data-m]')].some(x=>x.dataset.m===curM);});
    menu.querySelectorAll('a').forEach(a=>a.classList.toggle('on',a.dataset.m===curM));
    txt.textContent=menu.querySelector('a[data-m="'+curM+'"]').textContent;
  }
  document.querySelector('#modsel .selbtn').addEventListener('click',e=>{e.stopPropagation();menu.hidden=!menu.hidden;});
  menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{curM=a.dataset.m;menu.hidden=true;try{localStorage.setItem('ovModule',curM);}catch(e){}applyM();}));
  document.addEventListener('click',()=>{menu.hidden=true;});
  const r0=route; route=function(){
    r0();
    const v=views.find(x=>!x.hidden); mbar.hidden=v.dataset.view==='releases';
    const t=document.querySelector('tr.hit'); if(t&&t.dataset.m&&t.dataset.m!==curM){curM=t.dataset.m;}
    applyM(); if(t)t.scrollIntoView({block:'center'});
  };
  const relInits=[];
  document.querySelectorAll('.relwrap').forEach(wrap=>{
    const svg=wrap.querySelector('svg.relsvg'); const W=+svg.dataset.w, H=+svg.dataset.h; let vb=null;
    const set=()=>svg.setAttribute('viewBox',vb.join(' '));
    const fit=()=>{const r=svg.getBoundingClientRect(); if(!r.width) return false; const pad=30, side=330, aw=Math.max(200,r.width-side), s=Math.max((W+pad*2)/aw,(H+pad*2)/r.height,0.6); vb=[-pad,-pad,r.width*s,r.height*s]; set(); return true;};
    const zoomAt=(k,cx,cy)=>{const r=svg.getBoundingClientRect(); const px=vb[0]+(cx-r.left)/r.width*vb[2], py=vb[1]+(cy-r.top)/r.height*vb[3]; vb=[px-(px-vb[0])*k,py-(py-vb[1])*k,vb[2]*k,vb[3]*k]; set();};
    svg.addEventListener('wheel',e=>{e.preventDefault(); if(!vb&&!fit())return; zoomAt(e.deltaY>0?1.12:1/1.12,e.clientX,e.clientY);},{passive:false});
    let drag=null, moved=false;
    svg.addEventListener('mousedown',e=>{if(!vb&&!fit())return; drag={x:e.clientX,y:e.clientY,vb:vb.slice()};moved=false;svg.classList.add('drag');});
    window.addEventListener('mousemove',e=>{if(!drag)return; const r=svg.getBoundingClientRect(); const dx=(e.clientX-drag.x)/r.width*vb[2], dy=(e.clientY-drag.y)/r.height*vb[3]; if(Math.abs(e.clientX-drag.x)+Math.abs(e.clientY-drag.y)>3)moved=true; vb=[drag.vb[0]-dx,drag.vb[1]-dy,vb[2],vb[3]]; set();});
    window.addEventListener('mouseup',()=>{if(drag){drag=null;svg.classList.remove('drag');}});
    wrap.querySelectorAll('.zoom button').forEach(b=>b.addEventListener('click',()=>{if(!vb&&!fit())return; const r=svg.getBoundingClientRect(); if(b.dataset.z==='fit')fit(); else zoomAt(b.dataset.z==='in'?1/1.3:1.3,r.left+r.width/2,r.top+r.height/2);}));
    const panel=wrap.querySelector('.relpanel'), hint=wrap.querySelector('.relhint');
    function focus(id){
      svg.classList.toggle('focus',!!id);
      svg.querySelectorAll('.on,.sel').forEach(x=>x.classList.remove('on','sel'));
      panel.querySelectorAll('.info').forEach(x=>x.hidden=x.dataset.info!==id); hint.hidden=!!id;
      if(!id) return;
      const nb=new Set([id]);
      svg.querySelectorAll('.ed,.el').forEach(x=>{if(x.dataset.f===id||x.dataset.t===id){x.classList.add('on');nb.add(x.dataset.f);nb.add(x.dataset.t);}});
      svg.querySelectorAll('.bx').forEach(x=>{if(nb.has(x.dataset.id))x.classList.add('on'); if(x.dataset.id===id)x.classList.add('sel');});
    }
    svg.addEventListener('click',e=>{if(moved)return; const b=e.target.closest('.bx'); focus(b?b.dataset.id:null);});
    panel.addEventListener('click',e=>{const a=e.target.closest('[data-go]'); if(!a)return; const id=a.dataset.go; if(svg.querySelector('.bx[data-id="'+id+'"]')) focus(id); else location.hash='#/data/d-row-'+id;});
    relInits.push(()=>{ if(!wrap.classList.contains('dim') && !vb) requestAnimationFrame(fit); });
  });
  window.relFit=()=>relInits.forEach(f=>f());
  { const r1=route; route=function(){r1(); const v=views.find(x=>!x.hidden); if(v.dataset.view==='rel') window.relFit();}; }
  const setThh=()=>document.querySelectorAll('.view:not([hidden]) .tbl').forEach(t=>{const th=t.querySelector('th'); if(th&&th.offsetHeight)t.style.setProperty('--thh',th.offsetHeight+'px');});
  { const r2=route; route=function(){r2(); requestAnimationFrame(setThh); const d=document.getElementById('specdlg'); if(d)d.hidden=true;}; }
  // 跳過來的那一列會反白；點其他地方就清掉（點同一個連結再亮一次）
  document.addEventListener('click',e=>{
    const a=e.target.closest('a[href^="#/"]');
    if(a){ if(a.getAttribute('href')===location.hash) route(); return; }
    if(e.target.closest('#specdlg,#modsel')) return;
    document.querySelectorAll('.hit').forEach(t=>t.classList.remove('hit'));
  });
  window.addEventListener('hashchange',route); route();
  const dlg=document.getElementById('specdlg');
  const openSpec=id=>{if(!dlg)return; dlg.querySelectorAll('.spd').forEach(x=>x.hidden=x.dataset.spec!==id); dlg.hidden=false;};
  const closeSpec=()=>{if(dlg)dlg.hidden=true;};
  document.querySelectorAll('[data-spec-open]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();openSpec(a.dataset.specOpen);}));
  document.querySelectorAll('.specbox').forEach(b=>b.addEventListener('click',e=>{e.stopImmediatePropagation();openSpec(b.dataset.spec);},true));
  if(dlg){dlg.addEventListener('click',e=>{if(e.target===dlg||e.target.closest('[data-close]')||e.target.closest('a[href]'))closeSpec();}); document.addEventListener('keydown',e=>{if(e.key==='Escape')closeSpec();});}
})();
</script>
</body></html>
`;
const htmlOut = html.replace(/<td rowspan="(\d+)"([^>]*)>([\s\S]*?)<\/td>/g, (m0, n, attrs, inner) => +n > 1 ? `<td rowspan="${n}"${attrs}><div class="stk">${inner}</div></td>` : m0);
fs.writeFileSync(out, htmlOut);
console.log(`出 ${out}：${J.modules.length} 模組、${J.data.length} 種資料、${nPages} 頁、AI 推 ${nAi}、拍板 ${nDec}`);
