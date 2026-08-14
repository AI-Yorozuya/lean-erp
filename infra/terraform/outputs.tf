output "public_ip" {
  description = "EC2 公開 IP — SSH 跟 DNS A record 都指這個。"
  value       = aws_instance.app.public_ip
}

output "ssh_command" {
  description = "方便複製的 SSH 指令（記得換成你的 .pem 路徑）。"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.app.public_ip}"
}

output "media_bucket_name" {
  description = "media S3 bucket 名 — 填到 backend 的 AWS_STORAGE_BUCKET_NAME。"
  value       = aws_s3_bucket.media.bucket
}
