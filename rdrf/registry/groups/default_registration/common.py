import logging

from registry.groups.models import WorkingGroup
from rdrf.workflows.registration import FormRegistrationWorkflow

from .base import BaseRegistration


logger = logging.getLogger(__name__)


class DefaultUserRegistration(BaseRegistration):

    def __init__(self, user, request):
        self.token = request.session.get("token", None)
        self.user = user
        self.request = request

    def process(self):
        registry_code = self.request.POST['registry_code']
        registry = self._get_registry_object(registry_code)
        user = self._create_django_user(self.request, self.user, registry)
        # Initially UNALLOCATED
        working_group, status = WorkingGroup.objects.get_or_create(name=self._UNALLOCATED_GROUP,
                                                                   registry=registry)

        user.working_groups.set([working_group])
        user.save()
        logger.debug("Registration process - created user")

    def get_registration_workflow(self):
        return FormRegistrationWorkflow(None, None)
