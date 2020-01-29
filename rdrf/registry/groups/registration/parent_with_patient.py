import logging

from django.utils.translation import get_language
from registration.models import RegistrationProfile

from rdrf.events.events import EventType
from rdrf.services.io.notifications.email_notification import \
    process_notification
from registry.groups import GROUPS
from registry.patients.models import ParentGuardian

from .base import BaseRegistration

logger = logging.getLogger(__name__)


class ParentWithPatientRegistration(BaseRegistration):

    def process(self, user):
        registry_code = self.form.cleaned_data['registry_code']
        registry = self._get_registry_object(registry_code)

        user = self.update_django_user(user, registry)

        working_group = self._get_unallocated_working_group(registry)
        user.working_groups.set([working_group])
        user.save()

        logger.debug("Registration process - created user")
        patient = self._create_patient(registry, working_group, user, set_link_to_user=False)
        logger.debug("Registration process - created patient")

        parent_guardian = self._create_parent()

        parent_guardian.patient.add(patient)
        parent_guardian.user = user
        parent_guardian.save()
        logger.debug("Registration process - created parent")

        registration = RegistrationProfile.objects.get(user=user)
        template_data = {
            "patient": patient,
            "parent": parent_guardian,
            "registration": registration,
            "activation_url": self.get_registration_activation_url(registration),
        }

        process_notification(registry_code, EventType.NEW_PATIENT, template_data)
        logger.debug("Registration process - sent notification for NEW_PATIENT")

    def _create_parent(self):
        form_data = self.form.cleaned_data
        parent_guardian = ParentGuardian.objects.create(
            first_name=form_data["parent_guardian_first_name"],
            last_name=form_data["parent_guardian_last_name"],
            date_of_birth=form_data["parent_guardian_date_of_birth"],
            gender=form_data["parent_guardian_gender"],
        )
        return parent_guardian

    def update_django_user(self, django_user, registry):
        form_data = self.form.cleaned_data
        first_name = form_data['parent_guardian_first_name']
        last_name = form_data['parent_guardian_last_name']

        preferred_language = self.form.cleaned_data.get('preferred_language', 'en')
        django_user.preferred_language = preferred_language

        return self.setup_django_user(django_user, registry, GROUPS.PARENT, first_name, last_name)

    @property
    def language(self):
        return get_language()

    def get_template_name(self):
        return "registration/registration_form_patient_with_parent.html"
