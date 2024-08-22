#!/bin/sh

echo "Formatting your python code"
docker run --rm --volume $(pwd):/io ghcr.io/astral-sh/ruff check --fix .
docker run --rm --volume $(pwd):/io ghcr.io/astral-sh/ruff format .
