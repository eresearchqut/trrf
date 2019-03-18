#!/bin/sh

echo "Linting your python code"
docker run --rm --volume $(pwd):/apps alpine/flake8 . || exit 1

echo "Linting your javascript/typescript"
docker-compose run --rm node lint

