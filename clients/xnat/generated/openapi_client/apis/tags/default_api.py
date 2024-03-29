# coding: utf-8

"""
    XNAT REST API Translation

    REST API converted to Open API  # noqa: E501

    The version of the OpenAPI document: 1.0.0
    Generated by: https://openapi-generator.tech
"""

from openapi_client.paths.data_experiments_experiment_id_scans.get import DataExperimentsExperimentIdScansGet
from openapi_client.paths.data_projects_project_id_subjects_subject_id_experiments.get import DataProjectsProjectIdSubjectsSubjectIdExperimentsGet
from openapi_client.paths.data_services_auth.put import DataServicesAuthPut


class DefaultApi(
    DataExperimentsExperimentIdScansGet,
    DataProjectsProjectIdSubjectsSubjectIdExperimentsGet,
    DataServicesAuthPut,
):
    """NOTE: This class is auto generated by OpenAPI Generator
    Ref: https://openapi-generator.tech

    Do not edit the class manually.
    """
    pass
