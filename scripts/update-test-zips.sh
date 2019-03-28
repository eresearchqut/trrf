#!/bin/sh

alias teststack="docker-compose -f docker-compose-teststack-base.yml -f docker-compose-teststack-dev.yml"
alias teststack-exec-django="teststack exec serverundertest /docker-entrypoint.sh django-admin.py"

export_zip() {
    teststack stop
    teststack rm --force
    teststack up -d

    set +e

    teststack-exec-django migrate
    teststack-exec-django import "${1}" --force
    teststack-exec-django export registry --filename "${1}" --registry-code "${2}"

    set -e

    teststack stop
}

export_zip /app/rdrf/rdrf/testing/behaviour/features/exported_data/dd.zip dd
export_zip /app/rdrf/rdrf/testing/behaviour/features/exported_data/fh.zip fh
export_zip /app/rdrf/rdrf/testing/behaviour/features/exported_data/ang.zip ang
