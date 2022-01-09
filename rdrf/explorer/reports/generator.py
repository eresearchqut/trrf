from explorer.report_configuration import REPORT_CONFIGURATION
from rdrf.schema.schema import schema
import pandas as pd
import json
import logging
import re

logger = logging.getLogger(__name__)

class Report:

    def __init__(self, report_design):
        self.report_design = report_design
        self.report_config = REPORT_CONFIGURATION['demographic_model']
        self.report_fields_lookup = self.__init_report_fields_lookup()

    def __init_report_fields_lookup(self):
        return {model: model_config['fields'] for model, model_config in self.report_config.items()}

    def __humanise_column_label(self, col):
        pivoted_field_labels = re.search(r'(.*)_(.*)_(.*)', col)
        if pivoted_field_labels:
            try:
                model = pivoted_field_labels.group(1)
                model_field = pivoted_field_labels.group(2)
                pivoted_value = pivoted_field_labels.group(3)
                model_label = self.report_config[model]['label']
                field_label = self.report_config[model]['fields'][model_field]
                label = f"{pivoted_value}_{model_label}_{field_label}"
            except Exception as e:
                logger.error(e)
                label = col
        else:
            label = self.report_fields_lookup['patient'].get(col)
        return label if label else col

    def __reformat_pivoted_column_labels(self, col):
        # Check for Nan
        if col != col: return col

        re_cfg_default_name = re.search(r'a\.cfg\.defaultName_(.*?)_(.*?)_', col)
        if re_cfg_default_name:
            label = f"{re_cfg_default_name.group(1)}_{re_cfg_default_name.group(2)}_Name"
        else:
            label = re.sub(r'b\.cde\.value_', "", col)
        return label

    def __get_graphql_query(self):

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

        # Build list of patient fields to report on
        patient_fields = ['id']
        patient_fields.extend(
            self.report_design.reportdemographicfield_set.filter(model='patient').values_list('field', flat=True))

        # Build list of other demographic fields to report on, group by model
        other_demographic_fields = {}
        for demographic_field in self.report_design.reportdemographicfield_set.exclude(model='patient'):
                other_demographic_fields.setdefault(demographic_field.model, []).append(demographic_field.field)

        related_demographic_fields_query = ""

        for model_name, fields in other_demographic_fields.items():
            pivot_field = self.report_config[model_name]['pivot_field']
            selected_fields = fields.copy() if pivot_field in fields else fields.copy() + pivot_field
            related_demographic_fields_query = \
f"""
        {related_demographic_fields_query}
       ,{model_name} {{
            {",".join(selected_fields)}
       }}
"""

        patient_query_params = [
            f'registryCode:"{self.report_design.registry.code}"',
            f"filters: [{','.join(get_patient_filters())}]",
            f"workingGroupIds: [{','.join(get_patient_working_group_filters())}]",
            ]

        cde_keys = [json.dumps(rcdf.cde_key) for rcdf in self.report_design.reportclinicaldatafield_set.all()]

        query = \
f"""
query {{
    allPatients({",".join(patient_query_params)}) {{
        {",".join(patient_fields)}
        {related_demographic_fields_query},
        clinicalData(cdeKeys: [{",".join(cde_keys)}])
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
        result = schema.execute(self.__get_graphql_query(), context_value=request)
        return json.dumps(result.data)

    def export_to_csv(self, request):
        result = schema.execute(self.__get_graphql_query(), context_value=request)

        def graphql_to_pandas_field(graphql_field):
            # E.g. for workingGroup {id}, matching groups: ["workingGroup", " {id} ", "id"]
            pandas_field = re.sub(r"\s", "", graphql_field)
            # replace " { field }" with ".field"
            pandas_field = re.sub(r"(.+)({(.*)})", r"\1.\3", pandas_field)
            return pandas_field

        data_allpatients = result.data['allPatients']

        # Build definition of report fields grouped by model
        report_fields = {'patient': ['id']}
        for df in self.report_design.reportdemographicfield_set.all():
            report_fields.setdefault(df.model, []).append(graphql_to_pandas_field(df.field))

        # Dynamically build a dataframe for each set of demographic data with 1:many or many:many relationship with patient
        dataframes = []
        for model, fields in report_fields.items():
            if model == 'patient':
                continue

            model_config = self.report_config[model]
            pivot_field = graphql_to_pandas_field(model_config['pivot_field'])
            record_prefix = f"{model}_"

            # Normalize the json data into a pandas dataframe following the record path for this specific related model
            dataframe = pd.json_normalize(data_allpatients, meta=['id'], record_path=[model],
                                          record_prefix=record_prefix)

            # Pivot on the configured field for this model
            pivot_cols = [f"{record_prefix}{pivot_field}"]
            dataframe = dataframe.pivot(index=['id'],
                                        columns=pivot_cols,
                                        values=[f"{record_prefix}{field}" for field in fields if field != pivot_field])

            dataframe = dataframe.sort_index(axis=1, level=pivot_cols, sort_remaining=False)
            dataframe.columns = dataframe.columns.to_series().str.join('_')
            dataframe.columns = dataframe.columns.to_series().str.replace('.', '_')
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
                               record_path=['clinicalData'],
                               meta=report_fields['patient'],
                               errors='ignore')

        # Capture clinical columns before this dataframe is merged with demographic data
        clinical_cols = df.columns

        # Merge clinical data dataframe with related demographic data dataframe
        if merged is not None:
            df = pd.merge(left=df, right=merged, on='id', how='outer')

        df.columns = df.columns.to_series().apply(self.__humanise_column_label)

        # Early exit if there is no clinical data included in the report
        if 'cde.value' not in df.columns and 'cde.values' not in df.columns:
            df.drop(columns=['cfg', 'form', 'section', 'sectionCnt', 'cde'], inplace=True)
            return df.to_csv()

        # Merge the value and values columns together so we can pivot it
        if 'cde.value' not in df.columns:
            df['cde.value'] = None
        if 'cde.values' in df.columns:
            df['cde.value'] = df['cde.value'].combine_first(df['cde.values'])

        # Capture the demographic cols required for the pivot index before we go and rename columns
        demographic_cols = [col for col in df.columns if col == 'id' or col not in clinical_cols]

        # Rename the columns being pivoted to occur alphabetically in the order desired in the output report
        # https://github.com/pandas-dev/pandas/issues/17041#issuecomment-317576297
        df.rename(inplace=True, columns={'cfg.defaultName': 'a.cfg.defaultName', 'cde.value': 'b.cde.value'})

        # Pivot the cde values by their uniquely identifying columns (context form group, form, section, cde)
        cde_pivot_cols = ['cfg.name', 'cfg.sortOrder', 'cfg.entryNum', 'form', 'section', 'sectionCnt', 'cde.name']
        pivoted = df.pivot(index=demographic_cols,
                           columns=cde_pivot_cols,
                           values=['a.cfg.defaultName', 'b.cde.value'])

        # Re-order the columns
        pivoted = pivoted.sort_index(axis=1, level=cde_pivot_cols)

        # Remove context form group's sort order as we don't need to see this in the results.
        pivoted = pivoted.droplevel('cfg.sortOrder', axis=1)

        # Flatten the column levels into one, and reformat labels
        pivoted.columns = pivoted.columns.to_series().str.join('_')
        pivoted.columns = pivoted.columns.to_series().apply(self.__reformat_pivoted_column_labels)

        # Remove null columns (caused by patients with no matching clinical data)
        pivoted = pivoted.loc[:, pivoted.columns.notnull()]
        # Remove duplicate columns (caused by repeated context form group's defaultName from how it's pivoted)
        pivoted = pivoted.loc[:, ~pivoted.columns.duplicated()]

        return pivoted.to_csv()