#!/bin/sh

docker-compose -f docker-compose-teststack-base.yml -f docker-compose-teststack-dev.yml run --rm serverundertest runtests $@
RESULT=$?

docker-compose -f docker-compose-teststack-base.yml -f docker-compose-teststack-dev.yml stop

exit $RESULT
