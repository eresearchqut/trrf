import logging

from django.utils.translation import get_language

from rdrf.events.events import EventType
from rdrf.services.io.notifications.email_notification import process_notification
from rdrf.models.workflow_models import ClinicianSignupRequest

from registration.models import RegistrationProfile
from registry.patients.models import ParentGuardian, Patient
from registry.groups.models import WorkingGroup

from rdrf.workflows.registration import PatientWithParentRegistrationWorkflow

from .base import BaseRegistration


logger = logging.getLogger(__name__)


class ParentWithPatientRegistration(BaseRegistration):

    def __init__(self, user, request, form):
        super().__init__(user, request, form)
        self.token = request.session.get("token", None)
        if self.token:
            try:
                self.clinician_signup = ClinicianSignupRequest.objects.get(token=self.token,
                                                                           state="emailed")
            except ClinicianSignupRequest.DoesNotExist:
                raise Exception("Clinician already signed up or unknown token")
        else:
            self.clinician_signup = None

    def _do_clinician_signup(self, registry_model):
        from rdrf.helpers.utils import get_site
        user = self.update_django_user(self.user, registry_model, is_parent=False, is_clinician=True)

        logger.debug("created django user for clinician")

        # working group should be the working group of the patient
        patient = Patient.objects.get(id=self.clinician_signup.patient_id)

        user.working_groups.set([wg for wg in patient.working_groups.all()])
        user.save()
        logger.debug("set clinician working groups to patient's")
        self.clinician_signup.clinician_other.user = user
        self.clinician_signup.clinician_other.use_other = False
        self.clinician_signup.clinician_other.save()
        self.clinician_signup.state = "signed-up"   # at this stage the user is created but not active
        self.clinician_signup.save()
        patient.clinician = user
        patient.save()
        logger.debug("made this clinician the clinician of the patient")

        site_url = get_site()

        activation_template_data = {
            "site_url": site_url,
            "clinician_email": self.clinician_signup.clinician_email,
            "clinician_lastname": self.clinician_signup.clinician_other.clinician_last_name,
            "registration": RegistrationProfile.objects.get(user=user)
        }

        process_notification(registry_model.code,
                             EventType.CLINICIAN_ACTIVATION,
                             activation_template_data)
        logger.debug("Registration process - sent activation link for registered clinician")

    def process(self):
        registry_code = self.form.cleaned_data['registry_code']
        registry = self._get_registry_object(registry_code)
        preferred_language = self.form.cleaned_data.get("preferred_language", "en")
        if self.clinician_signup:
            logger.debug("signing up clinician")
            self._do_clinician_signup(registry)
            return

        user = self.update_django_user(self.user, registry, is_parent=True)
        user.preferred_language = preferred_language
        # Initially UNALLOCATED
        working_group, status = WorkingGroup.objects.get_or_create(name=self._UNALLOCATED_GROUP,
                                                                   registry=registry)

        user.working_groups.set([working_group])
        user.save()
        logger.debug("Registration process - created user")

        patient = self._create_patient(registry, working_group, user, set_link_to_user=False)
        logger.debug("Registration process - created patient")

        address = self._create_patient_address(patient)
        address.save()
        logger.debug("Registration process - created patient address")

        parent_guardian = self._create_parent()

        parent_guardian.patient.add(patient)
        parent_guardian.user = user
        parent_guardian.save()
        logger.debug("Registration process - created parent")

        template_data = {
            "patient": patient,
            "parent": parent_guardian,
            "registration": RegistrationProfile.objects.get(user=user)
        }

        process_notification(registry_code, EventType.NEW_PATIENT, template_data)
        logger.debug("Registration process - sent notification for NEW_PATIENT")

    def get_registration_workflow(self):
        return PatientWithParentRegistrationWorkflow(None, None)

    def _create_parent(self):
        form_data = self.form.cleaned_data
        parent_guardian = ParentGuardian.objects.create(
            first_name=form_data["parent_guardian_first_name"],
            last_name=form_data["parent_guardian_last_name"],
            date_of_birth=form_data["parent_guardian_date_of_birth"],
            gender=form_data["parent_guardian_gender"],
            address=form_data["parent_guardian_address"],
            suburb=form_data["parent_guardian_suburb"],
            state=form_data["parent_guardian_state"],
            postcode=form_data["parent_guardian_postcode"],
            country=form_data["parent_guardian_country"],
            phone=form_data["parent_guardian_phone"],
        )
        return parent_guardian

    def update_django_user(self, django_user, registry, is_parent, is_clinician=False):
        if is_parent:
            user_group = self._get_group("Parents")
        elif is_clinician:
            user_group = self._get_group("Clinical Staff")
        else:
            user_group = self._get_group("Patients")
        groups = [user_group.id, ] if user_group else []
        form_data = self.form.cleaned_data
        if is_parent:
            first_name = form_data['parent_guardian_first_name']
            last_name = form_data['parent_guardian_first_name']
        elif is_clinician:
            logger.debug("setting up clinician")
            # clinician signup only exists on subclass ..
            first_name = self.clinician_signup.clinician_other.clinician_first_name
            last_name = self.clinician_signup.clinician_other.clinician_last_name
        else:
            first_name = form_data['first_name']
            last_name = form_data['surname']

        return self.setup_django_user(django_user, registry, groups, first_name, last_name)

    @property
    def language(self):
        return get_language()
