module "eks_blueprints_addons" {
  source  = "aws-ia/eks-blueprints-addons/aws"
  version = "~> 1.19"

  cluster_name      = module.eks.cluster_name
  cluster_endpoint  = module.eks.cluster_endpoint
  cluster_version   = module.eks.cluster_version
  oidc_provider_arn = module.eks.oidc_provider_arn

  enable_kube_prometheus_stack = true

  helm_releases = {

    kuberay-operator = {
      namespace        = "kuberay-operator"
      create_namespace = true
      chart            = "kuberay-operator"
      chart_version    = "1.2.2"
      repository       = "https://ray-project.github.io/kuberay-helm/"
    }
  }
}
