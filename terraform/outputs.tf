output "telemetry_bucket" {
  description = "Name of the S3 bucket for raw telemetry"
  value       = aws_s3_bucket.telemetry.bucket
}


output "queue_url" {
  description = "URL of the SQS ingest queue"
  value       = aws_sqs_queue.telemetry.url
}

output "poses_table" {
  description = "Name of the DynamoDB table for estimated poses"
  value       = aws_dynamodb_table.poses.name
}
