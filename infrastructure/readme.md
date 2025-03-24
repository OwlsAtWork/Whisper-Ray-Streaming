terraform init -backend-config="remote-backend/infra-terraform-backend-626635410672-us-east-1.config"
terraform plan -var-file="jarvis-terraform.tfvars"
terraform109 apply -var-file="variables/prod-eks-v2_variables.tfvars" # an error is expected here
export AWS_REGION=us-east-1
export CLUSTER_NAME=prod-eks-v2
aws eks update-kubeconfig --region us-east-1 --name ${CLUSTER_NAME}
export KUBECONFIG=~/.kube/config
export KUBE_CONFIG_PATH=$KUBECONFIG
terraform109 apply -var-file="variables/prod-eks-v2_variables.tfvars"