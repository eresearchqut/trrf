#!/usr/bin/env bash
set -xe
cd /home/ec2-user/trrf
docker-compose -f docker-compose-prod.yml stop
