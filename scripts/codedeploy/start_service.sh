#!/usr/bin/env bash
set -xe

export AWS_DEFAULT_REGION=ap-southeast-2
export ECR_ACCOUNT_ID=$(aws ssm get-parameter --name ECR-ACCOUNT-ID | jq -r .Parameter.Value)
export TRRF_NGINX_PROXY=$(aws ssm get-parameter --name TRRF-NGINX-PROXY | jq -r .Parameter.Value)
export ECR_URL="${ECR_ACCOUNT_ID}.dkr.ecr.ap-southeast-2.amazonaws.com"

$(aws ecr get-login --no-include-email --registry-ids ${ECR_ACCOUNT_ID})

# TODO TRRF_VERSION should probably appended to this here
export UWSGI_IMAGE="${ECR_URL}/${APPLICATION_NAME}"
export NGINX_DOCKER_IMAGE="${ECR_URL}/${TRRF_NGINX_PROXY}"

docker pull $UWSGI_IMAGE

cd /home/ec2-user/trrf
docker-compose -f docker-compose-prod.yml up -d
