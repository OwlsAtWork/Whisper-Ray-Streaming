resource "aws_kms_key" "this" {

  policy = jsonencode({
          "Version": "2012-10-17",
    "Id": "key-consolepolicy-3",
    "Statement": [
        {
            "Sid": "Enable IAM User Permissions",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::${var.aws_account_id}:root"
            },
            "Action": "kms:*",
            "Resource": "*"
        },
        {
            "Sid": "Allow use of the key",
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    # "arn:aws:iam::${var.aws_account_id}:role/${var.cluster_name}-karpenter-r",
                    "arn:aws:iam::${var.aws_account_id}:role/${var.cluster_name}-worker-r"
                ]
            },
            "Action": [
                "kms:Encrypt",
                "kms:Decrypt",
                "kms:ReEncrypt*",
                "kms:GenerateDataKey*",
                "kms:DescribeKey"
            ],
            "Resource": "*"
        },
        {
            "Sid": "Allow attachment of persistent resources",
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    # "arn:aws:iam::${var.aws_account_id}:role/${var.cluster_name}-karpenter-r",
                    "arn:aws:iam::${var.aws_account_id}:role/${var.cluster_name}-worker-r"
                ]
            },
            "Action": [
                "kms:CreateGrant",
                "kms:ListGrants",
                "kms:RevokeGrant"
            ],
            "Resource": "*",
            "Condition": {
                "Bool": {
                    "kms:GrantIsForAWSResource": "true"
                }
            }
        }
    ]
  })
  tags = local.common_tags
}

resource "aws_kms_alias" "this" {
  name          = "${var.cluster_name}-kms"
  target_key_id = aws_kms_key.this.key_id
}