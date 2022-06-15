from unittest import TestCase

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry
from rdrf.patients.patient_columns import ColumnFullName, ColumnDateOfBirth
from rdrf.patients.patient_list_configuration import PatientListConfiguration
from rdrf.testing.unit.tests import RDRFTestCase


class PatientListTests(RDRFTestCase):
    def setUp(self):
        self.registry = Registry.objects.get(code='reg1')

    def testDefaultConfigurationWhenNoCustomConfigurationIsDefined(self):
        config_columns = PatientListConfiguration(self.registry).config.get('columns')
        self.assertEqual(config_columns,
                         ['full_name', 'date_of_birth', 'code', 'working_groups', 'diagnosis_progress',
                          'diagnosis_currency', 'stage', 'modules'])

    def testCustomConfiguration(self):
        self.registry.metadata_json = '{"patient_list": {"columns": ["full_name", "stage", "date_of_birth"]}}'
        self.registry.save()
        config_columns = PatientListConfiguration(self.registry).config.get('columns')
        self.assertEqual(config_columns,
                         ['full_name', 'stage', 'date_of_birth'])

    def testPatientListColumns(self):
        self.registry.metadata_json = '{"patient_list": {"columns": [{"full_name": {"label": "Full name"}}, "stage", "date_of_birth"]}}'
        self.registry.save()
        columns = PatientListConfiguration(self.registry).get_columns()
        self.assertEqual([(c.__class__.__name__, c.label, c.perm) for c in columns],
                         [('ColumnFullName', 'Full name', 'patients.can_see_full_name'),
                          ('ColumnDateOfBirth', 'Date of Birth', 'patients.can_see_dob')])

        self.registry.add_feature(RegistryFeatures.STAGES)
        columns = PatientListConfiguration(self.registry).get_columns()
        self.assertEqual([(c.__class__.__name__, c.label, c.perm) for c in columns],
                         [('ColumnFullName', 'Full name', 'patients.can_see_full_name'),
                          ('ColumnPatientStage', 'Stage', 'patients.can_see_data_modules'),
                          ('ColumnDateOfBirth', 'Date of Birth', 'patients.can_see_dob')])
