# AWS Lambda Runtime Interface Emulator

[Documentation](https://docs.aws.amazon.com/lambda/latest/dg/images-test.html)
[Source](https://github.com/aws/aws-lambda-runtime-interface-emulator/)

Call the lambda function after starting the docker-compose service with the following command:

```bash
curl -XPOST "http://localhost:8001/2015-03-31/functions/function/invocations" -d '{}'
```