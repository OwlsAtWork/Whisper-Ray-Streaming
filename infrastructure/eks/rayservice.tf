resource "kubernetes_secret" "pyannote_auth_token" {
  metadata {
    name      = "hf-token"
    namespace = "default" # replace with your desired namespace
  }

  data = {
    token = var.pyannote_auth_token
  }

  type = "Opaque"

  depends_on = [module.eks.eks_cluster_id]
}