# lean-erp — AI 助理指引

報價成交切片：**客戶 → 報價單 → 訂單**。骨架來自 lean-stack（Django-Ninja + Vue3），domain 是這個 repo 自己的。

## 動工前先讀

**不知道該幹嘛就打 `/next`**——它會判斷專案走到哪一站（意圖→架構→規格→施工），帶你走下一步。

1. `intents/架構圖.md` —— 整個系統一頁：資料·流程·頁面·原則。**每次動工先看全貌。**
2. `intents/建立報價單.md` —— 要蓋哪一塊，就讀那一塊的規格書。

**規則**：新需求不要直接改 code——先問它長在架構圖的哪裡（新的東西？新狀態？撞到哪條原則？），改完圖再切一塊施工。

## 紅線

- **零真實資料**。這是公開 repo，資料一律 seed 假資料；`.env` 永不進版控。
- **總額不存欄位**、不接受輸入——由明細現算（架構圖原則 1）。
- **報價不碰帳**：quotation 不 import 帳務相關模組，靠結構保證，不靠 if。
- 架構圖上每條原則，最後都要有一個測試守著。

## 慣例

- 後端指令走 `uv run`（例：`uv run python manage.py check`），不要直接戳 `.venv/bin/python`。
- 新功能：`apps/<feature>/apis.py` 建 ninja `Router` → 到 `core/api.py` 加一行掛上去。
- 前端新頁：`src/views/` 加 `.vue` → `src/router/index.js` 加一筆 → 需要的話再上側欄 `AppShell.vue`。
- Commit：`type(scope): subject`，scope 用 `backend` / `admin` / `intents` / `infra`。

## 目錄

```
intents/           知識層：架構圖＋各塊規格書（先有這個，程式才長）
apps/lean-backend  Django-Ninja；core/ 設定與 API 註冊，apps/ 各功能
apps/lean-admin    Vue3 + shadcn-vue 後台
infra/             部署
```
