import logging

from registration.models import RegistrationProfile

from rdrf.events.events import EventType
from rdrf.services.io.notifications.email_notification import \
    process_notification
from registry.groups import GROUPS

from .base import BaseRegistration

logger = logging.getLogger(__name__)


class PatientRegistration(BaseRegistration):

    def process(self, user):
        registry_code = self.form.cleaned_data['registry_code']
        registry = self._get_registry_object(registry_code)

        user = self.update_django_user(user, registry)

        working_group = self._get_unallocated_working_group(registry)
        user.working_groups.set([working_group])
        user.save()

        logger.info("Registration process - created user")
        patient = self._create_patient(registry, working_group, user)
        logger.info("Registration process - created patient")

        registration = RegistrationProfile.objects.get(user=user)
        template_data = {
            "patient": patient,
            "registration": registration,
            "activation_url": self.get_registration_activation_url(registration),
        }

        process_notification(registry_code, EventType.NEW_PATIENT, template_data)
        logger.info("Registration process - sent notification for NEW_PATIENT")

    def update_django_user(self, django_user, registry):
        form_data = self.form.cleaned_data
        return self.setup_django_user(django_user, registry, GROUPS.PATIENT, form_data['first_name'], form_data['surname'])

    def get_template_name(self):
        return "registration/registration_form_patient.html"
