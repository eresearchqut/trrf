import io
import json
import logging
import re

import pandas as pd
from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _
from rdrf.helpers.utils import models_from_mongo_key
from rdrf.models.definition.models import ContextFormGroup
from report.models import ReportCdeHeadingFormat
from report.schema.schema import schema

from gql_query_builder import GqlQuery

logger = logging.getLogger(__name__)


class Report:

    def __init__(self, report_design):
        self.report_design = report_design
        self.report_config = import_string(settings.REPORT_CONFIGURATION)['demographic_model']
        self.report_fields_lookup = self.__init_report_fields_lookup()

    def __init_report_fields_lookup(self):
        return {model: model_config['fields'] for model, model_config in self.report_config.items()}

    def __pandas_to_graphql_field(self, pandas_field):
        # E.g. for addressType_type, matching groups: ["addressType", "type"]
        regex = re.search(r'(.+?)_(.*)', pandas_field)
        if regex:
            # replace "_field" with "{ field }"
            graphql_field = f"{regex.group(1)} {{ {regex.group(2)} }}"
            return graphql_field
        else:
            return pandas_field

    def __humanise_column_label(self, col):
        label_groups = re.search(r'(.+?)_(.*)_(.*)', col)
        pivot_label = None
        if label_groups:
            pivot_label = f'{label_groups.group(3)}_'
        else:
            label_groups = re.search(r'(.*)_(.*)', col)

        if label_groups:
            try:
                model = label_groups.group(1)
                model_field = self.__pandas_to_graphql_field(label_groups.group(2))
                model_label = self.report_config[model]['label']
                field_label = self.report_config[model]['fields'][model_field]
                return f"{pivot_label or ''}{model_label}_{field_label}"
            except Exception as e:
                logger.error(e)
                return col
        else:
            return self.report_fields_lookup['patient'].get(col) or col

    def __reformat_pivoted_column_labels(self, col):
        # Check for Nan
        if col != col:
            return col

        re_cfg_default_name = re.search(r'a\.cfg\.defaultName_(.*?)_(.*?)_', col)
        if re_cfg_default_name:
            label = f"{re_cfg_default_name.group(1)}_{re_cfg_default_name.group(2)}_Name"
        else:
            label = re.sub(r'b\.cde\.value_', "", col)
        return label

    def __get_graphql_query(self, offset=None, limit=None):

        def get_patient_consent_question_filters():
            return [json.dumps(cq.code) for cq in self.report_design.filter_consents.all()]

        def get_patient_working_group_filters():
            return [f'"{str(wg.id)}"' for wg in self.report_design.filter_working_groups.all().order_by('id')]

        # Build Patient filters
        patient_filters = {
            'registryCode': f'"{self.report_design.registry.code}"',
            'consentQuestionCodes': f"[{','.join(get_patient_consent_question_filters())}]",
            'workingGroupIds': f"[{','.join(get_patient_working_group_filters())}]"
        }

        if offset:
            patient_filters['offset'] = offset

        if limit:
            patient_filters['limit'] = limit

        # Build simple patient demographic fields
        patient_fields = ['id']
        patient_fields.extend(
            self.report_design.reportdemographicfield_set.filter(model='patient').values_list('field', flat=True))

        # Build list of other demographic fields to report on, group by model
        other_demographic_fields = {}
        for demographic_field in self.report_design.reportdemographicfield_set.exclude(model='patient'):
            other_demographic_fields.setdefault(demographic_field.model, []).append(demographic_field.field)

        fields_nested_demographics = []
        for model_name, fields in other_demographic_fields.items():
            pivot_field = self.report_config[model_name].get('pivot_field', None)
            if pivot_field and pivot_field not in fields:
                selected_fields = fields.copy() + [pivot_field]
            else:
                selected_fields = fields.copy()
            fields_demographic = GqlQuery().fields(selected_fields).query(model_name).generate()
            fields_nested_demographics.append(fields_demographic)

        # Build Clinical data
        # TODO add sort_order to report_design model for clinicaldatafields rather than assuming it's safe to order by id
        cde_keys = [rcdf.cde_key for rcdf in self.report_design.reportclinicaldatafield_set.all().order_by('id')]

        # - create a dictionary to respectively group together cfg, form, sections by keys
        cfg_dicts = {}
        for key in cde_keys:
            logger.info(key)
            form,section,cde = models_from_mongo_key(self.report_design.registry, key)
            cfgs = ContextFormGroup.objects.filter(items__registry_form=form)
            for cfg in cfgs:
                cfg_dict = cfg_dicts.setdefault(cfg.code, {'is_fixed': cfg.is_fixed, 'forms': {}})
                form_dict = cfg_dict['forms'].setdefault(form.name, {'sections': {}})
                section_dict = form_dict['sections'].setdefault(section.code, {'cdes': []})
                section_dict['cdes'].append(cde.code)

        # - build the clinical data query
        fields_clinical_data = []
        for cfg_code, cfg in cfg_dicts.items():
            fields_form = []
            for form_name, form in cfg['forms'].items():
                fields_section = []
                for section_code, section in form['sections'].items():
                    field_section = GqlQuery().fields(section['cdes'], name=section_code).generate()
                    fields_section.append(field_section)

                if cfg['is_fixed']:
                    field_form = GqlQuery().fields(fields_section, name=form_name).generate()
                else:
                    field_data = GqlQuery().fields(fields_section, name='data').generate()
                    field_form = GqlQuery().fields(['key', field_data], name=form_name).generate()

                fields_form.append(field_form)

            field_cfg = GqlQuery().fields(fields_form, name=cfg_code).generate()
            fields_clinical_data.append(field_cfg)

        field_clinical_data = GqlQuery().fields(fields_clinical_data).query('clinicalData').generate()

        # Build query
        fields_patient = []
        fields_patient.extend(patient_fields)
        fields_patient.extend(fields_nested_demographics)
        fields_patient.append(field_clinical_data)
        return GqlQuery().fields(fields_patient).query('patients', input=patient_filters).operation().generate()

    def validate_for_csv_export(self):
        if self.report_design.cde_heading_format == ReportCdeHeadingFormat.CODE.value:
            return True, {}

        headings_dict = dict()

        for cde_key in list(self.report_design.reportclinicaldatafield_set.all().values_list('cde_key', flat=True)):
            form, section, cde = models_from_mongo_key(self.report_design.registry, cde_key)
            for cfg in ContextFormGroup.objects.filter(items__registry_form=form.id):
                col_header = ''

                if self.report_design.cde_heading_format == ReportCdeHeadingFormat.LABEL.value:
                    col_header = f'{cfg.name}_{form.nice_name}_{section.display_name}_{cde.name}'
                elif self.report_design.cde_heading_format == ReportCdeHeadingFormat.ABBR_NAME.value:
                    col_header = f'{cfg.abbreviated_name}_{form.abbreviated_name}_{section.abbreviated_name}_{cde.abbreviated_name}'

                headings_dict.setdefault(col_header, []).append(
                    {'cfg': cfg.code, 'form': form.nice_name, 'section': section.__str__(), 'cde': cde.__str__()})

        duplicate_headings = dict(filter(lambda item: len(item[1]) > 1, headings_dict.items()))

        return len(duplicate_headings) == 0, {'duplicate_headers': duplicate_headings}

    def export_to_json(self, request):

        limit = 20
        offset = 0

        while True:
            result = schema.execute(self.__get_graphql_query(offset=offset, limit=limit), context_value=request)
            all_patients = result.data['allPatients']
            num_patients = len(all_patients)
            offset += num_patients

            for patient in all_patients:
                patient_json = json.dumps(patient)
                yield f'{patient_json}\n'

            if num_patients < limit:
                break

    def export_to_csv(self, request):
        result = schema.execute(self.__get_graphql_query(), context_value=request)

        def graphql_to_pandas_field(graphql_field):
            if not graphql_field:
                return None
            # E.g. for workingGroup {id}, matching groups: ["workingGroup", " {id} ", "id"]
            pandas_field = re.sub(r"\s", "", graphql_field)
            # replace " { field }" with ".field"
            pandas_field = re.sub(r"(.+)({(.*)})", r"\1.\3", pandas_field)
            return pandas_field

        def get_cde_pivot_columns(cde_heading_format):
            if cde_heading_format == ReportCdeHeadingFormat.ABBR_NAME.value:
                return 'cfg.abbreviatedName', 'form.abbreviatedName', 'section.abbreviatedName', 'cde.abbreviatedName'
            if cde_heading_format == ReportCdeHeadingFormat.LABEL.value:
                return 'cfg.name', 'form.niceName', 'section.name', 'cde.name'
            if cde_heading_format == ReportCdeHeadingFormat.CODE.value:
                return 'cfg.code', 'form.name', 'section.code', 'cde.code'

            raise Exception(_('CDE Heading Format not supported.'))

        def stream_to_csv(dataframe):
            stream = io.StringIO()
            dataframe.to_csv(stream, chunksize=20)
            return stream

        data_allpatients = result.data['allPatients']

        # Build definition of report fields grouped by model
        report_fields = {'patient': ['id']}
        for df in self.report_design.reportdemographicfield_set.all():
            report_fields.setdefault(df.model, []).append(graphql_to_pandas_field(df.field))

        # Dynamically build a dataframe for each set of demographic related data
        dataframes = []
        for model, fields in report_fields.items():
            if model == 'patient':
                continue

            record_prefix = f"{model}_"
            model_config = self.report_config[model]
            pivot_field = graphql_to_pandas_field(model_config.get('pivot_field'))
            is_one_to_one = model_config.get('one_to_one', False)

            if is_one_to_one:
                # We can't use the record_path parameter of json_normalize because the data element for this model does not contain an array of items
                my_fields = ['id']
                my_fields.extend([f"{record_prefix}{field}" for field in fields])
                dataframe = pd.json_normalize(data_allpatients, meta=['id'])
                dataframe.columns = dataframe.columns.to_series().str.replace('.', '_')

                # Only take the columns that are relevant to this model, otherwise we end up with duplicates.
                dataframe = dataframe[my_fields]
            else:
                # Normalize the json data into a pandas dataframe following the record path for this specific related model
                dataframe = pd.json_normalize(data_allpatients, meta=['id'], record_path=[model], record_prefix=record_prefix)

                if pivot_field:
                    if not dataframe.empty:
                        pivot_cols = [f"{record_prefix}{pivot_field}"]
                        dataframe = dataframe.pivot(index=['id'],
                                                    columns=pivot_cols,
                                                    values=[f"{record_prefix}{field}" for field in fields])

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
            df.drop(columns=['cfg', 'form', 'section', 'cde'], inplace=True)
            return stream_to_csv(df)

        # Merge the value and values columns together so we can pivot it
        if 'cde.value' not in df.columns:
            df['cde.value'] = None
        if 'cde.values' in df.columns:
            df['cde.value'] = df['cde.value'].combine_first(df['cde.values'])

        # Capture the demographic cols required for the pivot index before we go and rename columns
        demographic_cols = [col for col in df.columns if col == 'id' or col not in clinical_cols]

        # Rename the columns being pivoted to occur alphabetically in the order desired in the output report
        # https://github.com/pandas-dev/pandas/issues/17041#issuecomment-317576297
        df.rename(inplace=True, columns={'cfg.defaultName': 'a.cfg.defaultName',
                                         'cde.value': 'b.cde.value'})

        # Pivot the cde values by their uniquely identifying columns (context form group, form, section, cde)
        cfg_name_col, form_name_col, section_name_col, cde_name_col = get_cde_pivot_columns(self.report_design.cde_heading_format)

        cde_pivot_cols = [cfg_name_col, 'cfg.sortOrder', 'cfg.entryNum', form_name_col, section_name_col, 'section.entryNum', cde_name_col]

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

        return stream_to_csv(pivoted)
