from rdrf.schema.schema import schema
import json
import logging

logger = logging.getLogger(__name__)

class Report:

    def __init__(self, report_design):
        self.report_design = report_design


    def __get_graphql_query(self):

        def get_patient_filters():
            patient_filters = []

            if self.report_design.filter_consents:
                patient_filters.append(f'"consents__answer=True"')
                patient_filters.extend(
                    [f'"consents__consent_question__code={consent_question.code}"' for consent_question in
                     self.report_design.filter_consents.all()])

            return patient_filters

        def get_patient_working_group_filters():
            if self.report_design.filter_working_groups:
                return [json.dumps(str(wg.id)) for wg in self.report_design.filter_working_groups.all()]

        patient_fields = []
        other_demographic_fields = {}

        # Separate patient fields from other related to patient fields.
        for demographic_field in self.report_design.demographicfield_set.all():
            field_dict = json.loads(demographic_field.field)
            model_name = field_dict['model']

            if model_name == 'Patient':
                patient_fields.append(field_dict)
            else:
                other_demographic_fields.setdefault(field_dict['model_field_lookup'], []).append(field_dict)
            # other_demographic_fields.setdefault(model_name, []).append(field_dict)

        related_demographic_fields_query = ""

        for model_lookup, fields in other_demographic_fields.items():
            related_demographic_fields_query = \
f"""
        {related_demographic_fields_query}
       ,{model_lookup} {{
            {",".join([field_dict['field'] for field_dict in fields])}
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
        {",".join([field_dict['field'] for field_dict in patient_fields])}
        {related_demographic_fields_query},
        clinicalDataFlat(cdeKeys: [{",".join(cde_keys)}])
            {{cfg {{name, sortOrder, entryNum}}, form, section, sectionCnt,
            cde {{
                code
                ... on ClinicalDataCde {{value}}
                ... on ClinicalDataCdeMultiValue {{values}}
            }} 
        }}
    }}
}}
"""
        return query

    def get_json(self, request):
        result = schema.execute(self.__get_graphql_query(), context_value=request)
        logger.debug(result)
        return json.dumps(result.data)

    def get_csv(self):
        result = schema.execute(self.__get_graphql_query(), context_value=request)

        return "TODO"