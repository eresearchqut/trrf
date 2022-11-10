import logging

from gql_query_builder import GqlQuery
from graphql import GraphQLError

from report.schema import create_dynamic_schema

logger = logging.getLogger(__name__)


class GraphQLResultError(GraphQLError):
    pass


def build_search_item(text, fields):
    return {'text': text, 'fields': fields}


def build_patient_filters(filters):
    variable_definition = {"filterArgs": ("PatientFilterType", filters)}

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


def build_all_patients_query(registry, patient_query_fields, query_input=None, operation_input=None):
    registry_fields = GqlQuery().fields(patient_query_fields)

    if query_input:
        registry_fields = registry_fields.query('allPatients', input=query_input)
    else:
        registry_fields = registry_fields.query('allPatients')

    registry_query = GqlQuery().fields([registry_fields.generate()]).query(registry.code)

    if operation_input:
        registry_query = registry_query.operation(name='AllPatientsQuery', input=operation_input)
    else:
        registry_query = registry_query.operation()

    return registry_query.generate()


def execute_query(request, query):
    schema = create_dynamic_schema()
    result = schema.execute(query, context_value=request)

    if hasattr(result, 'errors') and result.errors:
        raise GraphQLResultError(result.errors)

    return result


def query_patient_facets(request, registry, facet_keys):
    if not facet_keys:
        return []
    facet_query = build_facet_query(facet_keys)
    all_patients_query = build_all_patients_query(registry, [facet_query])
    result = execute_query(request, all_patients_query)
    return get_all_patients(result, registry).get('facets')


def query_patient(request, registry, id, fields, fragment=None):
    patient_query = GqlQuery().fields(fields).query('patients', input={'id': f'"{id}"'}).generate()
    all_patients_query = build_all_patients_query(registry, [patient_query])

    if fragment:
        all_patients_query = fragment + '\n' + all_patients_query

    result = execute_query(request, all_patients_query)
    patients = get_all_patients(result, registry).get('patients', [])

    if patients and len(patients) == 1:
        return patients[0]


def get_all_patients(results, registry):
    return results.data.get(registry.code, {}).get('allPatients', {})
