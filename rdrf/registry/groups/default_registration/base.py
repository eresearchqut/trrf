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

    def _create_django_user(self, request, django_user, registry, groups=[]):
        user_groups = [self._get_group(g) for g in groups]
        if user_groups:
            django_user.groups.set([g.id for g in user_groups])
        django_user.registry.set([registry, ] if registry else [])
        django_user.is_staff = True
        return django_user

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

