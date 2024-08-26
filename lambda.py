import logging
import os

import boto3
import django

logger = logging.getLogger(__name__)


def _set_env_variables(parameter_envs):
    ssm = boto3.client("ssm")
    response = ssm.get_parameters(
        Names=list(parameter_envs.keys()), WithDecryption=True
    )
    logger.debug(f"SSM parameters: {response}")
    for parameter in response["Parameters"]:
        os.environ[parameter_envs[parameter["Name"]]] = parameter["Value"]


if "AWS_EXECUTION_ENV" in os.environ:
    environment = os.environ["ENVIRONMENT"]
    application = os.environ["APPLICATION_NAME"]

    _set_env_variables(
        {
            f"/app/{environment}/SECRET_KEY": "SECRET_KEY",
            f"/app/{environment}/AWS_SES_ACCESS_KEY_ID": "AWS_SES_ACCESS_KEY_ID",
            f"/app/{environment}/AWS_SES_SECRET_ACCESS_KEY": "AWS_SES_SECRET_ACCESS_KEY",
            f"/app/{environment}/{application}/DBSERVER": "DBSERVER",
            f"/app/{environment}/{application}/DBPORT": "DBPORT",
            f"/app/{environment}/{application}/DBNAME": "DBNAME",
            f"/app/{environment}/{application}/DBUSER": "DBUSER",
            f"/app/{environment}/{application}/DBPASS": "DBPASS",
        }
    )

django.setup()

from rdrf.services.io.notifications.longitudinal_followups import (  # noqa: E402
    send_longitudinal_followups,
)


def longitudinal_followup_handler(_event, _context):
    send_longitudinal_followups()


if __name__ == "__main__":
    longitudinal_followup_handler(None, None)
