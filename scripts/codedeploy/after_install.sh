#!/usr/bin/env bash
set -x
mkdir -p /home/ec2-user/trrf/data/prod/log
chown -R ec2-user:ec2-user /home/ec2-user/trrf
cd /home/ec2-user/trrf

export AWS_DEFAULT_REGION=ap-southeast-2

export ECR_ACCOUNT_ID=$(aws ssm get-parameter --name /app/dev/ECR_ACCOUNT_ID | jq -r .Parameter.Value)
export ECR_URL="${ECR_ACCOUNT_ID}.dkr.ecr.ap-southeast-2.amazonaws.com"

$(aws ecr get-login --no-include-email --registry-ids ${ECR_ACCOUNT_ID})

# TODO TRRF_VERSION should probably appended to this here
export UWSGI_IMAGE="${ECR_URL}/${APPLICATION_NAME}"

echo "AWS_DEFAULT_REGION=ap-southeast-2" >> .env
echo "UWSGI_IMAGE=$UWSGI_IMAGE" >> .env
echo "ENVIRONMENT=${DEPLOYMENT_GROUP_NAME}"  >> .env
echo "APPLICATION_NAME=${APPLICATION_NAME}"  >> .env

export SSM_ENV_PATH=/app/${DEPLOYMENT_GROUP_NAME}/
export SSM_APP_PATH=/app/${DEPLOYMENT_GROUP_NAME}/${APPLICATION_NAME}/

aws ssm get-parameters-by-path --path ${SSM_ENV_PATH} --with-decryption | jq ".Parameters | .[] | [(.Name | ltrimstr(\"$SSM_ENV_PATH\")), .Value] | join(\"=\")" -r >> .env

aws ssm get-parameters-by-path --path ${SSM_APP_PATH} --with-decryption | jq ".Parameters | .[] | [(.Name | ltrimstr(\"$SSM_APP_PATH\")), .Value] | join(\"=\")" -r >> .env

docker-compose -f docker-compose-prod.yml pull

# TODO collecstatic should happen when the image is built after we switch to storing static files in S3
docker-compose -f docker-compose-prod.yml run uwsgi /docker-entrypoint.sh django-admin collectstatic --noinput

docker-compose -f docker-compose-prod.yml run uwsgi /docker-entrypoint.sh django-admin migrate --noinput
docker-compose -f docker-compose-prod.yml run uwsgi /docker-entrypoint.sh django-admin migrate --database clinical --noinput

# TODO this should happen in a DB init script that also creates the DBs if necessary
# it should only run the first time after the DB has been created
# docker-compose -f docker-compose-prod.yml run uwsgi /docker-entrypoint.sh db_init
