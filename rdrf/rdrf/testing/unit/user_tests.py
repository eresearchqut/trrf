import logging

from django.test import TestCase
from django.urls import reverse

from rdrf.models.definition.models import Registry, RegistryDashboard
from registry.groups import GROUPS
from registry.groups.models import CustomUser
from registry.patients.models import ParentGuardian, Patient

logger = logging.getLogger(__name__)


class CustomUserTest(TestCase):
    def test_get_full_name(self):
        # Standard User
        user = CustomUser.objects.create(first_name='Valerie', last_name='Brother')
        self.assertEqual(user.get_full_name(), 'Valerie Brother')

        # User that is a parent, but ParentGuardian object doesn't exist
        user.add_group(GROUPS.PARENT)
        self.assertEqual(user.get_full_name(), 'Valerie Brother')

        # User that is a parent, ParentGuardian has been configured
        ParentGuardian.objects.create(first_name='Valorie', last_name='Sister', user=user)
        self.assertEqual(user.get_full_name(), 'Valorie Sister')

    def test_default_page(self):
        def _execute_test_cases(test_cases):
            for test_case in test_cases:
                group, user_registry, expected_page = test_case
                user.groups.clear()
                if group:
                    user.add_group(group)

                user.registry.clear()
                if user_registry:
                    user.registry.set([user_registry])

                self.assertEqual(user.default_page, expected_page, f"{group=} {user_registry=}")

        registry = Registry.objects.create(code='test')
        user = CustomUser.objects.create()
        Patient.objects.create(consent=True, date_of_birth='1980-01-02', user=user)

        page_landing = reverse('landing')
        page_dashboard_list = reverse('parent_dashboard_list')
        page_patientslisting = reverse('patientslisting')
        page_patient = reverse('registry:patient_page', args=[registry.code])
        page_parent = reverse('registry:parent_page', args=[registry.code])

        # Round 1 - Test default page without dashboards set
        test_cases = [(None, None, page_patientslisting),
                      (GROUPS.PATIENT, None, page_landing),
                      (GROUPS.PATIENT, registry, page_patient),
                      (GROUPS.PARENT, None, page_landing),
                      (GROUPS.PARENT, registry, page_parent),
                      (GROUPS.CLINICAL, None, page_patientslisting),
                      (GROUPS.CARER, None, page_patientslisting),
                      (GROUPS.SUPER_USER, None, page_patientslisting),
                      (GROUPS.WORKING_GROUP_CURATOR, None, page_patientslisting),
                      (GROUPS.WORKING_GROUP_STAFF, None, page_patientslisting),
                      ]

        _execute_test_cases(test_cases)

        # Round 2 - Test default page when dashboard exists for the registry but not relevant to the user
        RegistryDashboard.objects.create(registry=registry)
        _execute_test_cases(test_cases)

        # Round 3 - Test default page when dashboard exists for the registry but not relevant to the user
        parent = ParentGuardian.objects.create(user=user)
        patient = Patient.objects.create(consent=True, date_of_birth='1980-01-02')
        patient.rdrf_registry.set([registry])
        parent.patient.set([patient])

        test_cases = [(None, None, page_patientslisting),
                      (GROUPS.PATIENT, None, page_landing),
                      (GROUPS.PATIENT, registry, page_patient),
                      (GROUPS.PARENT, None, page_dashboard_list),
                      (GROUPS.PARENT, registry, page_dashboard_list),
                      (GROUPS.CLINICAL, None, page_patientslisting),
                      (GROUPS.CARER, None, page_patientslisting),
                      (GROUPS.SUPER_USER, None, page_patientslisting),
                      (GROUPS.WORKING_GROUP_CURATOR, None, page_patientslisting),
                      (GROUPS.WORKING_GROUP_STAFF, None, page_patientslisting),
                      ]

        _execute_test_cases(test_cases)


class GroupTest(TestCase):
    GROUP_ATTRS = [
        "is_patient",
        "is_parent",
        "is_carrier",
        "is_carer",
        "is_patient_or_delegate",
        "is_clinician",
        "is_working_group_staff",
        "is_curator",
    ]

    def _test_group_attrs(self, groups, attrs):
        user = CustomUser.objects.create(username="_".join(groups))
        for group in groups:
            user.add_group(group)
        user.save()

        for attr in attrs:
            self.assertEqual(getattr(user, attr), True, attr)

        for attr in self.GROUP_ATTRS:
            if attr not in attrs:
                self.assertEqual(getattr(user, attr), False, attr)

    def test_patient(self):
        self._test_group_attrs([GROUPS.PATIENT], ["is_patient", "is_patient_or_delegate"])

    def test_parent(self):
        self._test_group_attrs([GROUPS.PARENT], ["is_parent", "is_patient_or_delegate"])

    def test_carrier(self):
        self._test_group_attrs([GROUPS.CARRIER], ["is_carrier", "is_patient_or_delegate"])

    def test_carer(self):
        self._test_group_attrs([GROUPS.CARER], ["is_carer", "is_patient_or_delegate"])

    def test_clinician(self):
        self._test_group_attrs([GROUPS.CLINICAL], ["is_clinician"])

    def test_working_group_staff(self):
        self._test_group_attrs([GROUPS.WORKING_GROUP_STAFF], ["is_working_group_staff"])

    def test_curator(self):
        self._test_group_attrs([GROUPS.WORKING_GROUP_CURATOR], ["is_curator"])

    def test_custom_group(self):
        self._test_group_attrs(["custom_group"], [])

    def test_patient_with_custom_group(self):
        self._test_group_attrs([GROUPS.PATIENT, "custom_group"], ["is_patient", "is_patient_or_delegate"])

    def test_group_like(self):
        self._test_group_attrs(["patients1"], [])
