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

# Build the images
docker-compose build

# ./develop.sh check-migrations
scripts/check-migrations.sh

#./develop.sh run-unittests
scripts/unit-tests.sh

#./develop.sh aloe teststack
scripts/end2end-tests.sh

#./develop.sh run build lint
#./develop.sh run "" node lint
scripts/lint.sh


# Notes for CD
# export TRRF_VERSION=1.0.0
# docker build -f docker/production/Dockerfile -t eresearchqut/trrf:${TRRF_VERSION} .
# scripts/end2end-tests.sh prod

# Then push to ECR etc.


