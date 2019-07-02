import abc
import logging

from django.contrib.auth.models import Group

from rdrf.models.definition.models import Registry
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient, PatientAddress, AddressType


logger = logging.getLogger(__name__)


class BaseRegistration(abc.ABC):

    def __init__(self, request, form):
        self.request = request
        self.form = form

    @abc.abstractmethod
    def get_template_name(self):
        raise NotImplementedError

    @abc.abstractmethod
    def process(self, user):
        raise NotImplementedError

    def _get_registry_object(self, registry_name):
        return Registry.objects.filter(code__iexact=registry_name).first()

    def _get_group(self, group_name):
        group, _ = Group.objects.get_or_create(name__iexact=group_name, defaults={'name': 'group_name'})
        return group

    def _get_unallocated_working_group(self, registry):
        return WorkingGroup.objects.get_unallocated(registry)

    def _create_patient_address(self, patient, address_type="Postal"):
        form_data = self.form.cleaned_data
        same_address = form_data.get("same_address", False)
        return PatientAddress.objects.create(
            patient=patient,
            address_type=self.get_address_type(address_type),
            address=form_data["parent_guardian_address"] if same_address else form_data["address"],
            suburb=form_data["parent_guardian_suburb"] if same_address else form_data["suburb"],
            state=form_data["parent_guardian_state"] if same_address else form_data["state"],
            postcode=form_data["parent_guardian_postcode"] if same_address else form_data["postcode"],
            country=form_data["parent_guardian_country"] if same_address else form_data["country"]
        )

    def _create_patient(self, registry, working_group, user, set_link_to_user=True):

        form_data = self.form.cleaned_data
        patient = Patient.objects.create(
            consent=True,
            family_name=form_data["surname"],
            given_names=form_data["first_name"],
            date_of_birth=form_data["date_of_birth"],
            sex=form_data["gender"]
        )

        patient.rdrf_registry.add(registry)
        patient.working_groups.add(working_group)
        patient.home_phone = form_data["phone_number"]
        patient.email = user.username
        patient.user = user if set_link_to_user else None
        patient.save()
        return patient

    def get_address_type(self, address_type):
        address_type_obj, created = AddressType.objects.get_or_create(type=address_type)
        return address_type_obj

    def setup_django_user(self, django_user, registry, group, first_name, last_name):
        django_user.registry.set([registry, ] if registry else [])
        django_user.groups.add(self._get_group(group))
        django_user.is_staff = True
        django_user.first_name = first_name
        django_user.last_name = last_name
        return django_user
