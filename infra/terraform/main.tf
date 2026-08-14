# 一個 flat config：provider + 一個 security group + 一台 EC2。
# 刻意不分 dev/prod、不拆 module —— 教學用，看得懂最重要。

provider "aws" {
  region = var.aws_region
}

# 取最新的 Ubuntu 24.04 (amd64) AMI，不用手動查 AMI id。
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical 官方帳號

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── Security Group：只開三個 port ───────────────────────────────
# 22 (SSH，鎖來源)、80 / 443 (給 nginx)。其餘一律擋。
resource "aws_security_group" "app" {
  name        = "${var.project_name}-sg"
  description = "lean-stack single-server: SSH + HTTP + HTTPS"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_cidr]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name      = "${var.project_name}-sg"
    ManagedBy = "Terraform"
  }
}

# ── EC2：一台機器，開機自動裝好 docker，等你 deploy ───────────────
resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.app.id]

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    delete_on_termination = true
  }

  # user_data：開機只負責「把 docker 裝好」。
  # 應用程式本身不在這裡跑 —— 由你之後手動跑 infra/scripts/deploy.sh
  # （把 build/migrate/up 的時機握在自己手上，比較好教也比較安全）。
  user_data = <<-EOF
    #!/bin/bash
    set -e
    apt-get update
    apt-get install -y ca-certificates curl git
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
      > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    usermod -aG docker ubuntu
    # 之後：scp 專案上來 → 跑 infra/scripts/deploy.sh
    #   docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod up -d --build
  EOF

  tags = {
    Name      = var.project_name
    ManagedBy = "Terraform"
  }
}

# ── S3：media 上傳用 bucket（預設私有）──────────────────────────
# prod 透過 backend 的 USE_S3=True + AWS_STORAGE_BUCKET_NAME 使用這個 bucket；
# 憑證走 EC2 instance role（或環境變數），不寫進 code。
# 安全預設：擋掉所有 public access，物件只能靠 IAM / signed URL 取用。
resource "aws_s3_bucket" "media" {
  bucket = var.media_bucket_name

  tags = {
    Name      = "${var.project_name}-media"
    ManagedBy = "Terraform"
  }
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
