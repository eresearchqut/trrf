import json
import logging
import re

import pandas as pd

from explorer.models import ReportDesign
from explorer.report_configuration import REPORT_CONFIGURATION
from explorer.reports.generator import Report
from rdrf.schema.schema import schema

logger = logging.getLogger(__name__)


def export_to_csv(report):
    # TODO replace db field names with human readable names
    def convert_query_field_to_column_label(query_field):
        # E.g. for workingGroup {id}
        # group 1 = "workingGroup"
        # group 2 = " {id} "
        # group 3 = "id"
        regex = re.compile(r"(.+)({(.*)})")
        # Get rid of any spaces
        query_field = re.sub(r"\s", "", query_field)
        # replace " { field }" with ".field"
        query_field = regex.sub(r"\1.\3", query_field)
        return query_field


    result = schema.execute(report.get_graphql_query())

    data_allpatients = result.data['allPatients']

    report_fields = {'Patient': ['id']}

    for df in report.report_design.demographicfield_set.all():
        df_dict = json.loads(df.field)
        model_name = df_dict['model']
        field = df_dict['field']
        report_fields.setdefault(model_name, []).append(convert_query_field_to_column_label(field))

    # Step 1 - Build a single dataframe of demographic data with 1:many or many:many relationship with patient
    dataframes = []

    for model, fields in report_fields.items():
        if model == 'Patient':
            continue

        model_cfg = REPORT_CONFIGURATION['demographic_model'][model]
        model_lookup = model_cfg['model_field_lookup']
        pivot_field = convert_query_field_to_column_label(model_cfg['pivot_field'])

        dataframe = pd.json_normalize(data_allpatients, meta=['id'], record_path=[model_lookup], record_prefix=model_lookup)
        pivot_cols = [f"{model_lookup}{pivot_field}"]
        dataframe = dataframe.pivot(index=['id'],
                                    columns=pivot_cols,
                                    values=[f"{model_lookup}{field}" for field in fields if field != pivot_field])

        dataframe = dataframe.sort_index(axis=1, level=pivot_cols, sort_remaining=False)
        def suffix_to_prefix(col):
            return re.sub(r'(.*)(_(.*))', r'\3_\1', col)

        dataframe.columns = dataframe.columns.to_series().str.join('_')
        dataframe.columns = dataframe.columns.to_series().str.replace('.', '_')
        dataframe.columns = dataframe.columns.to_series().apply(suffix_to_prefix)
        dataframe.reset_index(inplace=True)
        dataframes.append(dataframe)


    merged = None
    for df in dataframes:
        if merged is None:
            merged = df
        else:
            merged = pd.merge(left=merged, right=df, on='id', how='outer')

    # Step 2 - Clinical Data
    df = pd.json_normalize(data_allpatients,
                           record_path=['clinicalDataFlat'],
                           meta=report_fields['Patient'],
                           errors='ignore')

    demographic_field_cols = []
    demographic_field_cols.extend(report_fields['Patient'])

    if merged is not None:
        demographic_field_cols.extend(list(merged.columns))
        df = pd.merge(left=df, right=merged, on='id', how='outer')
        # df = pd.merge(left=df, right=merged, on='id')

    from collections import OrderedDict
    demographic_field_cols = list(OrderedDict((x, True) for x in demographic_field_cols).keys())
    # logger.info(demographic_field_cols)

    # Early exit if report does not contain any clinical data
    if 'cde.value' not in df.columns and 'cde.values' not in df.columns:
        df.drop(columns=['cfg', 'form', 'section', 'sectionCnt', 'cde'], inplace=True)
        return df.to_csv()

    # Merge the value and values columns together
    if 'cde.value' not in df.columns:
        df['cde.value'] = None
    if 'cde.values' in df.columns:
        df['cde.value'] = df['cde.value'].combine_first(df['cde.values'])

    # Pivot the cde values by their uniquely identifying columns (context form group, form, section, cde)
    pivoted = df.pivot(index=demographic_field_cols,
                       columns=['cfg.name', 'cfg.sortOrder', 'cfg.entryNum', 'form', 'section', 'sectionCnt',
                                'cde.code'],
                       values=['cde.value'])

    # Re-order the columns
    pivoted = pivoted.sort_index(axis=1, level=['cfg.sortOrder', 'cfg.entryNum', 'form', 'section', 'sectionCnt',
                                                'cde.code'])

    # Remove context form group's sort order as we don't need to see this in the results.
    pivoted = pivoted.droplevel('cfg.sortOrder', axis=1)

    # Flatten the column levels into one
    pivoted.columns = pivoted.columns.to_series().str.join('_')
    pivoted.columns = pivoted.columns.to_series().str.lstrip('cde.value_')
    pivoted.reset_index(inplace=True)

    # Remove null columns (caused by patients with no matching clinical data)
    pivoted = pivoted.loc[:, pivoted.columns.notnull()]

    return pivoted.to_csv()

report = Report(report_design=ReportDesign.objects.get(id=7))
csv = export_to_csv(report)
logger.info(csv)


