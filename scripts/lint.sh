#!/bin/sh

echo "Linting your python code"
docker run --rm --volume $(pwd):/io ghcr.io/astral-sh/ruff check . || exit 1
docker run --rm --volume $(pwd):/io ghcr.io/astral-sh/ruff format --check . || exit 1
