#!/usr/bin/env bash
set -x
mkdir -p /home/ec2-user/efs/trrf/data/log
chown -R ec2-user:ec2-user /home/ec2-user/efs/trrf
cd /home/ec2-user/efs/trrf
source .env

# TODO
# export UWSGI_IMAGE=$IMAGE_REPO:$APPLICATION_VERSION
export UWSGI_IMAGE=126579111836.dkr.ecr.ap-southeast-2.amazonaws.com/eresearchqut/trrf2:latest
export TRRF_VERSION=1.0.0
export DJANGO_FIXTURES=default

# TODO update path and make it work based on the environment and project name
aws --profile ssm get-parameters-by-path --path /app/eresearchqut/trrf --with-decryption | jq '.Parameters | .[] | [(.Name | ltrimstr("/app/eresearchqut/trrf/")), .Value] | join("=")' -r > .env_from_ssm

source .env_from_ssm


