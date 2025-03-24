# resource "aws_iam_role" "this" {
#   name   = "${var.cluster_name}-cluster-r"
#   assume_role_policy = jsonencode({
#     "Version": "2012-10-17",
#     "Statement": [
#         {
#             "Sid": "EKSClusterAssumeRole",
#             "Effect": "Allow",
#             "Principal": {
#                 "Service": "eks.amazonaws.com"
#             },
#             "Action": "sts:AssumeRole"
#         }
#     ]
# })

#   description = ""
#   managed_policy_arns = []
#   tags = local.common_tags
# }
