import logging

from registry.groups.models import WorkingGroup
from rdrf.events.events import EventType
from rdrf.services.io.notifications.email_notification import process_notification
from registration.models import RegistrationProfile

from .base import BaseRegistration


logger = logging.getLogger(__name__)


class PatientRegistration(BaseRegistration):

    def __init__(self, user, request, form):
        super().__init__(user, request, form)

    def update_django_user(self, django_user, registry):
        user_group = self._get_group("Patients")
        groups = [user_group.id, ] if user_group else []
        form_data = self.form.cleaned_data
        return self.setup_django_user(django_user, registry, groups, form_data['first_name'], form_data['surname'])

    def process(self):
        registry_code = self.form.cleaned_data['registry_code']
        registry = self._get_registry_object(registry_code)
        user = self.update_django_user(self.user, registry)
        # Initially UNALLOCATED
        working_group, status = WorkingGroup.objects.get_or_create(name=self._UNALLOCATED_GROUP,
                                                                   registry=registry)

        user.working_groups.set([working_group])
        user.save()
        logger.debug("Registration process - created user")
        patient = self._create_patient(registry, working_group, user)
        logger.debug("Registration process - created patient")
        address = self._create_patient_address(patient)
        address.save()
        logger.debug("Registration process - created patient address")

        template_data = {
            "patient": patient,
            "registration": RegistrationProfile.objects.get(user=user)
        }

        process_notification(registry_code, EventType.NEW_PATIENT, template_data)
        logger.debug("Registration process - sent notification for NEW_PATIENT")

    def get_template_name(self):
        return "registration/registration_form_patient.html"
