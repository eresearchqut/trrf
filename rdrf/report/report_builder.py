import codecs
import csv
import io
import itertools
import json
import logging
from collections import OrderedDict

from flatten_json import flatten
from gql_query_builder import GqlQuery

from rdrf.forms.dsl.parse_utils import prefetch_form_data
from rdrf.helpers.utils import BadKeyError, models_from_mongo_key
from rdrf.patients.query_data import (
    build_all_patients_query,
    build_data_summary_query,
    build_patient_filters,
    build_patients_query,
    get_all_patients,
)
from report.clinical_data_csv_util import ClinicalDataCsvUtil
from report.models import ReportCdeHeadingFormat
from report.schema import create_dynamic_schema, get_schema_field_name
from report.utils import get_flattened_json_path, load_report_configuration

logger = logging.getLogger(__name__)


class ReportBuilder:
    def __init__(self, report_design):
        self.report_design = report_design
        self.report_config = load_report_configuration()["demographic_model"]
        self.report_fields_lookup = self.__init_report_fields_lookup()
        self.patient_filters = self.__init_patient_filters()
        self.schema = create_dynamic_schema()

    def __init_report_fields_lookup(self):
        return {
            model: model_config["fields"]
            for model, model_config in self.report_config.items()
        }

    def __init_patient_filters(self):
        def get_patient_consent_question_filters():
            return [
                f"{cq.id}" for cq in self.report_design.filter_consents.all()
            ]

        def get_patient_working_group_filters():
            return [
                f"{str(wg.id)}"
                for wg in self.report_design.filter_working_groups.all().order_by(
                    "id"
                )
            ]

        filters = {
            "workingGroups": get_patient_working_group_filters(),
            "consentQuestions": get_patient_consent_question_filters(),
        }

        return build_patient_filters(filters)

    def __get_variants(self, lookup_key, request):
        query_data_summary = build_data_summary_query([lookup_key])
        operation_input, query_input, variables = self.patient_filters
        query = build_all_patients_query(
            self.report_design.registry,
            [query_data_summary],
            query_input,
            operation_input,
        )
        summary_result = self.schema.execute(
            query, variable_values=variables, context_value=request
        )
        return (
            get_all_patients(summary_result, self.report_design.registry)
            .get("dataSummary", {})
            .get(lookup_key)
        )

    def _build_query_from_variants(self, variants, fields):
        # Non-nested lists, where the variant code is globally unique
        # e.g. variants=["itemCode1", "itemCode2"]
        if any(isinstance(item, str) for item in variants):
            return [
                GqlQuery().fields(fields).query(header).generate()
                for header in variants
            ]

        # Nested lists, representing compound keys
        # e.g. variants=[["sectionA", "itemCode1"], ["sectionA", "itemCode2"], ["sectionB", "itemCode1"]]
        queries = []
        if variants and variants[0]:
            sorted_variants = sorted(variants, key=lambda x: x[0])
            for group_name, items in itertools.groupby(
                sorted_variants, lambda x: x[0]
            ):
                group_items = list(items)
                group_name_field = get_schema_field_name(group_name)
                next_group_items = [item[1:] for item in group_items]
                if len(next_group_items[0]) == 1:
                    # We've reached the end of the list so build the lowest level query
                    query_fields = [
                        GqlQuery()
                        .fields(fields)
                        .query(get_schema_field_name(item))
                        .generate()
                        for nested_item in next_group_items
                        for item in nested_item
                    ]
                    queries.extend(
                        [
                            GqlQuery()
                            .fields(query_fields)
                            .query(group_name_field)
                            .generate()
                        ]
                    )
                else:
                    # Recurse over the next lot of group items to continue to build the query from the inside out
                    inner_query_fields = self._build_query_from_variants(
                        next_group_items, fields
                    )
                    queries.append(
                        GqlQuery()
                        .fields(inner_query_fields)
                        .query(group_name_field)
                        .generate()
                    )
        return queries

    def _get_graphql_query(self, request, offset=None, limit=None):
        # Build Pagination filters
        pagination_args = {}
        if offset:
            pagination_args["offset"] = offset

        if limit:
            pagination_args["limit"] = limit

        # Build simple patient demographic fields
        patient_fields = []
        patient_fields.extend(
            self.report_design.reportdemographicfield_set.filter(
                model="patient"
            ).values_list("field", flat=True)
        )

        # Build list of other demographic fields to report on, group by model
        other_demographic_fields = {}
        for (
            demographic_field
        ) in self.report_design.reportdemographicfield_set.exclude(
            model="patient"
        ):
            other_demographic_fields.setdefault(
                demographic_field.model, []
            ).append(demographic_field.field)

        fields_nested_demographics = []
        for model_name, fields in other_demographic_fields.items():
            if model_name in self.report_config:
                model_config = self.report_config[model_name]
            else:
                continue

            if model_config.get("pivot", False):
                # Lookup the variants of this item which will form the column header groupings
                # e.g. for consents, returns a list of the unique consent codes
                variants = self.__get_variants(
                    model_config.get("variant_lookup"), request
                )

                # For each grouping, generate the query containing each of the fields selected
                col_queries = self._build_query_from_variants(variants, fields)

                if col_queries:
                    fields_nested_demographics.append(
                        GqlQuery()
                        .fields(col_queries)
                        .query(model_name)
                        .generate()
                    )
            else:
                fields_demographic = (
                    GqlQuery().fields(fields).query(model_name).generate()
                )
                fields_nested_demographics.append(fields_demographic)

        # Build Clinical data
        # Order by ID for the benefit of the unit tests to ensure the graphql query is generated in a predictable order
        # However, the order of the clinical data in a CSV export is currently determined by the order it appears in a
        # patient's clinical record. Revisit this in the future if there's a need to allow the user to set the order on
        # the fields in a report design.

        # - create a dictionary to respectively group together cfg, form, sections by keys
        invalid_cdes = []
        cfg_dicts = {}

        form_data_dict = {}  # Reduce the number of calls to prefetch_form_data

        def _get_form_data(form):
            if form.name not in form_data_dict:
                form_data_dict[form.name] = prefetch_form_data(form)

            return form_data_dict[form.name]

        for (
            cde_field
        ) in self.report_design.reportclinicaldatafield_set.all().order_by(
            "id"
        ):
            cfg = cde_field.context_form_group
            form, section, cde = models_from_mongo_key(
                self.report_design.registry, cde_field.cde_key
            )

            form_sections, cde_dict = _get_form_data(form)
            section_cdes = cde_dict.get(section.code, [])

            # validate cde reference
            if cde not in section_cdes or section not in form_sections:
                invalid_cdes.append(cde.code)

            cfg_dict = cfg_dicts.setdefault(
                cfg.code, {"is_fixed": cfg.is_fixed, "forms": {}}
            )
            form_dict = cfg_dict["forms"].setdefault(
                form.name, {"sections": {}}
            )
            section_dict = form_dict["sections"].setdefault(
                section.code, {"cdes": []}
            )
            section_dict["cdes"].append(cde.code)

        if invalid_cdes:
            raise BadKeyError(invalid_cdes)

        # - build the clinical data query
        fields_clinical_data = []
        for cfg_code, cfg in cfg_dicts.items():
            fields_form = []
            for form_name, form in cfg["forms"].items():
                fields_section = []
                form_name_field = get_schema_field_name(form_name)
                form_metadata = []

                for section_code, section in form["sections"].items():
                    field_section = (
                        GqlQuery()
                        .fields(
                            map(get_schema_field_name, section["cdes"]),
                            name=get_schema_field_name(section_code),
                        )
                        .generate()
                    )
                    fields_section.append(field_section)

                if self.report_design.cde_include_form_timestamp:
                    form_metadata.append(
                        GqlQuery()
                        .fields(["lastUpdated"], name="meta")
                        .generate()
                    )

                if cfg["is_fixed"]:
                    field_form = (
                        GqlQuery()
                        .fields(
                            [*form_metadata, *fields_section],
                            name=form_name_field,
                        )
                        .generate()
                    )
                else:
                    field_data = (
                        GqlQuery()
                        .fields(fields_section, name="data")
                        .generate()
                    )
                    field_form = (
                        GqlQuery()
                        .fields(
                            ["key", *form_metadata, field_data],
                            name=form_name_field,
                        )
                        .generate()
                    )

                fields_form.append(field_form)

            field_cfg = (
                GqlQuery()
                .fields(fields_form, name=get_schema_field_name(cfg_code))
                .generate()
            )
            fields_clinical_data.append(field_cfg)

        # Build query
        fields_patient = []
        fields_patient.extend(patient_fields)
        fields_patient.extend(fields_nested_demographics)
        if fields_clinical_data:
            fields_patient.append(
                GqlQuery()
                .fields(fields_clinical_data)
                .query("clinicalData")
                .generate()
            )
        query_patient = build_patients_query(
            fields_patient, ["id"], pagination_args
        )

        operation_input, query_input, variables = self.patient_filters
        return variables, build_all_patients_query(
            self.report_design.registry,
            [query_patient],
            query_input,
            operation_input,
        )

    def _get_demographic_headers(self, request):
        def get_flat_json_path(report_model, report_field, variant_index=None):
            if not report_field:
                return None
            if report_model == "patient":
                prefix = ""
            else:
                prefix = f"{report_model}_"

            json_field_path = get_flattened_json_path(report_field)

            if variant_index is not None:
                return f"{prefix}{variant_index}_{json_field_path}"
            else:
                return f"{prefix}{json_field_path}"

        fieldnames_dict = OrderedDict()

        # e.g. {'patientAddress': True}
        processed_multifield_models = {}

        for rdf in self.report_design.reportdemographicfield_set.all().order_by(
            "sort_order"
        ):
            model_config = self.report_config[rdf.model]

            if rdf.model == "patient":
                # Get label for simple fields
                fieldnames_dict[get_flat_json_path(rdf.model, rdf.field)] = (
                    model_config["fields"][rdf.field]
                )
            else:
                if model_config.get("multi_field", False):
                    if not processed_multifield_models.get(rdf.model):
                        # Process all the fields for this model now
                        model_fields = self.report_design.reportdemographicfield_set.filter(
                            model=rdf.model
                        ).values_list("field", flat=True)

                        if model_config.get("pivot", False):
                            # Lookup the variants of this item, expected to be a list of unique codes/values
                            variants = self.__get_variants(
                                model_config.get("variant_lookup"), request
                            )

                            if variants:
                                # Generate a fieldname item for each (column x model fields)
                                for item in variants:
                                    items = (
                                        item
                                        if isinstance(item, list)
                                        else [item]
                                    )
                                    item_pointer = "_".join(
                                        [
                                            get_schema_field_name(field)
                                            for field in items
                                        ]
                                    )
                                    for mf in model_fields:
                                        fieldnames_dict[
                                            get_flat_json_path(
                                                rdf.model,
                                                f"{item_pointer}_{mf}",
                                            )
                                        ] = f"{model_config['label']}_{item_pointer}_{model_config['fields'][mf]}"
                            else:
                                # Generate dummy columns so the report isn't completely empty
                                for mf in model_fields:
                                    fieldnames_dict[
                                        get_flat_json_path(rdf.model, mf)
                                    ] = f"{model_config['label']}_{model_config['fields'][mf]}"
                        else:
                            # Lookup how many variants of this model is relevant to our patient dataset
                            num_variants = self.__get_variants(
                                model_config["variant_lookup"], request
                            )

                            for i in range(num_variants or 0):
                                for mf in model_fields:
                                    fieldnames_dict[
                                        get_flat_json_path(rdf.model, mf, i)
                                    ] = f"{model_config['label']}_{i + 1}_{model_config['fields'][mf]}"

                        # Mark as processed
                        processed_multifield_models[rdf.model] = True
                else:
                    fieldnames_dict[
                        get_flat_json_path(rdf.model, rdf.field)
                    ] = f"{model_config['label']}_{model_config['fields'][rdf.field]}"

        return fieldnames_dict

    def validate_query(self, request):
        try:
            variables, query = self._get_graphql_query(
                request, offset=1, limit=1
            )
            result = self.schema.execute(
                query, variable_values=variables, context_value=request
            )
        except BadKeyError as ex:
            return False, {"query_bad_key_error": str(ex)}

        if result.errors:
            return False, {"query_structure": result.errors}

        return True, None

    def validate_for_csv_export(self):
        if (
            self.report_design.cde_heading_format
            == ReportCdeHeadingFormat.CODE.value
        ):
            return True, {}

        headings_dict = dict()

        for cde_field in self.report_design.reportclinicaldatafield_set.all():
            cfg = cde_field.context_form_group
            form, section, cde = models_from_mongo_key(
                self.report_design.registry, cde_field.cde_key
            )
            col_header = ""

            if (
                self.report_design.cde_heading_format
                == ReportCdeHeadingFormat.LABEL.value
            ):
                col_header = f"{cfg.name}_{form.nice_name}_{section.display_name}_{cde.name}"
            elif (
                self.report_design.cde_heading_format
                == ReportCdeHeadingFormat.ABBR_NAME.value
            ):
                col_header = f"{cfg.abbreviated_name}_{form.abbreviated_name}_{section.abbreviated_name}_{cde.abbreviated_name}"

            headings_dict.setdefault(col_header, []).append(
                {
                    "cfg": cfg.code,
                    "form": form.nice_name,
                    "section": section.__str__(),
                    "cde": cde.__str__(),
                }
            )

        duplicate_headings = dict(
            filter(lambda item: len(item[1]) > 1, headings_dict.items())
        )

        return len(duplicate_headings) == 0, {
            "duplicate_headers": duplicate_headings
        }

    def export_to_json(self, request):
        limit = 20
        offset = 0

        while True:
            variables, query = self._get_graphql_query(
                request, offset=offset, limit=limit
            )
            result = self.schema.execute(
                query, variable_values=variables, context_value=request
            )
            all_patients = get_all_patients(
                result, self.report_design.registry
            ).get("patients")
            num_patients = len(all_patients)
            offset += num_patients

            for patient in all_patients:
                patient_json = json.dumps(patient)
                yield f"{patient_json}\n"

            if num_patients < limit:
                break

    def export_to_csv(self, request):
        # Purpose of BOM:
        # - Required by MS Excel to correctly load content in UTF-8, otherwise encoding is ignored.
        # - Quick response back to browser to prevent cloudfront from timing out.
        yield codecs.BOM_UTF8

        # Build Headers
        headers = OrderedDict()
        headers.update(self._get_demographic_headers(request))
        headers.update(
            ClinicalDataCsvUtil().csv_headers(request.user, self.report_design)
        )

        output = io.StringIO()
        header_writer = csv.DictWriter(output, fieldnames=headers.values())
        header_writer.writeheader()

        yield output.getvalue()

        # Build/Chunk Patient Data
        limit = 20
        num_patients = 20
        offset = 0

        while num_patients >= limit:
            variables, query = self._get_graphql_query(
                request, offset=offset, limit=limit
            )
            result = self.schema.execute(
                query, variable_values=variables, context_value=request
            )
            flat_patient_data = [
                flatten(p)
                for p in get_all_patients(
                    result, self.report_design.registry
                ).get("patients")
            ]

            num_patients = len(flat_patient_data)
            offset += num_patients

            output = io.StringIO()
            data_writer = csv.DictWriter(
                output, fieldnames=(headers.keys()), extrasaction="ignore"
            )
            data_writer.writerows(flat_patient_data)

            yield output.getvalue()
