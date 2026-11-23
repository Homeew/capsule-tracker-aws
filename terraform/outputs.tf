output "telemetry_bucket" {
  description = "Name of the S3 bucket for raw telemetry"
  value       = aws_s3_bucket.telemetry.bucket
}

