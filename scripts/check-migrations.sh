#!/bin/sh

docker-compose run --rm runserver django-admin makemigrations --dry-run --noinput --check
