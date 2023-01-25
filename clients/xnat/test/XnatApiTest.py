import unittest

import openapi_client
from openapi_client.apis.tags import default_api


class MyTestCase(unittest.TestCase):

    def authenticate(self, api_instance):

        try:
            api_instance.data_services_auth_put()
        except openapi_client.ApiException as e:
            print(e.headers)
            set_cookie = e.headers.get('Set-Cookie', 'x')
            self.assertEqual(e.status, 404)
            return set_cookie

    def get_experiments(self, api_instance):
        api_response = api_instance.data_projects_project_id_subjects_subject_id_experiments_get(path_params={'project_id': 'PT-1', 'subject_id': 'patient1'})

        result_set = api_response.body.get_item_oapg('ResultSet')
        experiment_ids = [result.get_item_oapg('ID')
                          for result in result_set.get_item_oapg('Result')]

        return experiment_ids

    def get_scans(self, api_instance, experiment_id):
        api_response = api_instance.data_experiments_experiment_id_scans_get(path_params={'experiment_id': experiment_id})
        print(api_response)
        result_set = api_response.body.get_item_oapg('ResultSet')
        scans = [result for result in result_set.get_item_oapg('Result')]

        return scans

    def test_xnat_client(self):
        configuration = openapi_client.Configuration(
            host='http://localhost',
            username='xnatapi',
            password='xnatapi'
        )

        with openapi_client.ApiClient(configuration) as api_client:
            api_instance = default_api.DefaultApi(api_client)

            set_cookie = self.authenticate(api_instance)
            self.assertIsNotNone(set_cookie)
            api_client.cookie = set_cookie

            experiment_ids = self.get_experiments(api_instance)
            self.assertEqual(experiment_ids, ['XNAT_E00001'])

            scans = self.get_scans(api_instance, 'XNAT_E00001')
            self.assertEqual([scan.get_item_oapg('ID') for scan in scans], ['6'])


if __name__ == '__main__':
    unittest.main()
