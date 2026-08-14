# infra/terraform — 單一伺服器（教學版）

一份 flat 的 Terraform config：在 AWS 開 **一台 EC2 + 一個 security group(22/80/443)**，
機器開機自動裝好 docker，之後用 `infra/scripts/deploy.sh` 把 app 跑起來。

刻意 **不分 dev/prod、不拆 module** —— 看得懂 > 漂亮。

## 檔案

| 檔 | 內容 |
|----|------|
| `versions.tf` | terraform / aws provider 版本鎖定 |
| `variables.tf` | region / instance_type / key_name / ssh_cidr ... |
| `main.tf` | provider + security group + EC2（user_data 裝 docker） |
| `outputs.tf` | `public_ip`、`ssh_command` |
| `terraform.tfvars.example` | 範例值（複製成 `terraform.tfvars` 填實際值） |

## 用法（永遠 plan 先，review 後才 apply）

```bash
cp terraform.tfvars.example terraform.tfvars   # 填好 key_name / ssh_cidr
terraform init
terraform plan        # ← 一定先看 plan，確認要動的資源
# 人工 review plan，沒問題才：
terraform apply       # 會再問一次 yes/no
```

完成後 `terraform output public_ip` 拿到 IP。

## 鐵則（AI × 真雲）

- **預設只 `plan`，不 `apply`。** AI 直接對真雲 `apply` ≈ 新時代的「金鑰外洩 / 上線垮」：
  一個沒 review 的 plan 可能砍掉資料庫、改防火牆、噴帳單。**apply 是人按的。**
- **state 與機密永不進版控。** `.gitignore` 已擋 `*.tfstate*` / `.terraform/` / `*.tfvars`。
  tfstate 是明文，可能含敏感輸出 —— 外流等於把基建底牌給人。
- **憑證走環境變數**（`AWS_PROFILE` 或 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`），
  不寫進任何 `.tf` / `.tfvars` / repo。

## 憑證設定（本機）

```bash
export AWS_PROFILE=your-profile        # 建議：用 aws configure 設好 profile
# 或臨時：
# export AWS_ACCESS_KEY_ID=...
# export AWS_SECRET_ACCESS_KEY=...
```
