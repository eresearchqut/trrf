import abc

from rdrf.models.definition.models import Registry
from django.contrib.auth.models import Group
from registry.patients.models import  Patient, PatientAddress, AddressType

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

    def _create_patient(self, registry, working_group, user, set_link_to_user=True):

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
        patient.user = user if set_link_to_user else None
        patient.save()
        return patient

    def get_address_type(self, address_type):
        address_type_obj, created = AddressType.objects.get_or_create(type=address_type)
        return address_type_obj
