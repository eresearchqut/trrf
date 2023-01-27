#!/bin/sh

docker-compose -f docker-compose-teststack-base.yml -f docker-compose-teststack-dev.yml -f docker-compose-wiremock.yml run --rm serverundertest runtests $@
RESULT=$?

docker-compose -f docker-compose-teststack-base.yml -f docker-compose-teststack-dev.yml -f docker-compose-wiremock.yml stop

exit $RESULT
