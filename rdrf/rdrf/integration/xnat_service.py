import openapi_client
from django.conf import settings
from openapi_client.apis.tags import default_api


def xnat_api_client():
    return openapi_client.ApiClient(openapi_client.Configuration(
        host=settings.XNAT_API_ENDPOINT,
        username=settings.XNAT_API_USERNAME,
        password=settings.XNAT_API_PASSWORD
    ))


class XnatApi:

    def __init__(self, api_instance):
        self._api_instance = api_instance

    def authenticate(self):
        try:
            self._api_instance.data_services_auth_put()
        except openapi_client.ApiException as e:
            auth_cookie = e.headers.get('Set-Cookie', 'x')
            return auth_cookie

    def get_experiments(self, project_id, subject_id):
        api_response = self._api_instance.data_projects_project_id_subjects_subject_id_experiments_get(
            path_params={'project_id': project_id,
                         'subject_id': subject_id},
            query_params={'format': 'json'}
        )

        result_set = api_response.body.get_item_oapg('ResultSet')

        return [{'date': result.get_item_oapg('insert_date'),
                 'id': result.get_item_oapg('ID'),
                 'label': result.get_item_oapg('label'),
                 'URI': result.get_item_oapg('URI')}
                for result in result_set.get_item_oapg('Result')]

    def get_scans(self, experiment_id):
        api_response = self._api_instance.data_experiments_experiment_id_scans_get(
            path_params={'experiment_id': experiment_id},
            query_params={'format': 'json'}
        )
        result_set = api_response.body.get_item_oapg('ResultSet')
        return [{'id': result.get_item_oapg('ID'),
                 'type': result.get_item_oapg('type'),
                 'series_description': result.get_item_oapg('series_description'),
                 'URI': result.get_item_oapg('URI')}
                for result in result_set.get_item_oapg('Result')]


def xnat_experiments_scans(project_id, subject_id):
    with xnat_api_client() as api_client:
        api_instance = default_api.DefaultApi(api_client)

        xnat_api = XnatApi(api_instance)
        api_client.cookie = xnat_api.authenticate()

        return [{**experiment,
                 'scans': xnat_api.get_scans(experiment.get('id'))}
                for experiment in xnat_api.get_experiments(project_id, subject_id)]
