GIT_ROOT := $(shell git rev-parse --show-toplevel)
INFRA_ROOT := $(GIT_ROOT)/infra
JARVIS_INFRA_ROOT := $(GIT_ROOT)/infrastructure/workload/rayservice
VERSION ?= local
RELEASE_VERSION ?= v1
TF_INFRA_ROOT := $(INFRA_ROOT)
ECR_REPO_BASE_URL = 626635410672.dkr.ecr.us-east-1.amazonaws.com
WHISPER_RAY_SERVICE_REPO_URL = $(ECR_REPO_BASE_URL)/whisper-ray-service
EKS_CLUSTER_NAME := kuberay-cluster
REGION = us-east-1
TARGET_ZIP=whisper-ray-service.zip
SOURCE_FILES=.
VOICE_KUBERAY_CLUSTER_NAME := voice-kuberay-cluster

ecr-login:
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(ECR_REPO_BASE_URL)

set-jarvis-kubectl-context:
	aws eks update-kubeconfig --region $(REGION) --name $(EKS_CLUSTER_NAME)

set-voice-kuberay-context:
	aws eks update-kubeconfig --region $(REGION) --name $(VOICE_KUBERAY_CLUSTER_NAME)

build-ray-service:
	docker build --platform linux/amd64 --no-cache -t whisper-ray-service:$(VERSION) .

push-docker-whisper-ray-service:
	docker tag whisper-ray-service:$(VERSION) $(WHISPER_RAY_SERVICE_REPO_URL):$(RELEASE_VERSION)
	docker push $(WHISPER_RAY_SERVICE_REPO_URL):$(RELEASE_VERSION)

build-push-ray-service: build-ray-service push-docker-whisper-ray-service

deploy-ray-service:
	kubectl apply -f $(GIT_ROOT)/Whisper-RayService.yaml

undeploy-ray-service:
	kubectl delete -f $(GIT_ROOT)/Whisper-RayService.yaml


run-ray-service:
	python -m src.voice_stream_ai_server

stop-ray-service:
	ray stop

start-ray-service:
	ray start --head

deploy-jarvis-ray-service:
	kubectl apply -f $(JARVIS_INFRA_ROOT)/stack.yaml

undeploy-jarvis-ray-service:
	kubectl delete -f $(JARVIS_INFRA_ROOT)/stack.yaml

create_zip:
	@echo "Creating ZIP file: $(TARGET_ZIP)"
	@zip -r "$(TARGET_ZIP)" . -x "infra*/*" ".git/*" ".venv/*"
 
rename_and_upload_to_s3:
	@hash=$$(sha256sum "$(TARGET_ZIP)" | awk '{print $$1}'); \
	new_name="$$hash.zip"; \
	mv "$(TARGET_ZIP)" "$$new_name"; \
	echo "Renamed $(TARGET_ZIP) to $$new_name"; \
	aws s3 cp "$$new_name" s3://jarvis-whisper/"$$new_name"; \
	echo "https://jarvis-whisper.s3.us-east-1.amazonaws.com/$$new_name"; \
	rm "$$new_name" && echo "Deleted $$new_name"


create_and_rename_and_upload_to_s3: create_zip rename_and_upload_to_s3

