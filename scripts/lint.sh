#!/bin/sh

echo "Linting your python code"
docker run --rm --volume $(pwd):/apps alpine/flake8 . || exit 1
