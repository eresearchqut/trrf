from django.test import TestCase

from report.utils import get_flattened_json_path, get_graphql_result_value


class ReportUtilsTest(TestCase):
    def test_get_flattened_json_path(self):
        self.assertEqual(get_flattened_json_path(''), '')
        self.assertEqual(get_flattened_json_path('givenName'), 'givenName')
        self.assertEqual(get_flattened_json_path('addressType { type }'), 'addressType_type')
        self.assertEqual(get_flattened_json_path('addressType{type}'), 'addressType_type')
        self.assertEqual(get_flattened_json_path('nextOfKin { relationship { type }}'), 'nextOfKin_relationship_type')

    def test_get_graphql_result_value(self):

        graphql_result = {
            'givenName': 'Jon',
            'addressType': {'type': 'Postal'},
            'nextOfKin': {'relationship': {'type': 'Sibling'}}
        }

        self.assertEqual(get_graphql_result_value(graphql_result, 'givenName'), 'Jon')
        self.assertEqual(get_graphql_result_value(graphql_result, 'addressType{type}'), 'Postal')
        self.assertEqual(get_graphql_result_value(graphql_result, 'nextOfKin{relationship{type}}'), 'Sibling')
        self.assertEqual(get_graphql_result_value(graphql_result, 'mismatch'), None)
