#!/usr/bin/env bash
set -x
mkdir -p /home/ec2-user/efs/trrf/data/log
chown -R ec2-user:ec2-user /home/ec2-user/efs/trrf
cd /home/ec2-user/efs/trrf

# TODO
# echo "UWSGI_IMAGE=126579111836.dkr.ecr.ap-southeast-2.amazonaws.com/eresearchqut/trrf2:latest" >> .env
echo "TRRF_VERSION=latest" >> .env

echo "DJANGO_FIXTURES=default" >> .env
echo "CSRF_TRUSTED_ORIGINS=.registryframework.net" >> .env
echo "IPRESTRICT_IGNORE_PROXY_HEADERS=1" >> .env

export AWS_DEFAULT_REGION=ap-southeast-2

echo UWSGI_IMAGE=`aws ecr describe-repositories --repository-name $APPLICATION_NAME | jq '.repositories | .[0] | .repositoryUri' -r` >> .env

export SSM_ENV_PATH=/app/${DEPLOYMENT_GROUP_NAME}/
export SSM_APP_PATH=/app/${DEPLOYMENT_GROUP_NAME}/${APPLICATION_NAME}/

aws ssm get-parameters-by-path --path ${SSM_ENV_PATH} --with-decryption | jq ".Parameters | .[] | [(.Name | ltrimstr(\"$SSM_ENV_PATH\")), .Value] | join(\"=\")" -r >> .env

aws ssm get-parameters-by-path --path ${SSM_APP_PATH} --with-decryption | jq ".Parameters | .[] | [(.Name | ltrimstr(\"$SSM_APP_PATH\")), .Value] | join(\"=\")" -r >> .env


