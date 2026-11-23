# Latest estimated capsule positions, one row per (capsule, timestamp).
resource "aws_dynamodb_table" "poses" {
  name         = "${var.project}-poses"
  billing_mode = "PAY_PER_REQUEST" # no idle cost

  hash_key  = "capsule_id"
  range_key = "t"

  attribute {
    name = "capsule_id"
    type = "S"
  }

  attribute {
    name = "t"
    type = "N"
  }
}
