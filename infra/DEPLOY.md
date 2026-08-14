# infra/ — 部署 runbook（教學版）

三段式：先在 **本機 docker** 跑通 → 用 **Terraform** 開一台伺服器（plan→review→apply）→ 把 app **deploy** 上去。

> 鐵則先講：**AI 對真雲 `apply` 是新時代的「金鑰外洩 / 上線垮」**。
> 一個沒人 review 的 plan 可能砍資料庫、改防火牆、噴帳單。
> 所以：**永遠 `plan` 先、review 後人手 `apply`；state 與機密永不進版控；憑證走環境變數。**

---

## (1) 本機 docker（先在自己機器跑通）

後端 + DB + redis + celery worker（一個指令全起，與 prod 同構）：

```bash
docker compose -f infra/docker-compose.local.yml up --build
curl -s localhost:8000/api/v1/health    # {"status": "ok"}

# 試非同步任務：派工後輪詢進度，會看到 progress 0→100、status 變 SUCCESS。
JOB=$(curl -s -X POST localhost:8000/api/v1/progress/demo | sed -E 's/.*"id": *([0-9]+).*/\1/')
curl -s localhost:8000/api/v1/progress/$JOB
```

前端 dev server：

```bash
cd apps/lean-admin && npm install && npm run dev   # :5174
```

要在本機試「整套 prod 編排」（postgres + redis + backend + celery-worker + nginx）：

```bash
cp infra/.env.prod.example infra/.env.prod          # 填值
cd apps/lean-admin && npm ci && npm run build && cd -  # 先 build 前端
docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod up -d --build
curl -s localhost/api/v1/health
```

---

## (2) Terraform：開一台伺服器（plan → REVIEW → apply）

需求：本機裝好 terraform + AWS 憑證（`export AWS_PROFILE=...`，**別寫進檔案**）。

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # 填 key_name / ssh_cidr（建議鎖自己 IP/32）
terraform init
terraform plan                                 # ← 一定先看 plan
#  ↑↑↑ 人工 REVIEW：要新增/修改/刪除哪些資源？有沒有動到不該動的？
terraform apply                                # 確認無誤才執行，apply 還會再問一次 yes
terraform output public_ip                     # 拿到伺服器 IP
```

- **預設停在 `plan`。** `apply` 是人按的，不是 AI 自動跑的。
- state 檔（`*.tfstate`）會出現在這個資料夾 —— **已被 `.gitignore` 擋住，永不 commit**。

---

## (3) deploy app 到伺服器

把 repo 弄到伺服器（git clone 或 scp），在伺服器上：

```bash
cp infra/.env.prod.example infra/.env.prod     # 填正式值（強密碼 / SECRET_KEY / 網域）
bash infra/scripts/deploy.sh
```

`deploy.sh` 會：build admin 前端 → `docker compose -f infra/docker-compose.prod.yml up -d --build`
（起 postgres + redis + backend + **celery-worker** + nginx）→ `migrate`。redis 與 worker 是內部服務，不經 nginx。
驗證：

```bash
curl -s localhost/api/v1/health    # {"status": "ok"}
```

DNS：把網域 A record 指到 `terraform output public_ip`。
TLS：拿到憑證後依 `infra/nginx/nginx.conf` 末段說明開 443。

媒體檔（上傳）：prod 設 `USE_S3=True`，media 直接存/取 S3（`terraform output media_bucket_name`），
nginx **不** 服務 `/media`；本機開發 `USE_S3=False` 時 media 存本機 `/media`，由 Django(DEBUG) 服務。

---

## 機密 / state 紀律（再強調一次）

- **永不 commit**：`*.tfstate*`、`.terraform/`、`*.tfvars`、`infra/.env.prod`、任何 `.env`。
  （`.gitignore` 都已涵蓋；別手動 `git add -f` 繞過。）
- **憑證走環境變數**（`AWS_PROFILE` / `AWS_ACCESS_KEY_ID`...），不進 repo。
- **AI 不自動 `apply` 真雲**：plan 給人看，人決定。
