# trrf-analytics

## Description
A lambda to keep the materialised view containing TRRF analytics refreshed on a scheduled.
This lambda will loop through each registry application's database within the specified environment.

## Dependencies
* Python 3.9

## Installation
```
sam build

sam local invoke AnalyticsRefresher --parameter-overrides ApplicationName=myappname Environment=local

sam deploy --stack-name dev-trrf-analytics \
           --s3-bucket qut-lambda-code-ap-southeast-2 \
           --s3-prefix local \
           --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
           --parameter-overrides Environment=dev ApplicationName=trrf
```

Existing deployment of SSM parameters with database properties required for each application targeted 
within the `ApplicationName` environment variable. 

Expected format:
`/app/{environment}/{app_name}/{database_param_name}`