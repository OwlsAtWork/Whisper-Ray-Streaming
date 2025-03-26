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

data "aws_ami" "bottlerocket_ami" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["bottlerocket-aws-k8s-${var.cluster_version}-x86_64-*"]
  }
}

resource "random_string" "suffix" {
  length  = 8
  special = false
}


resource "tls_private_key" "nodes" {
  algorithm = "RSA"
}

resource "aws_key_pair" "nodes" {
  key_name   = "bottlerocket-nodes-${random_string.suffix.result}"
  public_key = tls_private_key.nodes.public_key_openssh
}


# https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/17.24.0
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "17.24.0" # <18

  cluster_version = var.cluster_version
  cluster_name    = var.cluster_name
  vpc_id          = var.vpc_id
  subnets         = var.private_subnets
  enable_irsa     = true

  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = false

  cluster_create_security_group = false
  cluster_security_group_id     = aws_security_group.cluster-sg.id

  manage_cluster_iam_resources = false
  cluster_iam_role_name        = aws_iam_role.cluster-role.name

  manage_worker_iam_resources = false

  cluster_enabled_log_types = ["audit", "api", "authenticator", "controllerManager", "scheduler"]

  cluster_encryption_config = [
    {
      provider_key_arn = aws_kms_key.this.arn
      resources        = ["secrets"]
    }
  ]


  # https://github.com/terraform-aws-modules/terraform-aws-eks/blob/e90c877a741ab3cc4215376a70f7bcc360b6a3d2/examples/bottlerocket/main.tf#L31
  # https://github.com/terraform-aws-modules/terraform-aws-eks/blob/e90c877a741ab3cc4215376a70f7bcc360b6a3d2/locals.tf#L36
  worker_groups_launch_template = [
    # this is recreated when running `terraform apply`, meaning this does not scale
    {
      name                                  = "bottlerocket-nodes"
      ami_id                                = data.aws_ami.bottlerocket_ami.id  #var.worker_ami_id
      instance_type                         = var.worker_instance_type
      iam_instance_profile_name             = "${var.cluster_name}-worker-i"

      asg_desired_capacity                  = var.asg_desired_capacity
      key_name                              = aws_key_pair.nodes.key_name

      public_ip = false

      userdata_template_file                = "${path.module}/userdata.toml"
      metadata_http_endpoint                = "enabled"  # The state of the metadata service: enabled, disabled.
      metadata_http_tokens                  = "required" # If session tokens are required: optional, required.
      metadata_http_put_response_hop_limit  = 2          # The desired HTTP PUT response hop limit for instance metadata requests.
      userdata_template_extra_args = {
        enable_admin_container   = false
        enable_control_container = true
        aws_region               = var.aws_region
      }
      # example of k8s/kubelet configuration via additional_userdata
      additional_userdata = <<EOT
[settings.kubernetes.node-labels]
ingress = "allowed"
EOT
    }
  ]

  tags = local.common_tags

  depends_on = [ 
    aws_iam_role.cluster-role,
    aws_iam_role.worker-role,
    aws_iam_instance_profile.worker-i,
    aws_kms_key.this,
    aws_security_group.cluster-sg
    
   ]
}
