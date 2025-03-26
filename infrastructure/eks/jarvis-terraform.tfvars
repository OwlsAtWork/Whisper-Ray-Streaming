# ------------------------------
# AWS REGION & ACCOUNT SETTINGS
# ------------------------------
aws_region       = "us-east-1"
aws_account_id   = "626635410672"  

# ------------------------------
# EKS CLUSTER CONFIGURATION
# ------------------------------
cluster_name                = "jarvis-kuberay-cluster"
cluster_version             = "1.32"
vpc_id                      = "vpc-00dae4de42d9c984a"  # Replace with your VPC ID
vpc_cidr                    = "10.10.0.0/16"            # CIDR range for the VPC
private_subnets             = [ "subnet-01f10c9c0ff74d0f2", "subnet-0caf84911b331f38c", "subnet-06cb3cc818ffb0036", "subnet-014f97f0e19a2036d" ]  # Replace with your subnet IDs
#cluster_security_group_id   = "sg-0abcd1234efgh5678"    # Replace with your security group ID
#cluster_iam_role_name       = "eks-cluster-role"        # Replace with your IAM role name

# ------------------------------
# EKS WORKER NODE CONFIGURATION
# ------------------------------
#worker_ami_id                = ""  # Replace with the EKS worker node AMI ID
worker_instance_type         = "t3.medium"
#worker_instance_profile_name = "eks-worker-profile"     # Replace with your instance profile name
asg_desired_capacity         = 2
#key_pair                     = "my-eks-keypair"         # Replace with your SSH key pair name
