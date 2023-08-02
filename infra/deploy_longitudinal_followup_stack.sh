#!/usr/bin/env bash
set -xe

ROLE_OUTPUT=$(aws sts assume-role --role-arn "${CLOUDFORMATION_BUILDER_ROLE_ARN}" \
                                  --role-session-name "CloudformationBuilderRole" \
                                  --query "Credentials.[AccessKeyId,SecretAccessKey,SessionToken]" \
                                  --output text)

export AWS_ACCESS_KEY_ID=$(echo $ROLE_OUTPUT | cut -d' ' -f1)
export AWS_SECRET_ACCESS_KEY=$(echo $ROLE_OUTPUT | cut -d' ' -f2)
export AWS_SESSION_TOKEN=$(echo $ROLE_OUTPUT | cut -d' ' -f3)

aws cloudformation deploy --template-file infra/longitudinal_followup_stack.yml \
                          --stack-name "${ENVIRONMENT_NAME}-${APPLICATION_NAME}-longitudinal-followup-stack" \
                          --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
                          --parameter-overrides \
                            EnvironmentName="$ENVIRONMENT_NAME" \
                            ApplicationName="$APPLICATION_NAME" \
                            AlertStackName="$ALERT_STACK_NAME" \
                            NetworkStackName="$NETWORK_STACK_NAME" \
                            EcrAccount="$ECR_ACCOUNT" \
                            ImageTag="$GIT_TAG"
