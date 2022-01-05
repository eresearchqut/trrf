from explorer.report_configuration import REPORT_CONFIGURATION
from rdrf.schema.schema import schema
import pandas as pd
import json
import logging
import re

logger = logging.getLogger(__name__)

class ReportColumn:
    def humanise_label(self):
            # TODO REFACTOR
            report_config = REPORT_CONFIGURATION['demographic_model']
            report_fields_lookup = {}
            for model, model_config in report_config.items():
                fields_keyed_by_value = dict((v, k) for k, v in model_config['fields'].items())
                report_fields_lookup[model] = fields_keyed_by_value

            fields_with_relations = re.search(r'(.*)_(.*)_(.*)', col)
            if fields_with_relations:
                try:
                    field_label = report_fields_lookup[fields_with_relations.group(2)].get(
                        fields_with_relations.group(3))
                    label = f"{fields_with_relations.group(1)}_{fields_with_relations.group(2)}_{field_label}"
                except Exception as e:
                    logger.error(e)
                    label = col
            else:
                label = report_fields_lookup['Patient'].get(col)
            return label if label else col

class Report:

    def __init__(self, report_design):
        self.report_design = report_design
        self.report_fields_lookup = self.__init_report_fields_lookup()

    def __init_report_fields_lookup(self):
        report_config = REPORT_CONFIGURATION['demographic_model']
        report_fields_lookup = {}
        for model, model_config in report_config.items():
            fields_keyed_by_value = dict((v, k) for k, v in model_config['fields'].items())
            report_fields_lookup[model] = fields_keyed_by_value
        return report_fields_lookup

    def humanise_column_label(self, col):
        pivoted_field_labels = re.search(r'(.*)_(.*)_(.*)', col)
        if pivoted_field_labels:
            try:
                model = pivoted_field_labels.group(1)
                model_field = pivoted_field_labels.group(2)
                pivoted_value = pivoted_field_labels.group(3)
                model_field_label = self.report_fields_lookup[model].get(model_field)
                label = f"{pivoted_value}_{model}_{model_field_label}"
            except Exception as e:
                logger.error(e)
                label = col
        else:
            label = self.report_fields_lookup['Patient'].get(col)
        return label if label else col

    def get_graphql_query(self):

        def get_patient_filters():
            patient_filters = []

            if self.report_design.filter_consents.all():
                patient_filters.append(f'"consents__answer=True"')
                patient_filters.extend(
                    [f'"consents__consent_question__code={consent_question.code}"' for consent_question in
                     self.report_design.filter_consents])

            return patient_filters

        def get_patient_working_group_filters():
            wg_filters = []
            if self.report_design.filter_working_groups.all():
                wg_filters = [json.dumps(str(wg.id)) for wg in self.report_design.filter_working_groups]

            return wg_filters

        patient_fields = ['id']
        other_demographic_fields = {}

        # Separate patient fields from other related to patient fields.
        for demographic_field in self.report_design.demographicfield_set.all():
            field_dict = json.loads(demographic_field.field)
            model_name = field_dict['model']

            if model_name == 'Patient':
                patient_fields.append(field_dict['field'])
            else:
                other_demographic_fields.setdefault(model_name, []).append(field_dict)

        related_demographic_fields_query = ""

        for model_name, fields in other_demographic_fields.items():
            model_config = REPORT_CONFIGURATION['demographic_model'][model_name]
            pivot_field = model_config['pivot_field']
            selected_fields = [field_dict['field'] for field_dict in fields]
            if pivot_field not in selected_fields:
                selected_fields.append(pivot_field)
            related_demographic_fields_query = \
f"""
        {related_demographic_fields_query}
       ,{model_config['model_field_lookup']} {{
            {",".join(selected_fields)}
       }}
"""

        logger.info(related_demographic_fields_query)

        patient_query_params = [
            f'registryCode:"{self.report_design.registry.code}"',
            f"filters: [{','.join(get_patient_filters())}]",
            f"workingGroupIds: [{','.join(get_patient_working_group_filters())}]",
            ]

        cde_keys = []
        for cde_field in self.report_design.cdefield_set.all():
            cde_field_dict = json.loads(cde_field.field)
            cde_keys.append(json.dumps(cde_field_dict['cde_key']))

        query = \
f"""
query {{
    allPatients({",".join(patient_query_params)}) {{
        {",".join(patient_fields)}
        {related_demographic_fields_query},
        clinicalDataFlat(cdeKeys: [{",".join(cde_keys)}])
            {{cfg {{name, defaultName, sortOrder, entryNum}}, form, section, sectionCnt,
            cde {{
                name
                ... on ClinicalDataCde {{value}}
                ... on ClinicalDataCdeMultiValue {{values}}
            }} 
        }}
    }}
}}
"""
        return query

    def export_to_json(self, request):
        result = schema.execute(self.get_graphql_query(), context_value=request)
        logger.debug(result)
        return json.dumps(result.data)

    def export_to_csv(self, request):
        result = schema.execute(self.get_graphql_query(), context_value=request)

        def graphql_to_pandas_field(graphql_field):
            # E.g. for workingGroup {id}, matching groups: ["workingGroup", " {id} ", "id"]
            pandas_field = re.sub(r"\s", "", graphql_field)
            # replace " { field }" with ".field"
            pandas_field = re.sub(r"(.+)({(.*)})", r"\1.\3", pandas_field)
            return pandas_field

        data_allpatients = result.data['allPatients']

        # Build definition of report fields grouped by model
        report_fields = {'Patient': ['id']}
        for df in self.report_design.demographicfield_set.all():
            df_dict = json.loads(df.field)
            model_name = df_dict['model']
            field = df_dict['field']
            report_fields.setdefault(model_name, []).append(graphql_to_pandas_field(field))

        # Dynamically build a dataframe for each set of demographic data with 1:many or many:many relationship with patient
        dataframes = []
        for model, fields in report_fields.items():
            if model == 'Patient':
                continue

            model_config = REPORT_CONFIGURATION['demographic_model'][model]
            model_lookup = model_config['model_field_lookup']
            pivot_field = graphql_to_pandas_field(model_config['pivot_field'])
            record_prefix = f"{model}_"

            # Normalize the json data into a pandas dataframe following the record path for this specific related model
            dataframe = pd.json_normalize(data_allpatients, meta=['id'], record_path=[model_lookup],
                                          record_prefix=record_prefix)

            # Pivot on the configured field for this model
            pivot_cols = [f"{record_prefix}{pivot_field}"]
            dataframe = dataframe.pivot(index=['id'],
                                        columns=pivot_cols,
                                        values=[f"{record_prefix}{field}" for field in fields if field != pivot_field])

            dataframe = dataframe.sort_index(axis=1, level=pivot_cols, sort_remaining=False)
            dataframe.columns = dataframe.columns.to_series().str.join('_')
            dataframe.columns = dataframe.columns.to_series().str.replace('.', '_')
            dataframe.reset_index(inplace=True)
            dataframes.append(dataframe)

        # Merge all the dynamically built dataframes into one (merged)
        merged = None
        for df in dataframes:
            if merged is None:
                merged = df
            else:
                merged = pd.merge(left=merged, right=df, on='id', how='outer')

        # Normalise the rest of the patient and clinical data
        df = pd.json_normalize(data_allpatients,
                               record_path=['clinicalDataFlat'],
                               meta=report_fields['Patient'],
                               errors='ignore')

        # Capture clinical columns before this dataframe is merged with demographic data
        clinical_cols = df.columns

        # Merge clinical data dataframe with related demographic data dataframe
        if merged is not None:
            df = pd.merge(left=df, right=merged, on='id', how='outer')

        df.columns = df.columns.to_series().apply(self.humanise_column_label)

        # Early exit if there is no clinical data included in the report
        if 'cde.value' not in df.columns and 'cde.values' not in df.columns:
            df.drop(columns=['cfg', 'form', 'section', 'sectionCnt', 'cde'], inplace=True)
            return df.to_csv()

        # Merge the value and values columns together so we can pivot it
        if 'cde.value' not in df.columns:
            df['cde.value'] = None
        if 'cde.values' in df.columns:
            df['cde.value'] = df['cde.value'].combine_first(df['cde.values'])

        # Pivot the cde values by their uniquely identifying columns (context form group, form, section, cde)
        # TODO figure out how to get the context form group 'defaultName' to display as expected **  Currently working on this

        pivoted = df.pivot(index=[col for col in df.columns if col not in clinical_cols],
                           columns=['cfg.name', 'cfg.sortOrder', 'cfg.entryNum', 'form', 'section', 'sectionCnt',
                                    'cde.name'],
                           values=['cfg.defaultName', 'cde.value'])
        logger.info('** pivoted DF COLUMNS **')
        logger.info(pivoted.columns)
        # Re-order the columns
        pivoted = pivoted.sort_index(axis=1, level=['cfg.sortOrder', 'cfg.entryNum', 'form', 'section', 'sectionCnt',
                                                    'cde.name'])
        logger.info('** resorted DF COLUMNS **')
        logger.info(pivoted.columns)


        # Remove context form group's sort order as we don't need to see this in the results.
        pivoted = pivoted.droplevel('cfg.sortOrder', axis=1)

        # Flatten the column levels into one
        def fix_pivoted_column_labels(col):
            # Check for Nan
            if col != col: return col

            re_cfg_default_name = re.search(r'cfg\.defaultName_(.*?)_(.*?)_', col)
            if re_cfg_default_name:
                label = f"{re_cfg_default_name.group(1)}_{re_cfg_default_name.group(2)}_Name"
            else:
                label = re.sub(r'cde\.value_', "", col)
            return label

        pivoted.columns = pivoted.columns.to_series().str.join('_')
        pivoted.columns = pivoted.columns.to_series().apply(fix_pivoted_column_labels)
        pivoted.reset_index(inplace=True)

        # Remove null columns (caused by patients with no matching clinical data)
        pivoted = pivoted.loc[:, pivoted.columns.notnull()]
        # Remove duplicate columns (caused by repeated context form group's defaultName from how it's pivoted)
        pivoted = pivoted.loc[:, ~pivoted.columns.duplicated()]

        return pivoted.to_csv()