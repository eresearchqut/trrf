import logging

from registry.groups.models import WorkingGroup
from rdrf.workflows.registration import PatientRegistrationWorkflow
from rdrf.events.events import EventType
from rdrf.services.io.notifications.email_notification import process_notification
from registration.models import RegistrationProfile

from ..base import BaseRegistration


logger = logging.getLogger(__name__)


class PatientRegistration(BaseRegistration):

    def __init__(self, user, request):
        super().__init__(user, request)

    def _create_django_user(self, request, django_user, registry, groups=[]):
        user_groups = [self._get_group(g) for g in groups]
        if user_groups:
            django_user.groups.set([g.id for g in user_groups])
        django_user.registry.set([registry, ] if registry else [])
        django_user.is_staff = True
        user_group = self._get_group("Patients")
        django_user.groups.set([user_group.id, ] if user_group else [])
        django_user.first_name = request.POST['first_name']
        django_user.last_name = request.POST['surname']
        return django_user

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
        patient = self._create_patient(registry, working_group, user)
        logger.debug("Registration process - created patient")
        address = self._create_patient_address(patient, self.request)
        address.save()
        logger.debug("Registration process - created patient address")

        template_data = {
            "patient": patient,
            "registration": RegistrationProfile.objects.get(user=user)
        }

        process_notification(registry_code, EventType.NEW_PATIENT, template_data)
        logger.debug("Registration process - sent notification for NEW_PATIENT")

    def get_registration_workflow(self):
        return PatientRegistrationWorkflow(None, None)
