# XNAT API
## Generate an OpenAPI client from the xnat spec
1. Run the openapi generator tool:
```shell
docker run --rm -v $(pwd):/local openapitools/openapi-generator-cli generate -i /local/spec/xnat-api.yaml -g python -o /local/generated
```
2. update the dateutil dependency version in `generated/setup.py`:
```text
    "python-dateutil ~= 2.8.0",
```
