export KUBECONFIG=~/.kube/config
export KUBE_CONFIG_PATH=$KUBECONFIG
export AWS_REGION=us-east-1
export CLUSTER_NAME=jarvis-kuberay-cluster
aws eks update-kubeconfig --region us-east-1 --name ${CLUSTER_NAME}

./terraform init -backend-config="remote-backend/infra-terraform-backend-626635410672-us-east-1.config"
./terraform plan -var-file="jarvis-terraform.tfvars"

export KARPENTER_VERSION=1.3.3
export KARPENTER_NAMESPACE=karpenter
export CLUSTER_NAME=jarvis-kuberay-cluster
export KARPENTER_IAM_ROLE_ARN="arn:aws:iam::626635410672:role/jarvis-kuberay-cluster-karpenter-r"


helm upgrade --install karpenter oci://public.ecr.aws/karpenter/karpenter --version "${KARPENTER_VERSION}" --namespace "${KARPENTER_NAMESPACE}" --create-namespace   --set "settings.clusterName=${CLUSTER_NAME}" --set controller.resources.requests.cpu=1 --set controller.resources.requests.memory=1Gi --set controller.resources.limits.cpu=1 --set controller.resources.limits.memory=1Gi  --set "serviceAccount.annotations.eks\.amazonaws\.com/role-arn=${KARPENTER_IAM_ROLE_ARN}"


