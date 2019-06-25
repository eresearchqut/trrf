import logging

from rdrf.events.events import EventType
from rdrf.services.io.notifications.email_notification import process_notification
from rdrf.models.workflow_models import ClinicianSignupRequest

from registration.models import RegistrationProfile
from registry.patients.models import ParentGuardian, Patient, PatientAddress
from registry.groups.models import WorkingGroup
from rdrf.workflows.registration import PatientRegistrationWorkflow

from .base import BaseRegistration


logger = logging.getLogger(__name__)


class PatientRegistration(BaseRegistration):

    def __init__(self, user, request):
        self.token = request.session.get("token", None)
        self.user = user
        self.request = request
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
        user = self._create_django_user(self.request,
                                        self.user,
                                        registry_model,
                                        is_parent=False,
                                        is_clinician=True)

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
        registry_code = self.request.POST['registry_code']
        registry = self._get_registry_object(registry_code)
        preferred_language = self.request.POST.get("preferred_language", "en")
        if self.clinician_signup:
            logger.debug("signing up clinician")
            self._do_clinician_signup(registry)
            return

        user = self._create_django_user(self.request, self.user, registry, is_parent=True)
        user.preferred_language = preferred_language
        # Initially UNALLOCATED
        working_group, status = WorkingGroup.objects.get_or_create(name=self._UNALLOCATED_GROUP,
                                                                   registry=registry)

        user.working_groups.set([working_group])
        user.save()
        logger.debug("Registration process - created user")

        patient = Patient.objects.create(
            consent=True,
            family_name=self.request.POST["surname"],
            given_names=self.request.POST["first_name"],
            date_of_birth=self.request.POST["date_of_birth"],
            sex=self.request.POST["gender"]
        )

        patient.rdrf_registry.add(registry)
        patient.working_groups.add(working_group)
        patient.home_phone = self.request.POST["phone_number"]
        patient.email = user.username
        patient.user = None

        patient.save()
        logger.debug("Registration process - created patient")

        address = self._create_patient_address(patient, self.request)
        address.save()
        logger.debug("Registration process - created patient address")

        parent_guardian = self._create_parent(self.request)

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
        return PatientRegistrationWorkflow(None, None)

    def _create_parent(self, request):
        parent_guardian = ParentGuardian.objects.create(
            first_name=request.POST["parent_guardian_first_name"],
            last_name=request.POST["parent_guardian_last_name"],
            date_of_birth=request.POST["parent_guardian_date_of_birth"],
            gender=request.POST["parent_guardian_gender"],
            address=request.POST["parent_guardian_address"],
            suburb=request.POST["parent_guardian_suburb"],
            state=request.POST["parent_guardian_state"],
            postcode=request.POST["parent_guardian_postcode"],
            country=request.POST["parent_guardian_country"],
            phone=request.POST["parent_guardian_phone"],
        )
        return parent_guardian

    def _create_patient_address(self, patient, request, address_type="Postal"):
        same_address = "same_address" in request.POST

        address = PatientAddress.objects.create(
            patient=patient,
            address_type=self.get_address_type(address_type),
            address=request.POST["parent_guardian_address"] if same_address else request.POST["address"],
            suburb=request.POST["parent_guardian_suburb"] if same_address else request.POST["suburb"],
            state=request.POST["parent_guardian_state"] if same_address else request.POST["state"],
            postcode=request.POST["parent_guardian_postcode"] if same_address else request.POST["postcode"],
            country=request.POST["parent_guardian_country"] if same_address else request.POST["country"]
        )
        return address
