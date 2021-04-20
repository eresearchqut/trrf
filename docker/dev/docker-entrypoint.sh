#!/bin/bash


# wait for a given host:port to become available
#
# $1 host
# $2 port
function dockerwait {
    while ! exec 6<>/dev/tcp/"$1"/"$2"; do
        warn "$(date) - waiting to connect $1 $2"
        sleep 5
    done
    success "$(date) - connected to $1 $2"

    exec 6>&-
    exec 6<&-
}


function info () {
    printf "\r  [\033[00;34mINFO\033[0m] %s\n" "$1"
}


function warn () {
    printf "\r  [\033[00;33mWARN\033[0m] %s\n" "$1"
}


function success () {
    printf "\r\033[2K  [\033[00;32m OK \033[0m] %s\n" "$1"
}


function fail () {
    printf "\r\033[2K  [\033[0;31mFAIL\033[0m] %s\n" "$1"
    echo ''
    exit 1
}


# wait for services to become available
# this prevents race conditions using fig
function wait_for_services {
    if [[ "$WAIT_FOR_DB" ]] ; then
        dockerwait "$DBSERVER" "$DBPORT"
    fi
    if [[ "$WAIT_FOR_CLINICAL_DB" ]] ; then
        dockerwait "$CLINICAL_DBSERVER" "$CLINICAL_DBPORT"
    fi
    if [[ "$WAIT_FOR_REPORTING_DB" ]] ; then
        dockerwait "$REPORTING_DBSERVER" "$REPORTING_DBPORT"
    fi
    if [[ "$WAIT_FOR_CACHE" ]] ; then
        dockerwait "$CACHESERVER" "$CACHEPORT"
    fi
    if [[ "$WAIT_FOR_RUNSERVER" ]] ; then
        dockerwait "$RUNSERVER" "$RUNSERVERPORT"
    fi
    if [[ "$WAIT_FOR_UWSGI" ]] ; then
        dockerwait "$UWSGISERVER" "$UWSGIPORT"
    fi
}


function defaults {
    : "${DBSERVER:=db}"
    : "${DBPORT:=5432}"
    : "${DBUSER:=webapp}"
    : "${DBNAME:=${DBUSER}}"
    : "${DBPASS:=${DBUSER}}"

    : "${CLINICAL_DBSERVER:=${DBSERVER}}"
    : "${CLINICAL_DBPORT:=5432}"
    : "${CLINICAL_DBUSER:=${DBUSER}}"
    : "${CLINICAL_DBNAME:=${CLINICAL_DBUSER}}"
    : "${CLINICAL_DBPASS:=${DBPASS}}"

    : "${REPORTING_DBSERVER:=${DBSERVER}}"
    : "${REPORTING_DBPORT:=5432}"
    : "${REPORTING_DBUSER:=${DBUSER}}"
    : "${REPORTING_DBNAME:=${REPORTING_DBUSER}}"
    : "${REPORTING_DBPASS:=${DBPASS}}"

    : "${UWSGISERVER:=uwsgi}"
    : "${UWSGIPORT:=9000}"
    : "${UWSGI_OPTS:=/app/uwsgi/docker.ini}"
    : "${RUNSERVER:=runserver}"
    : "${RUNSERVERPORT:=8000}"
    : "${RUNSERVER_CMD:=runserver}"
    : "${CACHESERVER:=cache}"
    : "${CACHEPORT:=11211}"

    MEMCACHE=""
    if [[ "$WAIT_FOR_CACHE" ]] ; then
      : "${MEMCACHE:=${CACHESERVER}:${CACHEPORT}}"
    fi

    # variables to control where tests will look for the app (aloe via selenium hub)
    : "${TEST_APP_SCHEME:=http}"
    : "${TEST_APP_HOST:=runservertest}"
    : "${TEST_APP_PORT:=8000}"
    : "${TEST_APP_PATH:=/}"
    : "${TEST_APP_URL:=${TEST_APP_SCHEME}://${TEST_APP_HOST}:${TEST_APP_PORT}${TEST_APP_PATH}}"
    #: "${TEST_BROWSER:=chrome}"
    : "${TEST_BROWSER:=firefox}"
    : "${TEST_WAIT:=30}"
    : "${TEST_SELENIUM_HUB:=http://hub:4444/wd/hub}"

    : "${DJANGO_FIXTURES:=""}"

    export DBSERVER DBPORT DBUSER DBNAME DBPASS MEMCACHE
    export CLINICAL_DBSERVER CLINICAL_DBPORT CLINICAL_DBUSER CLINICAL_DBNAME CLINICAL_DBPASS
    export REPORTING_DBSERVER REPORTING_DBPORT REPORTING_DBUSER REPORTING_DBNAME REPORTING_DBPASS
    export TEST_APP_URL TEST_APP_SCHEME TEST_APP_HOST TEST_APP_PORT TEST_APP_PATH TEST_BROWSER TEST_WAIT TEST_SELENIUM_HUB
    export DJANGO_FIXTURES
}


function _django_check_deploy {
    info "running check --deploy"
    set -x
    django-admin.py check --deploy --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-check.log
    set +x
}


function _django_migrate {
    info "running migrate"
    set -x
    django-admin.py migrate --noinput --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-migrate.log
    django-admin.py migrate --database=clinical --noinput --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-migrate-clinical.log
    django-admin.py update_permissions --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-permissions.log
    set +x
}


function _django_collectstatic {
    info "running collectstatic"
    set -x
    django-admin.py collectstatic --noinput --settings="${DJANGO_SETTINGS_MODULE}" 2>&1 | tee "${LOG_DIRECTORY}"/uwsgi-collectstatic.log
    set +x
}


function _django_fixtures {
    info "loading fixtures ${DJANGO_FIXTURES}"
    set -x
    django-admin.py init ${DJANGO_FIXTURES}
    set +x
}


function _runserver() {
    : "${RUNSERVER_OPTS=${RUNSERVER_CMD} 0.0.0.0:${RUNSERVERPORT} --settings=${DJANGO_SETTINGS_MODULE}}"

    _django_migrate
    _django_fixtures

    info "RUNSERVER_OPTS is ${RUNSERVER_OPTS}"
    set -x
    # shellcheck disable=SC2086
    exec django-admin.py ${RUNSERVER_OPTS}
}


function _aloe() {
    export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE}"_test
    shift
    set -x
    exec django-admin.py harvest --with-xunit --xunit-file="${WRITABLE_DIRECTORY}"/tests.xml --verbosity=3 "$@"
}


trap exit SIGHUP SIGINT SIGTERM
defaults

# Display all env vars, but mask the values of sensitive ones (containing pass, key or secret in their name)
env | sort | awk -F "=" '{ if($1 ~ /(KEY|PASS|SECRET)/) print $1 "=xxxxx"; else print }'

wait_for_services

# prod uwsgi entrypoint
if [ "$1" = 'uwsgi' ]; then
    info "[Run] Starting prod uwsgi"

    _django_check_deploy

    set -x
    # exec uwsgi --die-on-term --ini "${UWSGI_OPTS}"
    exec uwsgi --http :9000 --wsgi-file /app/uwsgi/django.wsgi --static-map /static=/data/static
fi

# prod uwsgi HTTPS entrypoint
if [ "$1" = 'uwsgi_ssl' ]; then
    info "[Run] Starting prod uwsgi on HTTPS"

    _django_check_deploy

    set -x
    # exec uwsgi --die-on-term --ini "${UWSGI_OPTS}"
    exec uwsgi --master --https 0.0.0.0:9443,/etc/ssl/certs/ssl-cert-snakeoil.pem,/etc/ssl/private/ssl-cert-snakeoil.key --wsgi-file /app/uwsgi/django.wsgi --static-map /static=/data/static
fi

# prod uwsgi HTTPS entrypoint
if [ "$1" = 'uwsgi_ssl_fargate' ]; then
    info "[Run] Starting prod uwsgi on HTTPS"

    _django_check_deploy

    info "running collectstatic"
    set -x
    django-admin.py collectstatic --noinput --settings="${DJANGO_SETTINGS_MODULE}" 2>&1

    set -x
    # exec uwsgi --die-on-term --ini "${UWSGI_OPTS}"
    exec uwsgi --master --enable-threads --processes 6 --https 0.0.0.0:9443,/etc/ssl/certs/ssl-cert-snakeoil.pem,/etc/ssl/private/ssl-cert-snakeoil.key --wsgi-file /app/uwsgi/django.wsgi --static-map /static=/data/static
fi



# runserver entrypoint
if [ "$1" = 'runserver' ]; then
    info "[Run] Starting runserver"
    _runserver
fi

# runserver_plus entrypoint
if [ "$1" = 'runserver_plus' ]; then
    info "[Run] Starting runserver_plus"
    RUNSERVER_CMD=runserver_plus
    _runserver
fi

# runtests entrypoint
if [ "$1" = 'runtests' ]; then
    info "[Run] Starting tests"
    export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE}"_test

    set -x
    args="rdrf/rdrf/testing/unit"
    if [ "$2" != "" ]; then
        # pass through any arguments (if provided) to pytest
        args="${@:2}"
    fi
    cd /app
    exec pytest $args
fi

# aloe entrypoint
if [ "$1" = 'aloe' ]; then
    info "[Run] Starting aloe"
    # cd /app/rdrf/rdrf/testing/behaviour || exit
    # Find the aloe tests directory dynamically, in order to also find them in projects
    # including TRRF as a git submodule
    cd `find /app -path '*/testing/behaviour'` || exit 1
    _aloe "$@"
fi

# db_init entrypoint
if [ "$1" = 'db_init' ]; then
    info "[Run] Initialising the DB with data"
    _django_fixtures
    exit
fi

warn "[RUN]: Builtin command not provided [tarball|aloe|runtests|runserver|runserver_plus|uwsgi|uwsgi_local|db_init]"
info "[RUN]: $*"

set -x
# shellcheck disable=SC2086 disable=SC2048
exec "$@"
