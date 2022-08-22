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

                logger.info(f'Assertion for user group: {group}, registry {user_registry}')
                self.assertEqual(user.default_page, expected_page)

        registry = Registry.objects.create(code='test')
        user = CustomUser.objects.create()

        page_dashboard_list = reverse('parent_dashboard_list')
        page_patientslisting = reverse('patientslisting')
        page_patient = reverse('registry:patient_page', args=[registry.code])
        page_parent = reverse('registry:parent_page', args=[registry.code])

        # Round 1 - Test default page without dashboards set
        test_cases = [(None, None, page_patientslisting),
                      (GROUPS.PATIENT, None, page_patientslisting),
                      (GROUPS.PATIENT, registry, page_patient),
                      (GROUPS.PARENT, None, page_patientslisting),
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
                      (GROUPS.PATIENT, None, page_patientslisting),
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

