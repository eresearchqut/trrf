import typing_extensions

from openapi_client.paths import PathValues
from openapi_client.apis.paths.data_services_auth import DataServicesAuth
from openapi_client.apis.paths.data_projects_project_id_subjects_subject_id_experiments import DataProjectsProjectIdSubjectsSubjectIdExperiments
from openapi_client.apis.paths.data_experiments_experiment_id_scans import DataExperimentsExperimentIdScans

PathToApi = typing_extensions.TypedDict(
    'PathToApi',
    {
        PathValues.DATA_SERVICES_AUTH: DataServicesAuth,
        PathValues.DATA_PROJECTS_PROJECT_ID_SUBJECTS_SUBJECT_ID_EXPERIMENTS: DataProjectsProjectIdSubjectsSubjectIdExperiments,
        PathValues.DATA_EXPERIMENTS_EXPERIMENT_ID_SCANS: DataExperimentsExperimentIdScans,
    }
)

path_to_api = PathToApi(
    {
        PathValues.DATA_SERVICES_AUTH: DataServicesAuth,
        PathValues.DATA_PROJECTS_PROJECT_ID_SUBJECTS_SUBJECT_ID_EXPERIMENTS: DataProjectsProjectIdSubjectsSubjectIdExperiments,
        PathValues.DATA_EXPERIMENTS_EXPERIMENT_ID_SCANS: DataExperimentsExperimentIdScans,
    }
)
