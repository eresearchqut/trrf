import codecs
import csv
import io
import json
import logging
import re
from collections import OrderedDict
from importlib import import_module

from django.conf import settings
from flatten_json import flatten
from gql_query_builder import GqlQuery

from rdrf.helpers.utils import models_from_mongo_key, BadKeyError
from rdrf.models.definition.models import ContextFormGroup
from report.models import ReportCdeHeadingFormat
from report.clinical_data_csv_util import ClinicalDataCsvUtil
from report.schema import create_dynamic_schema, get_schema_field_name

logger = logging.getLogger(__name__)


class ReportBuilder:

    def __init__(self, report_design):
        self.report_design = report_design
        self.report_config = self.__load_report_configuration()
        self.report_fields_lookup = self.__init_report_fields_lookup()
        self.patient_filters = self.__init_patient_filters()
        self.schema = create_dynamic_schema()

    def __load_report_configuration(self):
        report_config_module = import_module(settings.REPORT_CONFIG_MODULE)
        get_report_config_func = getattr(report_config_module, settings.REPORT_CONFIG_METHOD_GET)
        report_configuration = get_report_config_func()
        return report_configuration['demographic_model']

    def __init_report_fields_lookup(self):
        return {model: model_config['fields'] for model, model_config in self.report_config.items()}

    def __init_patient_filters(self):
        def get_patient_consent_question_filters():
            return [json.dumps(cq.code) for cq in self.report_design.filter_consents.all()]

        def get_patient_working_group_filters():
            return [f'"{str(wg.id)}"' for wg in self.report_design.filter_working_groups.all().order_by('id')]

        return {
            'registryCode': f'"{self.report_design.registry.code}"',
            'consentQuestionCodes': f"[{','.join(get_patient_consent_question_filters())}]",
            'workingGroupIds': f"[{','.join(get_patient_working_group_filters())}]"
        }

    def __get_variants(self, lookup_key, request=None):
        query = GqlQuery().fields([lookup_key]).query('dataSummary',
                                                      input=self.patient_filters).operation().generate()
        summary_result = self.schema.execute(query, context_value=request)
        return summary_result.data['dataSummary'][lookup_key]

    def __get_graphql_query(self, offset=None, limit=None):

        # Build Patient filters
        patient_filters = self.patient_filters.copy()
        if offset:
            patient_filters['offset'] = offset

        if limit:
            patient_filters['limit'] = limit

        # Build simple patient demographic fields
        patient_fields = []
        patient_fields.extend(
            self.report_design.reportdemographicfield_set.filter(model='patient').values_list('field', flat=True))

        # Build list of other demographic fields to report on, group by model
        other_demographic_fields = {}
        for demographic_field in self.report_design.reportdemographicfield_set.exclude(model='patient'):
            other_demographic_fields.setdefault(demographic_field.model, []).append(demographic_field.field)

        fields_nested_demographics = []
        for model_name, fields in other_demographic_fields.items():
            model_config = self.report_config[model_name]
            if model_config.get('pivot', False):
                # Lookup the variants of this item which will form the column header groupings
                # e.g. for consents, returns a list of the unique consent codes
                column_headers = self.__get_variants(model_config.get('variant_lookup'))

                # For each grouping, generate the query containing each of the fields selected
                col_queries = [GqlQuery().fields(fields).query(header).generate() for header in column_headers]
                if col_queries:
                    fields_nested_demographics.append(GqlQuery().fields(col_queries).query(model_name).generate())
            else:
                fields_demographic = GqlQuery().fields(fields).query(model_name).generate()
                fields_nested_demographics.append(fields_demographic)

        # Build Clinical data
        # Order by ID for the benefit of the unit tests to ensure the graphql query is generated in a predictable order
        # However, the order of the clinical data in a CSV export is currently determined by the order it appears in a
        # patient's clinical record. Revisit this in the future if there's a need to allow the user to set the order on
        # the fields in a report design.
        cde_keys = [rcdf.cde_key for rcdf in self.report_design.reportclinicaldatafield_set.all().order_by('id')]

        # - create a dictionary to respectively group together cfg, form, sections by keys
        cfg_dicts = {}
        for key in cde_keys:
            form, section, cde = models_from_mongo_key(self.report_design.registry, key)
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
                form_name_field = get_schema_field_name(form_name)
                for section_code, section in form['sections'].items():
                    field_section = GqlQuery().fields(map(get_schema_field_name, section['cdes']), name=get_schema_field_name(section_code)).generate()
                    fields_section.append(field_section)

                if cfg['is_fixed']:
                    field_form = GqlQuery().fields(fields_section, name=form_name_field).generate()
                else:
                    field_data = GqlQuery().fields(fields_section, name='data').generate()
                    field_form = GqlQuery().fields(['key', field_data], name=form_name_field).generate()

                fields_form.append(field_form)

            field_cfg = GqlQuery().fields(fields_form, name=get_schema_field_name(cfg_code)).generate()
            fields_clinical_data.append(field_cfg)

        # Build query
        fields_patient = []
        fields_patient.extend(patient_fields)
        fields_patient.extend(fields_nested_demographics)
        if fields_clinical_data:
            fields_patient.append(GqlQuery().fields(fields_clinical_data).query('clinicalData').generate())
        return GqlQuery().fields(fields_patient).query('patients', input=patient_filters).operation().generate()

    def __get_demographic_headers(self, request):
        def get_flat_json_path(report_model, report_field, variant_index=None):
            if not report_field:
                return None
            if report_model == 'patient':
                prefix = ''
            else:
                prefix = f'{report_model}_'

            # When report_field contains nested fields (indicated by the presence of curly braces),
            # Then apply further transformation to the report field to flatten it
            if re.search('[{}]', report_field):
                # e.g. addressType { type }
                # 1. Remove spaces = addressType{type}
                json_field_path = re.sub(r"\s", "", report_field)
                # 2. Replace curly brace with a single underscore to separate the parts = addressType_type
                # --> regex group 1 = addressType
                # --> regex group 2 = {type}
                # --> regex group 3 = type
                json_field_path = re.sub(r"(.+)({(.*)})", r"\1_\3", json_field_path)
            else:
                json_field_path = report_field

            if variant_index is not None:
                return f"{prefix}{variant_index}_{json_field_path}"
            else:
                return f"{prefix}{json_field_path}"

        fieldnames_dict = OrderedDict()

        # e.g. {'patientAddress': True}
        processed_multifield_models = {}

        for rdf in self.report_design.reportdemographicfield_set.all().order_by('sort_order'):
            model_config = self.report_config[rdf.model]

            if rdf.model == 'patient':
                # Get label for simple fields
                fieldnames_dict[get_flat_json_path(rdf.model, rdf.field)] = model_config['fields'][rdf.field]
            else:
                if model_config.get('multi_field', False):
                    if not processed_multifield_models.get(rdf.model):
                        # Process all the fields for this model now
                        model_fields = self.report_design.reportdemographicfield_set.filter(
                            model=rdf.model).values_list("field", flat=True)

                        if model_config.get('pivot', False):
                            # Lookup the variants of this item, expected to be a list of unique codes/values
                            column_headers = self.__get_variants(model_config.get('variant_lookup'))

                            if column_headers:
                                # Generate a fieldname item for each (column x model fields)
                                for column in column_headers:
                                    for mf in model_fields:
                                        fieldnames_dict[get_flat_json_path(rdf.model, f'{column}_{mf}')] = \
                                            f"{model_config['label']}_{column}_{model_config['fields'][mf]}"
                            else:
                                # Generate dummy columns so the report isn't completely empty
                                for mf in model_fields:
                                    fieldnames_dict[get_flat_json_path(rdf.model, mf)] = \
                                        f"{model_config['label']}_{model_config['fields'][mf]}"
                        else:
                            # Lookup how many variants of this model is relevant to our patient dataset
                            num_variants = self.__get_variants(model_config['variant_lookup'], request)

                            for i in range(num_variants or 0):
                                for mf in model_fields:
                                    fieldnames_dict[get_flat_json_path(rdf.model, mf, i)] = \
                                        f"{model_config['label']}_{i + 1}_{model_config['fields'][mf]}"

                        # Mark as processed
                        processed_multifield_models[rdf.model] = True
                else:
                    fieldnames_dict[get_flat_json_path(rdf.model,
                                                       rdf.field)] = f"{model_config['label']}_{model_config['fields'][rdf.field]}"

        return fieldnames_dict

    def validate_query(self, request):
        try:
            result = self.schema.execute(self.__get_graphql_query(offset=1, limit=1), context_value=request)
        except BadKeyError as ex:
            return False, {'query_bad_key_error': str(ex)}

        if result.errors:
            return False, {'query_structure': result.errors}

        return True, None

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
            result = self.schema.execute(self.__get_graphql_query(offset=offset, limit=limit), context_value=request)
            all_patients = result.data['patients']
            num_patients = len(all_patients)
            offset += num_patients

            for patient in all_patients:
                patient_json = json.dumps(patient)
                yield f'{patient_json}\n'

            if num_patients < limit:
                break

    def export_to_csv(self, request):
        # Build Headers
        headers = OrderedDict()
        headers.update(self.__get_demographic_headers(request))
        headers.update(ClinicalDataCsvUtil().csv_headers(request.user, self.report_design))

        output = io.StringIO()
        header_writer = csv.DictWriter(output, fieldnames=headers.values())
        header_writer.writeheader()
        yield codecs.BOM_UTF8  # Required by MS Excel to correctly load content in UTF-8, otherwise encoding is ignored.
        yield output.getvalue()

        # Build/Chunk Patient Data
        limit = 20
        num_patients = 20
        offset = 0

        while num_patients >= limit:
            result = self.schema.execute(self.__get_graphql_query(offset=offset, limit=limit), context_value=request)
            flat_patient_data = [flatten(p) for p in result.data['patients']]

            num_patients = len(flat_patient_data)
            offset += num_patients

            output = io.StringIO()
            data_writer = csv.DictWriter(output, fieldnames=(headers.keys()), extrasaction='ignore')
            data_writer.writerows(flat_patient_data)

            yield output.getvalue()
