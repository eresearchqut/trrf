# do not import all endpoints into this module because that uses a lot of memory and stack frames
# if you need the ability to import all endpoints from this module, import them with
# from openapi_client.apis.path_to_api import path_to_api

import enum


class PathValues(str, enum.Enum):
    DATA_SERVICES_AUTH = "/data/services/auth"
    DATA_PROJECTS_PROJECT_ID_SUBJECTS_SUBJECT_ID_EXPERIMENTS = "/data/projects/{project_id}/subjects/{subject_id}/experiments"
    DATA_EXPERIMENTS_EXPERIMENT_ID_SCANS = "/data/experiments/{experiment_id}/scans"
