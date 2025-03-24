# ------------------------------
# EKS CLUSTER CONFIGURATION
# ------------------------------

locals {
  common_tags = {
    "OBZ:Owner"                 = "devops",
    "OBZ:ManageBy"              = "Terraform",
    "karpenter.sh/discovery"    = "${var.cluster_name}",
    "CostCenter"                = "IT-Infra",
    "AccountID"                 = "${var.aws_account_id}"
  }
}
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.34.0" # Updated to the latest stable version

  cluster_name      = var.cluster_name
  cluster_version   = var.cluster_version
  vpc_id            = var.vpc_id
  subnet_ids        = var.private_subnets

  enable_irsa = true

  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = false
  enable_cluster_creator_admin_permissions = true

  create_node_security_group = false

  cluster_security_group_additional_rules = {
    hybrid-all = {
      cidr_blocks = [var.vpc_cidr]
      description = "Allow all traffic from remote node/pod network"
      from_port   = 0
      to_port     = 0
      protocol    = "all"
      type        = "ingress"
    }
  }

  #cluster_security_group_id     = var.cluster_security_group_id



  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  cluster_encryption_config = [
    {
      provider_key_arn = aws_kms_key.eks.arn
      resources        = ["secrets"]
    }
  ]

  self_managed_node_groups = {
    system = {
      ami_type      = "BOTTLEROCKET_x86_64"
      instance_type = "t3.medium"

      min_size = 2
      max_size = 3
      # This value is ignored after the initial creation
      # https://github.com/bryantbiggs/eks-desired-size-hack
      desired_size = 2
    #   iam_role_arn = ""
    #   iam_instance_profile_arn = ""

    #   # Additional settings
    #   additional_security_group_ids = [module.eks.cluster_security_group_id]
    #   create_security_group         = false

      # This is not required - demonstrates how to pass additional configuration
      # Ref https://bottlerocket.dev/en/os/1.19.x/api/settings/
      bootstrap_extra_args = <<-EOT
        # The admin host container provides SSH access and runs with "superpowers".
        # It is disabled by default, but can be disabled explicitly.
        [settings.host-containers.admin]
        enabled = false

        # The control host container provides out-of-band access via SSM.
        # It is enabled by default, and can be disabled if you do not expect to use SSM.
        # This could leave you with no way to access the API and change settings on an existing node!
        [settings.host-containers.control]
        enabled = true

        # extra args added
        [settings.kernel]
        lockdown = "integrity"
      EOT
    }
  }

  cluster_addons = {
    coredns                = {}
    kube-proxy             = {}
    vpc-cni                = {}
    aws-ebs-csi-driver     = {}
    aws-efs-csi-driver     = {}
    amazon-cloudwatch-observability ={}

  }

  tags = local.common_tags       
}

# ------------------------------
# KMS ENCRYPTION CONFIGURATION
# ------------------------------
resource "aws_kms_key" "eks" {
  description             = "${var.cluster_name}-eks-secrets-encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  tags                    = local.common_tags 

}

resource "aws_kms_alias" "eks" {
  name          = "alias/${var.cluster_name}-eks-key"
  target_key_id = aws_kms_key.eks.key_id
}


