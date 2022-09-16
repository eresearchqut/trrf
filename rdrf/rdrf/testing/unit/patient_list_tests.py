from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry
from rdrf.patients.patient_columns import ColumnFullName
from rdrf.patients.patient_list_configuration import PatientListConfiguration
from rdrf.testing.unit.tests import RDRFTestCase


class PatientListTests(RDRFTestCase):
    def setUp(self):
        self.registry = Registry.objects.get(code='reg1')

    def testDefaultConfigurationWhenNoCustomConfigurationIsDefined(self):
        config_columns = PatientListConfiguration(self.registry).config.get('columns')
        self.assertEqual(config_columns,
                         ['full_name', 'date_of_birth', 'code', 'working_groups', 'diagnosis_progress',
                          'diagnosis_currency', 'stage', 'modules', 'actions'])

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
        self.assertEqual([(key, c.__class__.__name__, c.label, c.perm) for key, c in columns.items()],
                         [('full_name', 'ColumnFullName', 'Full name', 'patients.can_see_full_name'),
                          ('date_of_birth', 'ColumnDateOfBirth', 'Date of Birth', 'patients.can_see_dob')])

        self.registry.add_feature(RegistryFeatures.STAGES)
        columns = PatientListConfiguration(self.registry).get_columns()
        self.assertEqual([(key, c.__class__.__name__, c.label, c.perm) for key, c in columns.items()],
                         [('full_name', 'ColumnFullName', 'Full name', 'patients.can_see_full_name'),
                          ('stage', 'ColumnPatientStage', 'Stage', 'patients.can_see_data_modules'),
                          ('date_of_birth', 'ColumnDateOfBirth', 'Date of Birth', 'patients.can_see_dob')])

    def testGetFacetsWhenNoCustomFacetsDefined(self):
        registry_config = PatientListConfiguration(self.registry)
        self.assertEqual(registry_config.get_facets(), {})

    def testExtensibilityOfPatientListConfiguration(self):
        class ExtendPatientListConfiguration(PatientListConfiguration):
            def __init__(self, registry):
                super().__init__(registry)
                self.AVAILABLE_COLUMNS = {**self.AVAILABLE_COLUMNS, **{
                    'full_name_2': {'label': 'Full Name', 'permission': 'patients.can_see_full_name',
                                    'class': ColumnFullName}
                }}

        self.registry.metadata_json = '{"patient_list": {"columns": [{"full_name": {"label": "Full name"}}, {"full_name_2": {"label": "Full name"}}]}}'
        self.registry.save()

        base_patient_list = PatientListConfiguration(self.registry)
        extended_patient_list = ExtendPatientListConfiguration(self.registry)

        self.assertEqual(len(base_patient_list.get_columns().keys()), 1)
        self.assertEqual(len(extended_patient_list.get_columns().keys()), 2)
