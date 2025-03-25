
# ------------------------------
# CLUSTER ROLE
# ------------------------------
resource "aws_iam_role" "cluster-role" {
  name               = "${var.cluster_name}-cluster-r"
  
  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EKSClusterAssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "eks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
})
  managed_policy_arns = [
        "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy","arn:aws:iam::aws:policy/AmazonEKSServicePolicy",
        "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController","arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess"
    ]


  tags = {
      "karpenter.sh/discovery" = "prod-eks-sophi-v2"
      "Sophi:Owner" = "devops",
      "Sophi:Creation" = "scheduled"
  }
}
# ------------------------------
# WORKER NODE ROLE
# ------------------------------
resource "aws_iam_role" "worker-role" {
  name               = "${var.cluster_name}-worker-r"
  
  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EKSWorkerAssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
})
  managed_policy_arns = [
      "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy","arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
      "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore","arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
      "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
      ]


  tags = local.common_tags
}

resource "aws_iam_instance_profile" "worker-i" {
  name = "${var.cluster_name}-worker-i"
  role = aws_iam_role.worker-role.name

  tags = local.common_tags
}


# ------------------------------
# KARPENTER POLICY AND ROLE
# ------------------------------

resource "aws_iam_policy" "karpenter-p" {
  name        = "${var.cluster_name}-karpenter-p"
 
  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  policy = jsonencode({
    "Statement": [
        {
            "Action": [
                "ec2:CreateLaunchTemplate",
                "ec2:CreateFleet",
                "ec2:RunInstances",
                "ec2:CreateTags",
                "iam:PassRole",
                "ec2:TerminateInstances",
                "ec2:DescribeLaunchTemplates",
                "ec2:DeleteLaunchTemplate",
                "ec2:DescribeInstances",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeSubnets",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeInstanceTypeOfferings",
                "ec2:DescribeAvailabilityZones",
                "ec2:DescribeSpotPriceHistory",
                "ssm:GetParameter",
                "pricing:DescribeServices",
                "pricing:GetAttributeValues",
                "pricing:GetProducts",
                "ec2:Describe*",
                "eks:Describe*",
                "eks:Get*",
                "kms:ListKeys",
                "kms:DescribeKey",
                "kms:DescribeCustomKeyStores",
                "kms:GetPublicKey"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ],
    "Version": "2012-10-17"
})

  tags = local.common_tags

}


resource "aws_iam_role" "karpenter-r" {
  name               = "${var.cluster_name}-karpenter-r"
  
  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Principal": {
                "Federated": module.eks.oidc_provider_arn
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub": "sts.amazonaws.com",
                    "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub": "system:serviceaccount:karpenter:karpenter"
                }
            }
        }
    ]
})
  managed_policy_arns = [aws_iam_policy.karpenter-p.arn]

  tags = local.common_tags
}
