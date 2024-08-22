#!/bin/sh

echo "Linting your python code"
docker run --rm --volume $(pwd):/io ghcr.io/astral-sh/ruff check . || exit 1
