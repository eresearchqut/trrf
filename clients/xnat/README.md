# XNAT API
## Generate an OpenAPI client from the xnat spec
1. Run the openapi generator tool:
```shell
docker run --rm -v $(pwd):/local openapitools/openapi-generator-cli:v7.18.0 generate -i /local/spec/xnat-api.yaml -g python -o /local/generated
```
