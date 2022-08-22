import uuid

from django.test import TestCase

from rdrf.models.definition.models import RegistryDashboard, Registry
from registry.groups.models import CustomUser
from registry.groups import GROUPS as RDRF_GROUPS
from registry.patients.models import Patient, ParentGuardian


def list_dashboards(user):
    return list(RegistryDashboard.objects.filter_user_parent_dashboards(user).all())


class RegistryDashboardManagerTest(TestCase):
    def setUp(self):
        def create_valid_patient():
            return Patient.objects.create(consent=True, date_of_birth='1999-12-12')

        def create_user_with_group(group):
            user = CustomUser.objects.create(username=uuid.uuid1())
            user.add_group(group)
            return user

        # Registries
        self.registry_A = Registry.objects.create(code='A')
        self.registry_B = Registry.objects.create(code='B')
        self.registry_C = Registry.objects.create(code='C')

        # Dashboards
        self.dashboard_registry_A = RegistryDashboard.objects.create(registry=self.registry_A)
        self.dashboard_registry_B = RegistryDashboard.objects.create(registry=self.registry_B)

        # Patients
        self.patient1 = create_valid_patient()
        self.patient2 = create_valid_patient()
        self.patient3 = create_valid_patient()
        self.patient4 = create_valid_patient()

        self.patient1.rdrf_registry.set([self.registry_A])
        self.patient2.rdrf_registry.set([self.registry_A])

        self.patient3.rdrf_registry.set([self.registry_B])
        self.patient4.rdrf_registry.set([self.registry_C])

        self.parent_user = create_user_with_group(RDRF_GROUPS.PARENT)
        self.patient_user = create_user_with_group(RDRF_GROUPS.PATIENT)
        self.carer_user = create_user_with_group(RDRF_GROUPS.CARER)

    def test_get_dashboards_for_parent_user(self):
        parent = ParentGuardian.objects.create(user=self.parent_user)

        # Parent has one child, in a registry, with a dashboard.
        parent.patient.set([self.patient1])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_A])

        parent.patient.set([self.patient3])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_B])

        # Parent has one child, in a registry, with no dashboard
        parent.patient.set([self.patient4])
        self.assertEqual(list_dashboards(parent.user), [])

        # Parent has multiple children, all in one registry, with a dashboard
        parent.patient.set([self.patient1, self.patient2])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_A])

        # Parent has multiple children, in different registries, all with a dashboard
        parent.patient.set([self.patient1, self.patient3])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_A, self.dashboard_registry_B])

        # Parent has multiple children, in different registries, only one with a dashboard
        parent.patient.set([self.patient3, self.patient4])
        self.assertEqual(list_dashboards(parent.user), [self.dashboard_registry_B])

    def test_dashboards_for_other_users(self):
        self.patient1.carer = self.carer_user
        self.assertEqual(list_dashboards(self.carer_user), [])

        self.patient1.user = self.patient_user
        self.assertEqual(list_dashboards(self.patient_user), [])
