# 部署 runbook

三段：先在**本機**跑通 → 用 **Terraform** 開一台機器 → 把 app **deploy** 上去。

> **鐵則先講**：AI 對真雲 `apply` 是新時代的「金鑰外洩／上線垮」。一個沒人看過的 plan 可能砍掉資料庫、改掉防火牆、噴出帳單。
> 所以：**永遠先 `plan`、人看過才 `apply`；state 與機密永不進版控；憑證走環境變數。**

---

## (1) 本機先跑通

開發用（後端 + DB + redis + worker，一個指令全起）：

```bash
docker compose -f infra/docker-compose.local.yml up --build
curl -s localhost:8000/api/v1/health    # {"status": "ok"}
```

前端 dev server：

```bash
cd apps/lean-admin && npm install && npm run dev   # :5174
```

要在本機試「整套正式編排」（postgres + redis + backend + worker + Caddy）：

```bash
cp infra/.env.prod.example infra/.env.prod            # 填值；SITE_ADDRESS 留空＝本機純 HTTP
cd apps/lean-admin && npm ci && npm run build && cd -  # 先 build 前端
docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod up -d --build
curl -s localhost/api/v1/health                        # {"status": "ok"}
```

> `ALLOWED_HOSTS` 要包含你連進來用的網域（本機就是 `localhost`），否則後端會回 400。

---

## (2) Terraform：開一台機器（plan → 你看過 → apply）

需求：本機裝好 terraform，AWS 憑證走環境變數（`export AWS_PROFILE=...`，**別寫進檔案**）。

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # 填 key_name 與 ssh_cidr
terraform init
terraform plan                                 # ← 一定先看
#  ↑↑↑ 人工檢查：要新增/修改/刪除哪些資源？有沒有動到不該動的？
terraform apply                                # 確認無誤才執行，apply 還會再問一次
terraform output public_ip
```

**ssh_cidr 沒有預設值**，terraform 會問你——這是刻意的，逼你想一次「誰可以連進這台機器」。填 `0.0.0.0/0` 會被擋下來。查自己的 IP：`curl ifconfig.me`。

**不用的時候關掉**：`terraform destroy`。這是**正常操作**不是急救——設定都在 repo 裡，明天 `apply` 一次就全回來。機器留著就是每天在算錢。

**先設預算警示**：AWS Console → Billing → Budgets，設一個你能接受的金額。忘了關機器是新手最常見的意外帳單。

---

## (3) deploy 到機器上

把 repo 弄到機器上（git clone），然後：

```bash
cp infra/.env.prod.example infra/.env.prod   # 填正式值：強密碼、SECRET_KEY、網域
bash infra/scripts/deploy.sh
```

`deploy.sh` 會 build 前端 → 起整套 compose → 跑 migrate。

**網域與 HTTPS**：

1. DNS 加一筆 A record 指到 `terraform output public_ip`。
   **Cloudflare 的話請設 DNS-only（灰雲）** —— 開了代理會擋掉憑證申請。
2. `infra/.env.prod` 裡把 `SITE_ADDRESS` 填成你的網域，`ALLOWED_HOSTS` 也要含它。
3. 重跑 `deploy.sh`。

Caddy 會自己去申請憑證、到期前自己續期——**沒有 certbot、沒有 cron、沒有續期後要 reload 的步驟**。憑證存在 `caddy-data` volume 裡，別隨手把 volume 砍了（重申請會撞 Let's Encrypt 的速率限制）。

驗證：

```bash
curl -s https://你的網域/api/v1/health    # {"status": "ok"}
```

---

## 機密與 state 紀律

- **永不 commit**：`*.tfstate*`、`.terraform/`、`*.tfvars`、`infra/.env.prod`、任何 `.env`。`.gitignore` 都涵蓋了，別用 `git add -f` 繞過。
- **憑證走環境變數**（`AWS_PROFILE` / `AWS_ACCESS_KEY_ID`…），不進 repo、不貼進對話框。
- **AI 不自動 `apply` 真雲**：plan 給人看，人決定。
