#!/usr/bin/env bash
set -xe
$(aws ecr get-login --no-include-email --region ap-southeast-2)

export UWSGI_IMAGE=`aws ecr describe-repositories --repository-name $APPLICATION_NAME | jq '.repositories | .[0] | .repositoryUri' -r`

docker pull $UWSGI_IMAGE

cd /home/ec2-user/efs/trrf
docker-compose -f docker-compose-prod.yml up -d
