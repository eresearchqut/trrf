import logging

from gql_query_builder import GqlQuery

from report.schema import create_dynamic_schema


logger = logging.getLogger(__name__)


def build_search_item(text, fields):
    return {'text': text, 'fields': fields}


def build_patient_filters(registry_code, filters):
    variable_definition = {"registryCode": ("String!", registry_code),
                           "filterArgs": ("PatientFilterType", filters)
                           }

    operation_input = {f'${key}': data_type for key, (data_type, variable) in variable_definition.items()}
    query_input = {key: f'${key}' for key in variable_definition.keys()}
    variables = {key: variable for key, (data_type, variable) in variable_definition.items()}

    return operation_input, query_input, variables


def build_patients_query(patient_fields, sort_fields, pagination):
    sort_fields_formatted = ",".join([f'"{field}"' for field in sort_fields])
    patients_input = {'sort': f'[{sort_fields_formatted}]',
                      'offset': pagination.get('offset'),
                      'limit': pagination.get('limit')}
    # remove any inputs with null values
    patients_input = {key: val for key, val in patients_input.items() if val is not None}
    patient_query = GqlQuery().fields(patient_fields).query('patients', input=patients_input).generate()
    return patient_query


def build_facet_query(facet_keys):
    facets_fields = [GqlQuery().fields(['label', 'value', 'total']).query(facet_key).generate()
                     for facet_key in facet_keys]

    return GqlQuery().fields(facets_fields).query('facets').generate()


def build_data_summary_query(data_summary_fields):
    return GqlQuery().fields(data_summary_fields).query('dataSummary').generate()


def build_all_patients_query(patient_query_fields, query_input, operation_input=None):
    query = GqlQuery().fields(patient_query_fields).query('allPatients', input=query_input)
    if operation_input:
        query = query.operation(name='AllPatientsQuery', input=operation_input)
    else:
        query = query.operation()
    return query.generate()


def query_patient_facets(request, registry, facet_keys):
    if not facet_keys:
        return []
    schema = create_dynamic_schema()
    facet_query = build_facet_query(facet_keys)
    all_patients_query = build_all_patients_query([facet_query], {'registryCode': f'"{registry.code}"'})
    result = schema.execute(all_patients_query, context_value=request)
    return get_all_patients(result).get('facets')


def get_all_patients(results):
    return results.data.get('allPatients', {})
