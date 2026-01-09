# openapi_client.DefaultApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**data_experiments_experiment_id_scans_get**](DefaultApi.md#data_experiments_experiment_id_scans_get) | **GET** /data/experiments/{experiment_id}/scans | 
[**data_projects_project_id_subjects_subject_id_experiments_get**](DefaultApi.md#data_projects_project_id_subjects_subject_id_experiments_get) | **GET** /data/projects/{project_id}/subjects/{subject_id}/experiments | 
[**data_services_auth_put**](DefaultApi.md#data_services_auth_put) | **PUT** /data/services/auth | 


# **data_experiments_experiment_id_scans_get**
> DataExperimentsExperimentIdScansGet200Response data_experiments_experiment_id_scans_get(experiment_id, format=format)

Get A Listing Of Scans From An Image Session

### Example

* Api Key Authentication (cookieAuth):

```python
import openapi_client
from openapi_client.models.data_experiments_experiment_id_scans_get200_response import DataExperimentsExperimentIdScansGet200Response
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: cookieAuth
configuration.api_key['cookieAuth'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['cookieAuth'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)
    experiment_id = 'experiment_id_example' # str | 
    format = 'json' # str | The format of the response (optional) (default to 'json')

    try:
        api_response = api_instance.data_experiments_experiment_id_scans_get(experiment_id, format=format)
        print("The response of DefaultApi->data_experiments_experiment_id_scans_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->data_experiments_experiment_id_scans_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**|  | 
 **format** | **str**| The format of the response | [optional] [default to &#39;json&#39;]

### Return type

[**DataExperimentsExperimentIdScansGet200Response**](DataExperimentsExperimentIdScansGet200Response.md)

### Authorization

[cookieAuth](../README.md#cookieAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **data_projects_project_id_subjects_subject_id_experiments_get**
> DataProjectsProjectIdSubjectsSubjectIdExperimentsGet200Response data_projects_project_id_subjects_subject_id_experiments_get(project_id, subject_id, format=format)

Get a list of experiments

### Example

* Api Key Authentication (cookieAuth):

```python
import openapi_client
from openapi_client.models.data_projects_project_id_subjects_subject_id_experiments_get200_response import DataProjectsProjectIdSubjectsSubjectIdExperimentsGet200Response
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: cookieAuth
configuration.api_key['cookieAuth'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['cookieAuth'] = 'Bearer'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)
    project_id = 'project_id_example' # str | 
    subject_id = 'subject_id_example' # str | 
    format = 'json' # str | The format of the response (optional) (default to 'json')

    try:
        api_response = api_instance.data_projects_project_id_subjects_subject_id_experiments_get(project_id, subject_id, format=format)
        print("The response of DefaultApi->data_projects_project_id_subjects_subject_id_experiments_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->data_projects_project_id_subjects_subject_id_experiments_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **project_id** | **str**|  | 
 **subject_id** | **str**|  | 
 **format** | **str**| The format of the response | [optional] [default to &#39;json&#39;]

### Return type

[**DataProjectsProjectIdSubjectsSubjectIdExperimentsGet200Response**](DataProjectsProjectIdSubjectsSubjectIdExperimentsGet200Response.md)

### Authorization

[cookieAuth](../README.md#cookieAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **data_services_auth_put**
> data_services_auth_put()

Logs in and returns the authentication cookie

### Example

* Basic Authentication (basicAuth):

```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure HTTP basic authorization: basicAuth
configuration = openapi_client.Configuration(
    username = os.environ["USERNAME"],
    password = os.environ["PASSWORD"]
)

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.DefaultApi(api_client)

    try:
        api_instance.data_services_auth_put()
    except Exception as e:
        print("Exception when calling DefaultApi->data_services_auth_put: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successfully authenticated. The session ID is returned in a  cookie named &#x60;JSESSIONID&#x60;. You need to include this cookie in subsequent requests  |  * Set-Cookie -  <br>  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

