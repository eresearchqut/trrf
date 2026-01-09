# DataExperimentsExperimentIdScansGet200ResponseResultSet


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**result** | [**List[DataExperimentsExperimentIdScansGet200ResponseResultSetResultInner]**](DataExperimentsExperimentIdScansGet200ResponseResultSetResultInner.md) |  | [optional] 
**total_records** | **str** |  | [optional] 

## Example

```python
from openapi_client.models.data_experiments_experiment_id_scans_get200_response_result_set import DataExperimentsExperimentIdScansGet200ResponseResultSet

# TODO update the JSON string below
json = "{}"
# create an instance of DataExperimentsExperimentIdScansGet200ResponseResultSet from a JSON string
data_experiments_experiment_id_scans_get200_response_result_set_instance = DataExperimentsExperimentIdScansGet200ResponseResultSet.from_json(json)
# print the JSON string representation of the object
print(DataExperimentsExperimentIdScansGet200ResponseResultSet.to_json())

# convert the object into a dict
data_experiments_experiment_id_scans_get200_response_result_set_dict = data_experiments_experiment_id_scans_get200_response_result_set_instance.to_dict()
# create an instance of DataExperimentsExperimentIdScansGet200ResponseResultSet from a dict
data_experiments_experiment_id_scans_get200_response_result_set_from_dict = DataExperimentsExperimentIdScansGet200ResponseResultSet.from_dict(data_experiments_experiment_id_scans_get200_response_result_set_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


