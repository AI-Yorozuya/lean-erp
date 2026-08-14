# 所有可調參數集中在這。實際值放 terraform.tfvars（不進版控），
# 範例見 terraform.tfvars.example。

variable "project_name" {
  description = "資源命名前綴（對齊 repo 名）"
  type        = string
  default     = "lean-erp"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1" # Tokyo
}

variable "instance_type" {
  description = "EC2 機型（amd64）。教學用小台即可。"
  type        = string
  default     = "t3.small"
}

variable "key_name" {
  description = "AWS 既有的 EC2 Key Pair 名稱（用來 SSH 進機器）。先在 AWS console 建好 key pair 再填這裡。"
  type        = string
}

variable "ssh_cidr" {
  description = "允許 SSH(22) 進來的來源 CIDR。填你自己的對外 IP，查法：curl ifconfig.me"
  type        = string
  # 刻意不給預設值：沒填 terraform 就會問你，逼你想一次「誰可以連進這台機器」。

  validation {
    condition     = var.ssh_cidr != "0.0.0.0/0"
    error_message = "ssh_cidr 不能是 0.0.0.0/0——那等於全世界都能敲你的 22 port。填自己的 IP，例如 203.0.113.7/32（查法：curl ifconfig.me）。"
  }
}

variable "root_volume_size" {
  description = "根磁碟大小(GB)。留空間給 docker image + volume + log。"
  type        = number
  default     = 30
}

variable "enable_media_bucket" {
  description = "要不要開 S3 bucket 放上傳檔。v1 的三張表沒有任何上傳欄位，預設不開——少一個要管的東西、也少一筆帳單。真的要傳檔了再開。"
  type        = bool
  default     = false
}

variable "media_bucket_name" {
  description = "S3 bucket 名。⚠ bucket 名是【全世界共用】的，別人取過你就不能用——記得加自己的後綴，例如 lean-erp-media-你的名字。只有 enable_media_bucket = true 才需要填。"
  type        = string
  default     = ""
}
