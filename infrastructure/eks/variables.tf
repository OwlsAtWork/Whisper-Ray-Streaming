# ------------------------------
# AWS REGION & ACCOUNT SETTINGS
# ------------------------------
variable "aws_region" {
  description = "The AWS region for the EKS cluster"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

# ------------------------------
# EKS CLUSTER CONFIGURATION
# ------------------------------
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.31"
}

variable "vpc_id" {
  description = "VPC ID where the EKS cluster will be deployed"
  type        = string
}

variable "vpc_cidr" {
}

variable "private_subnets" {
  description = "List of private subnets for EKS nodes"
  type        = list(string)
}

# variable "cluster_security_group_id" {
#   description = "Security group ID for the EKS cluster"
#   type        = string
# }

