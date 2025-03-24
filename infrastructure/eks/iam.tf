
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


# # ------------------------------
# # KARPENTER ROLE
# # ------------------------------
# resource "aws_iam_role" "karpenter-r" {
#   name               = "${var.cluster_name}-karpenter-r"
  
#   assume_role_policy = jsonencode({
#     "Version": "2012-10-17",
#     "Statement": [
#         {
#             "Sid": "",
#             "Effect": "Allow",
#             "Principal": {
#                 "Federated": module.eks.oidc_provider_arn
#             },
#             "Action": "sts:AssumeRoleWithWebIdentity",
#             "Condition": {
#                 "StringEquals": {
#                     "oidc.eks.us-east-1.amazonaws.com/id/:sub": "sts.amazonaws.com",
#                     "oidc.eks.us-east-1.amazonaws.com/id/8D445462AD6CC9528EBE85A030A4BB22:sub": "system:serviceaccount:karpenter:karpenter"
#                 }
#             }
#         }
#     ]
# })
#   managed_policy_arns = []

#   tags = local.common_tags
# }