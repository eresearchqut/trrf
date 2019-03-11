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
docker-compose -f dev.yml run runserver django-admin makemigrations --dry-run --noinput --check

#./develop.sh run-unittests
#./develop.sh aloe teststack

#./develop.sh run build lint
docker run -it --rm --volume $(pwd):/apps alpine/flake8 .
#./develop.sh run "" node lint
docker-compose -f dev.yml run --rm node lint

