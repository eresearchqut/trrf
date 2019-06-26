import abc

from rdrf.models.definition.models import Registry
from django.contrib.auth.models import Group

import logging

logger = logging.getLogger(__name__)


class BaseRegistration(object):
    _UNALLOCATED_GROUP = "Unallocated"
    user = None
    request = None

    def __init__(self, user, request):
        self.user = user
        self.request = request

    @abc.abstractmethod
    def process(self, ):
        return

    @abc.abstractmethod
    def get_registration_workflow(self):
        return

    def _get_registry_object(self, registry_name):
        try:
            registry = Registry.objects.get(code__iexact=registry_name)
            return registry
        except Registry.DoesNotExist:
            return None

    def _get_group(self, group_name):
        try:
            group, created = Group.objects.get_or_create(name=group_name)
            return group
        except Group.DoesNotExist:
            return None
