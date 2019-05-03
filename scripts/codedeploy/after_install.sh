#!/usr/bin/env bash
set -x
mkdir -p /home/ec2-user/efs/trrf/data/prod/log
chown -R ec2-user:ec2-user /home/ec2-user/efs/trrf
cd /home/ec2-user/efs/trrf

# TODO
# echo "UWSGI_IMAGE=126579111836.dkr.ecr.ap-southeast-2.amazonaws.com/eresearchqut/trrf2:latest" >> .env
echo "TRRF_VERSION=latest" >> .env

echo "DJANGO_FIXTURES=default" >> .env
echo "CSRF_TRUSTED_ORIGINS=.registryframework.net" >> .env
echo "IPRESTRICT_IGNORE_PROXY_HEADER=1" >> .env

export AWS_DEFAULT_REGION=ap-southeast-2

export UWSGI_IMAGE=`aws ecr describe-repositories --repository-name $APPLICATION_NAME | jq '.repositories | .[0] | .repositoryUri' -r`
echo "UWSGI_IMAGE=$UWSGI_IMAGE" >> .env

export SSM_ENV_PATH=/app/${DEPLOYMENT_GROUP_NAME}/
export SSM_APP_PATH=/app/${DEPLOYMENT_GROUP_NAME}/${APPLICATION_NAME}/

aws ssm get-parameters-by-path --path ${SSM_ENV_PATH} --with-decryption | jq ".Parameters | .[] | [(.Name | ltrimstr(\"$SSM_ENV_PATH\")), .Value] | join(\"=\")" -r >> .env

aws ssm get-parameters-by-path --path ${SSM_APP_PATH} --with-decryption | jq ".Parameters | .[] | [(.Name | ltrimstr(\"$SSM_APP_PATH\")), .Value] | join(\"=\")" -r >> .env

# TODO collecstatic should happen when the image is built after we switch to storing static files in S3
docker-compose -f docker-compose-prod.yml run uwsgi /docker-entrypoint.sh django-admin collectstatic --noinput
docker-compose -f docker-compose-prod.yml run uwsgi /docker-entrypoint.sh django-admin migrate --noinput

# TODO this should happen in a DB init script that also creates the DBs if necessary
# docker-compose -f docker-compose-prod.yml run uwsgi django_admin.py init users iprestrict_permissive
