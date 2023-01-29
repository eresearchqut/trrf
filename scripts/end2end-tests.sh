#!/bin/sh

# check we have an argument to find the stack to run tests against
if [ "${1}x" = "x" ]; then
    STACK=dev
elif [ "${1}" != "dev" ] && [ "${1}" != "prod" ]; then
    echo "You probably want one of these:"
    echo "> $0 dev"
    echo "> $0 prod"
    exit 1
else
    STACK=${1}
fi

alias aloe='docker-compose -f docker-compose-aloe.yml'
alias selenium='docker-compose -f docker-compose-selenium.yml'
alias teststack="docker-compose -f docker-compose-teststack-base.yml -f docker-compose-teststack-${STACK}.yml -f docker-compose-wiremock.yml"

stop_all() {
    trap "echo 'Exiting'" HUP INT TERM
    aloe stop
    selenium stop
    teststack stop
}

trap "stop_all; exit" HUP INT TERM

# start selenium in the background
selenium stop
selenium rm --force
selenium up -d

# start the test stack in the background
teststack stop
teststack rm --force
teststack up -d

# run aloe
aloe stop
aloe rm --force

set +e
aloe run --rm aloe_${STACK}
rval=$?
set -e

stop_all

ALOEOUT="data/aloe/${STACK}"

mkdir -p "$ALOEOUT"
selenium logs --no-color > "$ALOEOUT"/aloe-selenium.log
teststack logs --no-color > "$ALOEOUT"/aloe-teststack.log

exit $rval

