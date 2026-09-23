# lean-erp — AI 助理指引

報價系統：3C 店的業務替公司客戶開報價單，匯出 PDF 傳給客戶。骨架來自 lean-stack（Django-Ninja + Vue3），domain 是這個 repo 自己的。

## 動工前先讀

1. `intents/系統總覽.json` —— 正本：資料、關係、頁面、規格、權限、流程、原則、版本。**每次動工先看全貌。** 人看的是產生器出的 `intents/系統總覽.html`。
2. 要蓋哪一顆按鈕，就讀系統總覽裡那一塊 `specs`（動作、欄位、計算、回應）和它的 `tests`。

**規則**：新需求不要直接改 code——先用 `system-overview` skill 的改版模式落進系統總覽（新的資料？新的頁？撞到哪條原則？），json 改完跑產生器，再照規格施工。系統總覽上沒有的東西不進程式。

## 紅線

- **零真實資料**。這是公開 repo，資料一律 seed 假資料；`.env` 永不進版控。
- **總額不存欄位**、不接受輸入——由品項現算（rule_total_sum）。
- **單價不收前端的數字**——建立時從商品帶入、之後不變（rule_price_from_product、rule_price_frozen）。
- **門預設是關的，而且照模組分角色**：銷售管理的 router 掛 `auth=sales_only`、報表分析掛 `boss_only`（`apps/_common/roles.py`＝系統總覽 modules[].roles）；公開端點各自用 `auth=None` 明講。
- 系統總覽上每條原則、每條驗收，都要有一個測試守著；**測試函式名＝系統總覽的 id**（`test_create_ok`、`test_rule_sent_locked`）。

## 慣例

- 後端指令走 `uv run`（例：`uv run python manage.py check`），不要直接戳 `.venv/bin/python`。
- 新功能：`apps/<feature>/apis.py` 建 ninja `Router` → 到 `core/api.py` 加一行掛上去。
- 前端新頁：`src/views/` 加 `.vue` → `src/router/index.js` 加一筆 → 側欄 `AppShell.vue` 的 nav 照系統總覽的模組分群。
- 改了 `intents/系統總覽.json` 就重出頁：`node .claude/skills/system-overview/build.cjs intents/`。
- Commit：`type(scope): subject`，scope 用 `backend` / `admin` / `intents` / `infra`。

## 目錄

```
intents/           知識層：意圖清單、頁面清單、原型、系統總覽（先有這個，程式才長）
apps/lean-backend  Django-Ninja；core/ 設定與 API 註冊，apps/ 各功能（customers、products、quotations＝銷售管理；reports＝報表分析；accounts＝登入與角色）
apps/lean-admin    Vue3 + shadcn-vue 後台
infra/             部署
```
