import re

from rdrf.models.definition.models import Registry
from rdrf.patients.query_data import PatientQueryData
from rdrf.testing.unit.tests import RDRFTestCase
from registry.groups.models import CustomUser


class PatientQueryDataTest(RDRFTestCase):

    def _request(self):
        class TestContext:
            user = CustomUser.objects.get(username='admin')
        return TestContext()

    def _query_syntax(self, query_string):
        return re.sub(r'\s+', ' ', query_string.strip())

    def test_facet_query(self):
        query_data = PatientQueryData(Registry.objects.get(code='fh'))

        expected_facet_query = '''
            query {
                allPatients(registryCode: "fh") {
                    facets {
                        field
                        categories {
                            label
                            value
                            total
                        }
                    }
                }
            }
        '''

        self.assertEqual(self._query_syntax(expected_facet_query), query_data._get_facet_query())

    def test_get_facets(self):
        query_data = PatientQueryData(Registry.objects.get(code='fh'))
        facets = query_data.get_facet_values(self._request(), ['living_status'])
        self.assertEqual(['living_status'], [facet.get('field') for facet in facets])
