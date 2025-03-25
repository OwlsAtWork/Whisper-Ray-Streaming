output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_oidc_issuer_url" {
  description = "OIDC issuer URL for IRSA"
  value       = module.eks.cluster_oidc_issuer_url
}

output "eks_cluster_oidc_issuer_arn" {
  value = module.eks.oidc_provider_arn
}

output "oidc_provider_stripped" {
  description = "OIDC provider URL without https://"
  value       = replace(module.eks.cluster_oidc_issuer_url, "https://", "")
}