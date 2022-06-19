import logging

from django.utils.translation import ugettext_lazy as _

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.patients.patient_columns import ColumnFullName, ColumnDateOfBirth, ColumnCodeField, ColumnWorkingGroups, \
    ColumnDiagnosisProgress, ColumnDiagnosisCurrency, ColumnPatientStage, ColumnContextMenu, ColumnLivingStatus, \
    ColumnDateLastUpdated

logger = logging.getLogger(__name__)


class PatientListConfiguration:

    def __init__(self, registry):
        self.registry = registry
        self.config = self._load_config()
        logger.debug(f'Loaded config for registry {self.registry}: {self.config}')

    def _get_available_columns(self):
        return {
            'columns': {
                'full_name': {'label': 'Patient', 'permission': 'patients.can_see_full_name', 'class': ColumnFullName},
                'date_of_birth': {'label': 'Date of Birth', 'permission': 'patients.can_see_dob', 'class': ColumnDateOfBirth},
                'code': {'label': 'Code', 'permission': 'patients.can_see_code_field', 'class': ColumnCodeField},
                'working_groups': {'label': 'Working Groups', 'permission': 'patients.can_see_working_groups', 'class': ColumnWorkingGroups},
                'diagnosis_progress': {'label': 'Diagnosis Entry Progress', 'permission': 'patients.can_see_diagnosis_progress', 'class': ColumnDiagnosisProgress},
                'diagnosis_currency': {'label': 'Updated < 365 days', 'permission': 'patients.can_see_diagnosis_currency', 'class': ColumnDiagnosisCurrency},
                'stage': {'label': 'Stage', 'permission': 'patients.can_see_data_modules', 'class': ColumnPatientStage, 'feature': RegistryFeatures.STAGES},
                'modules': {'label': 'Modules', 'permission': 'patients.can_see_data_modules', 'class': ColumnContextMenu},
                'last_updated_overall_at': {'label': 'Date Last Updated', 'permission': 'patients.can_see_last_updated_at', 'class': ColumnDateLastUpdated},
                'living_status': {'label': 'Living Status', 'permission': 'patients.can_see_living_status', 'class': ColumnLivingStatus},
            }
        }

    def _get_available_facets(self):
        return ['living_status']

    def _default_patient_list_configuration(self):
        return {'columns': ['full_name', 'date_of_birth', 'code', 'working_groups', 'diagnosis_progress',
                            'diagnosis_currency', 'stage', 'modules']}

    def _load_config(self):
        return self.registry.get_metadata_item('patient_list') or self._default_patient_list_configuration()

    def get_facets(self):
        # Expecting facets to be defined as: {"living_status": {"default": "Alive"}}
        facets = {key: value for key, value in self.config.get('facets', {}).items()
                  if key in self._get_available_facets()}
        logger.debug(f'facets={facets}')
        return facets

    def get_columns(self):
        def get_column_key_and_config(column):
            if isinstance(column, str):
                return column, None
            elif isinstance(column, dict):
                return next(iter(column.items()))
            else:
                raise 'Expected column config to be a string or a dict'

        def get_column_config(key):
            return self._get_available_columns().get('columns', {}).get(key)

        columns = []
        for column in self.config.get('columns', []):
            column_key, custom_config = get_column_key_and_config(column)
            column_config = get_column_config(column_key)

            # Ignore unsupported columns
            if not column_config:
                continue

            # Merge custom config with default config. Custom config takes precedence.
            if custom_config:
                column_config = {**column_config, **custom_config}

            # Early exit if this column requires a feature which is not enabled
            feature = column_config.get('feature', None)
            if feature and not self.registry.has_feature(feature):
                continue

            column_class = column_config.get('class')
            label = column_config.get('label')
            permission = column_config.get('permission')

            columns.append(column_class(_(label), permission))

        return columns
