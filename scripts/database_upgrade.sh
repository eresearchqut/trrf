#!/bin/bash

if [ $# -ne 2 ] || [ $1 = "--help" ]; then
  echo "Usage: $0 <old postgres version> <new postgres version>"
  echo "Upgrade databases from one major version to another"
  exit 1
fi

function get_connection_string() {
  echo "postgresql://webapp:webapp@$1/"
}

function get_file_path() {
  echo "/data/upgrade_${pg_old}_to_${pg_new}_$1.sql"
}

function log_progress() {
  echo -e "\033[0;32m$1\033[0m" >&2
}

pg_old=$1
pg_new=$2

databases=(db clinicaldb)

set -ex

POSTGRES_VERSION=$pg_old docker-compose stop
POSTGRES_VERSION=$pg_new docker-compose stop

log_progress "Databases stopped"

for db in "${databases[@]}";
do
  POSTGRES_VERSION=$pg_old docker-compose run --rm runserver pg_dump -d "$(get_connection_string "$db")" -f "$(get_file_path "$db")"
done

log_progress "Databases dumped"

POSTGRES_VERSION=$pg_old docker-compose down -v --remove-orphans

log_progress "Databases removed"

for db in "${databases[@]}";
do
  POSTGRES_VERSION=$pg_new docker-compose run --rm runserver psql -d "$(get_connection_string "$db")" -f "$(get_file_path "$db")"
done

log_progress "Databases restored"

echo -e "\033[1;33mREMINDER: Update the database version in .env to $pg_new & set it in the shell with 'export POSTGRES_VERSION=$pg_new'\033[0m" >&2