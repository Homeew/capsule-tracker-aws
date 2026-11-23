# Private registry for the tracker worker image.
resource "aws_ecr_repository" "worker" {
  name         = "${var.project}-worker"
  force_delete = true # lets `terraform destroy` remove it even if images remain

  image_scanning_configuration {
    scan_on_push = true
  }
}
