#!/bin/bash

set -e

#
# Development build and tests
#

# ccg-composer runs as this UID, and needs to be able to
# create output directories within it
# mkdir -p data/
# sudo chown 1000:1000 data/

# ./develop.sh build base
# ./develop.sh build builder
# ./develop.sh build node
# ./develop.sh build dev
docker-compose -f dev.yml build

# ./develop.sh check-migrations
docker-compose -f dev.yml run --rm runserver django-admin makemigrations --dry-run --noinput --check

#./develop.sh run-unittests
docker-compose -f test.yml run runservertest runtests


#./develop.sh aloe teststack
./run-aloe.sh

#./develop.sh run build lint
docker run --rm --volume $(pwd):/apps alpine/flake8 .
#./develop.sh run "" node lint
docker-compose -f dev.yml run --rm node lint

