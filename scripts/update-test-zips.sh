#!/bin/bash

teststack() {
  docker-compose -f docker-compose-teststack-base.yml -f docker-compose-teststack-dev.yml "$@"
}

teststack-exec-django() {
  teststack exec serverundertest /docker-entrypoint.sh django-admin "$@"
}


wait_for_server() {
    while ! curl -Is http://localhost:$1 > /dev/null; do
        echo "$(date) - waiting to connect $1"
        sleep 5
    done
    echo "$(date) - connected to $1"
}

export_zip() {
    teststack stop
    teststack rm --force
    teststack up -d

    PORT=$(teststack port serverundertest 8000 | cut -d':' -f2)
    wait_for_server $PORT

    set +e

    teststack-exec-django import "${1}" --force
    teststack-exec-django export registry --filename "${1}" --registry-code "${2}"

    set -e

    teststack stop
}

export_zip /app/rdrf/rdrf/testing/behaviour/features/exported_data/dd.zip dd
export_zip /app/rdrf/rdrf/testing/behaviour/features/exported_data/fh.zip fh
export_zip /app/rdrf/rdrf/testing/behaviour/features/exported_data/ang.zip ang
