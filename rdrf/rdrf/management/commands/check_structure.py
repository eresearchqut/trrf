import sys
from django.core.management import BaseCommand
from rdrf.models import Registry
from rdrf.models import Modjgo
import yaml
import jsonschema
import errno
import os

explanation = "This command checks for schema validation errors"

SCHEMA_LOCATIONS = ["/app/rdrf/rdrf/schemas/modjgo.yaml",
                    "/env/src/django-rdrf/rdrf/rdrf/schemas/modjgo.yaml"]

class Command(BaseCommand):
    help = 'Checks in clinical db against json schema(s)'

    def add_arguments(self, parser):
        parser.add_argument('-r',"--registry_code",
                            action='store',
                            dest='registry_code',
                            help='Code of registry to check')
        parser.add_argument('-c','--collection',
                            action='store',
                            dest='collection',
                            default="cdes",
                            choices=['cdes', 'history', 'progress', 'registry_specific'],
                            help='Collection name')

        parser.add_argument('-t','--test-mode',
                            action='store_true',
                            dest='test_mode',
                            default=False,
                            help='Test mode - does not return exit code 1 on fail')

    def _usage(self):
        print(explanation)

    def _print(self, msg):
        self.stdout.write(msg + "\n")

    def handle(self, *args, **options):
        self.test_mode = options.get("test_mode", False)
        problem_count = 0
        self.schema = self._load_schema()
        registry_code = options.get("registry_code",None)
        if registry_code is None:
            self._print("Error: registry code required")
            if not self.test_mode:
                sys.exit(1)
        try:
            registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self._print("Error: registry does not exist")
            if not self.test_mode:
                sys.exit(1)
        
        collection = options.get("collection", "cdes")
        if collection == "registry_specific":
           collection = "registry_specific_patient_data"

        for modjgo_model in Modjgo.objects.filter(registry_code=registry_code,
                                                  collection=collection):
            data = modjgo_model.data
            problem = self._check_for_problem(collection, data)
            if problem is not None:
                problem_count += 1
                django_model, django_id, message = problem
                self._print("%s;%s;%s;%s" % (modjgo_model.pk,
                                       django_model,
                                       django_id,
                                       message))

        if problem_count > 0:
            if not self.test_mode:
                sys.exit(1)
            
                
    def _load_schema(self):
        # base rdrf and mtm will differ on the location of this file
        for file_location in SCHEMA_LOCATIONS:
            if os.path.exists(file_location):
                with open(file_location) as sf:
                    return yaml.load(sf)

        raise FileNotFoundError(errno.ENOENT,
                                os.strerror(errno.ENOENT),
                                "modjgo.yaml")

    def _get_key(self, data, key):
        if data is None:
            return None
        if key in data:
            return data[key]

    def _check_for_problem(self, collection, data):
        schema = self._load_schema()
        try:
            jsonschema.validate({collection: data}, schema)
            return None
        except Exception as verr:
            message = verr.message
            django_id = self._get_key(data, "django_id")
            django_model = self._get_key(data, "django_model")
            return django_model, django_id, message
