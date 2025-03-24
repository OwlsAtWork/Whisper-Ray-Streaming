# ------------------------------
# AWS REGION & ACCOUNT SETTINGS
# ------------------------------

variable "aws_region" {
  description = "AWS region where the EKS cluster will be deployed"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID used for authentication"
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
  description = "CIDR block for the VPC"
  type        = string
}

variable "private_subnets" {
  description = "List of private subnets used for EKS worker nodes"
  type        = list(string)
}

variable "cluster_security_group_id" {
  description = "ID of the security group associated with the EKS cluster"
  type        = string
}

variable "cluster_iam_role_name" {
  description = "Name of the IAM role assigned to the EKS cluster"
  type        = string
}

# ------------------------------
# EKS WORKER NODE CONFIGURATION
# ------------------------------

variable "worker_ami_id" {
  description = "AMI ID for the EKS worker nodes"
  type        = string
}

variable "worker_instance_type" {
  description = "Instance type for the EKS worker nodes (e.g., t3.medium)"
  type        = string
  default     = "t3.medium"
}

variable "worker_instance_profile_name" {
  description = "Instance profile name for the EKS worker nodes"
  type        = string
}

variable "asg_desired_capacity" {
  description = "Desired capacity for the Auto Scaling Group (ASG)"
  type        = number
  default     = 2
}

variable "key_pair" {
  description = "Key pair name used to SSH into EKS worker nodes"
  type        = string
}