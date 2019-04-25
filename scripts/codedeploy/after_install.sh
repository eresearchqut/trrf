#!/usr/bin/env bash
set -x
mkdir -p /home/ec2-user/efs/trrf/data/log
chown -R ec2-user:ec2-user /home/ec2-user/efs/trrf
cd /home/ec2-user/efs/trrf

# TODO
# export UWSGI_IMAGE=$IMAGE_REPO:$APPLICATION_VERSION

echo "UWSGI_IMAGE=126579111836.dkr.ecr.ap-southeast-2.amazonaws.com/eresearchqut/trrf2:latest" >> .env
# echo "TRRF_VERSION=1.0.0" >> .env
# echo "DJANGO_FIXTURES=default" >> .env

echo UWSGI_IMAGE=`aws ecr describe-repositories --repository-name $APPLICATION_NAME | jq '.repositories | .[0] | .repositoryUri'` >> .env


export SSM_PATH=/${DEPLOYMENT_GROUP_NAME}/${APPLICATION_NAME}/

aws --profile r4 ssm get-parameters-by-path --path ${SSM_PATH} --with-decryption | jq ".Parameters | .[] | [(.Name | ltrimstr(\"$SSM_PATH\")), .Value] | join(\"=\")" -r

# TODO update path and make it work based on the environment and project name
#aws ssm get-parameters-by-path --path /app/eresearchqut/trrf --with-decryption | jq '.Parameters | .[] | [(.Name | ltrimstr("/app/eresearchqut/trrf/")), .Value] | join("=")' -r >> .env

# source .env
# source .env_from_ssm


