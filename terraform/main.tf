data "aws_caller_identity" "current" {}

locals {
  bucket_name = "${var.project}-telemetry-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "telemetry" {
  bucket = local.bucket_name

  tags = {
    Project = var.project
  }
}

resource "aws_s3_bucket_public_access_block" "telemetry" {
  bucket = aws_s3_bucket.telemetry.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
