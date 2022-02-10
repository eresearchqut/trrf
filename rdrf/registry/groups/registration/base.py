import abc
import logging

from django.contrib.auth.models import Group
from django.urls import reverse

from rdrf.helpers.utils import make_full_url
from rdrf.models.definition.models import Registry
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient

from registry.patients.patient_stage_flows import get_registry_stage_flow

logger = logging.getLogger(__name__)


class BaseRegistration(abc.ABC):

    def __init__(self, request, form=None):
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
        group, _ = Group.objects.get_or_create(name__iexact=group_name, defaults={'name': group_name})
        return group

    def _get_unallocated_working_group(self, registry):
        return WorkingGroup.objects.get_unallocated(registry)

    def _create_patient(self, registry, working_group, user, set_link_to_user=True):
        if not self.form:
            raise AttributeError("Cannot create patient without form")

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
        patient.email = user.username
        patient.user = user if set_link_to_user else None
        get_registry_stage_flow(registry).handle(patient)
        patient.save()
        return patient

    def setup_django_user(self, django_user, registry, group, first_name, last_name):
        django_user.registry.set([registry, ] if registry else [])
        django_user.groups.add(self._get_group(group))
        django_user.is_staff = False
        django_user.first_name = first_name
        django_user.last_name = last_name
        return django_user

    def get_registration_activation_url(self, registration_profile):
        activation_url = reverse(
            "registration_activate",
            kwargs={"activation_key": registration_profile.activation_key})
        return make_full_url(activation_url)
