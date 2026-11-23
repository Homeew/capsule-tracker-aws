# Ingest buffer between the sensor simulator and the tracker.
resource "aws_sqs_queue" "telemetry" {
  name                      = "${var.project}-telemetry"
  message_retention_seconds = 86400 # keep unread messages for 24 h
  receive_wait_time_seconds = 10    # long polling
}
