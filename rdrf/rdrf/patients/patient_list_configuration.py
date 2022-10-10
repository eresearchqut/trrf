import logging

from django.utils.translation import gettext_lazy as _

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.patients.patient_columns import ColumnFullName, ColumnDateOfBirth, ColumnCodeField, ColumnWorkingGroups, \
    ColumnDiagnosisProgress, ColumnDiagnosisCurrency, ColumnPatientStage, ColumnContextMenu, ColumnDateLastUpdated, \
    ColumnActionsMenu
from report.schema import to_camel_case

logger = logging.getLogger(__name__)


class PatientListConfiguration:

    AVAILABLE_COLUMNS = {
        'full_name': {'label': 'Patient', 'permission': 'patients.can_see_full_name', 'class': ColumnFullName},
        'date_of_birth': {'label': 'Date of Birth', 'permission': 'patients.can_see_dob', 'class': ColumnDateOfBirth},
        'code': {'label': 'Code', 'permission': 'patients.can_see_code_field', 'class': ColumnCodeField},
        'working_groups': {'label': 'Working Groups', 'permission': 'patients.can_see_working_groups', 'class': ColumnWorkingGroups},
        'diagnosis_progress': {'label': 'Diagnosis Entry Progress', 'permission': 'patients.can_see_diagnosis_progress', 'class': ColumnDiagnosisProgress},
        'diagnosis_currency': {'label': 'Updated < 365 days', 'permission': 'patients.can_see_diagnosis_currency', 'class': ColumnDiagnosisCurrency},
        'stage': {'label': 'Stage', 'permission': 'patients.can_see_data_modules', 'class': ColumnPatientStage, 'feature': RegistryFeatures.STAGES},
        'modules': {'label': 'Modules', 'permission': 'patients.can_see_data_modules', 'class': ColumnContextMenu},
        'last_updated_overall_at': {'label': 'Date Last Updated', 'permission': 'patients.can_see_last_updated_at', 'class': ColumnDateLastUpdated},
        'actions': {'label': 'Actions', 'permission': 'patients.delete_patient', 'class': ColumnActionsMenu},
    }

    AVAILABLE_FACETS = {
        "living_status": {'label': _('Living Status'), 'permission': 'patients.can_see_living_status', 'default': None},
        "working_groups": {'label': _('Working Groups'), 'permission': None, 'default': None}
    }

    DEFAULT_CONFIGURATION = {'columns': ['full_name', 'date_of_birth', 'code', 'working_groups', 'diagnosis_progress',
                                         'diagnosis_currency', 'stage', 'modules', 'actions'],
                             'facets': {}}

    def __init__(self, registry):
        self.registry = registry
        self.config = self._load_config()

    def _load_config(self):
        return self.registry.get_metadata_item('patient_list') or self.DEFAULT_CONFIGURATION

    @staticmethod
    def _get_item_key_and_config(config_item):
        if isinstance(config_item, str):
            return config_item, {}
        elif isinstance(config_item, dict):
            return next(iter(config_item.items()))
        else:
            raise 'Expected config item to be a string or a dict'

    def get_facets(self):
        configured_facets = {}

        registry_config_facets = self.config.get('facets', [])

        for facet_config_item in registry_config_facets:
            key, configured_facet = self._get_item_key_and_config(facet_config_item)
            if key in self.AVAILABLE_FACETS.keys():
                gql_key = to_camel_case(key)
                configured_facets[gql_key] = {**(self.AVAILABLE_FACETS[key]), **configured_facet}

        logger.debug(f'configured_facets: {configured_facets}')

        return configured_facets

    def get_columns(self):
        def get_column_config(key):
            return self.AVAILABLE_COLUMNS.get(key)

        columns = {}
        for column in self.config.get('columns', []):
            column_key, custom_config = self._get_item_key_and_config(column)
            column_config = get_column_config(column_key)

            # Ignore unsupported columns
            if not column_config:
                continue

            # Merge custom config with default config. Custom config takes precedence.
            column_config = {**column_config, **custom_config}

            # Early exit if this column requires a feature which is not enabled
            feature = column_config.get('feature', None)
            if feature and not self.registry.has_feature(feature):
                continue

            column_class = column_config.get('class')
            label = column_config.get('label')
            permission = column_config.get('permission')

            columns[column_key] = column_class(_(label), permission)

        return columns
