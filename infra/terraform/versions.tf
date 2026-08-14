# Terraform 與 provider 版本鎖定。
# 鎖版本是「可重現基建」的基礎：同一份 code 在任何人機器上跑出同樣的 plan。
terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
