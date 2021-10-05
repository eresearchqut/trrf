#!/bin/bash

# Creates the translation source from the app source code, and the supplied registry definition
# Used as input for crowdin translation platform
#
# And contain registry definition file named $APPLICATION_NAME.yaml in the project root

if [ -z "$1" ]
then
    echo "Registry definition argument"
    exit 1
fi

# Build django strings
docker-compose run --rm -w "/app" runserver django-admin makemessages -d django -l en
docker-compose run --rm -w "/app" runserver django-admin makemessages -d djangojs -l en -i "*node_modules*" -i "*yarn*"

# Build registry definition strings
docker-compose run --rm -w "/app" -e REGISTRY_DEFINITION="$1" runserver bash -c 'django-admin create_translation_file --yaml_file "$REGISTRY_DEFINITION" --system_po_file "translations/locale/en/LC_MESSAGES/django.po" >> "translations/locale/en/LC_MESSAGES/django.po"'