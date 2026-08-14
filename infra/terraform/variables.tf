# 所有可調參數集中在這。實際值放 terraform.tfvars（不進版控），
# 範例見 terraform.tfvars.example。

variable "project_name" {
  description = "資源命名前綴（對齊 repo 名 lean-stack）"
  type        = string
  default     = "lean-stack"
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
  description = "允許 SSH(22) 進來的來源 CIDR。強烈建議鎖成你自己的 IP/32，別用 0.0.0.0/0。"
  type        = string
  default     = "0.0.0.0/0"
}

variable "root_volume_size" {
  description = "根磁碟大小(GB)。留空間給 docker image + volume + log。"
  type        = number
  default     = 30
}

variable "media_bucket_name" {
  description = "media 上傳用的 S3 bucket 名（全球唯一）。對齊 backend 的 AWS_STORAGE_BUCKET_NAME。"
  type        = string
  default     = "lean-stack-media"
}
