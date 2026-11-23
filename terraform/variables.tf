variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ca-central-1"
}

variable "project" {
  description = "Project name used as a prefix for resource names"
  type        = string
  default     = "capsule-tracker"
}
