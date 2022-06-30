from gql_query_builder import GqlQuery

from report.schema import create_dynamic_schema


class PatientQueryData:
    def __init__(self, registry):
        self.registry = registry

    def _get_facet_query(self):
        fields_facets = ['field', GqlQuery().fields(['label', 'value', 'total']).query('categories').generate()]
        query_facets = GqlQuery().fields(fields_facets).query('facets').generate()
        return GqlQuery().fields([query_facets]).query('allPatients', input={'registryCode': f'"{self.registry.code}"'}).operation().generate()

    def get_facet_values(self, request, facet_keys):
        schema = create_dynamic_schema()

        result = schema.execute(self._get_facet_query(), context_value=request)

        facets = result.data.get('allPatients', {}).get('facets')

        return [facet for facet in facets if facet.get('field') in facet_keys]
