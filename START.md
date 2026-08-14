# 開始前：環境設定

> **已經有 Claude Code、Docker、GitHub 帳號的人請跳過這頁**，直接看 [README](README.md)。
> 這頁是一次性的設定，大概半小時。裝完就不用再碰。

## 你不必懂的事

docker、git、npm 這些是 **Claude 的工作，不是你的**。這頁只要求你「照著做得到」，不要求你「懂為什麼」——願意先不求甚解，是這條路上最省時間的態度。

## 三件事

### 1. Claude Code

需要 Claude 付費訂閱。安裝方式看官方文件（會變，以官方為準）：<https://docs.claude.com/en/docs/claude-code>

**確認裝好了**：終端機打

```bash
claude --version
```

有版本號就成功。

### 2. Docker Desktop

<https://www.docker.com/products/docker-desktop/> 下載安裝，開啟它，等到鯨魚圖示不再轉。

**確認裝好了**：

```bash
docker compose version
```

有版本號就成功。

> 卡住最常見的原因：裝好了但沒**打開** Docker Desktop。它要在背景跑著。

### 3. GitHub 帳號

<https://github.com/signup>。這一步只是為了把程式碼拿下來、之後存得回去。

**確認可以用**：

```bash
git --version
```

## 把系統跑起來

```bash
git clone https://github.com/AI-Yorozuya/lean-erp.git
cd lean-erp
docker compose -f infra/docker-compose.local.yml up --build
```

第一次會下載一堆東西，慢是正常的。跑完之後另開一個終端機：

```bash
curl -s localhost:8000/api/v1/health
```

看到 `{"status": "ok"}` 就是成功了。前端：

```bash
cd apps/lean-admin && npm install && npm run dev
```

瀏覽器開它印出來的網址（預設 <http://localhost:5174>）。

## 過關檢查

四個都打勾就可以開始了：

- [ ] `claude --version` 有版本號
- [ ] `docker compose version` 有版本號
- [ ] `curl localhost:8000/api/v1/health` 回 `{"status": "ok"}`
- [ ] 瀏覽器打得開後台首頁

## 卡住怎麼辦

**先問 Claude**——把終端機上的錯誤訊息整段貼給它，講你剛做了什麼。這不只是解法，也是這門課要練的第一個反射：**覺得雜，先問 Claude**。

還是過不了就帶著錯誤訊息來門診。**這關卡住不是你的問題**，環境問題本來就該有人接。
