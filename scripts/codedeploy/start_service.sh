#!/usr/bin/env bash
set -xe
$(aws ecr get-login --no-include-email --region ap-southeast-2)
docker pull $UWSGI_IMAGE
cd /home/ec2-user/efs/trrf
docker-compose -f docker-compose-prod.yml up -d
