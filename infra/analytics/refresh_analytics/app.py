import json
import logging
import os

import boto3
import psycopg2

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app_environment = os.getenv('ENVIRONMENT')
app_name = os.getenv('APPLICATION_NAME')
view_name = os.getenv('ANALYTICS_VIEW_NAME')
log_table_name = os.getenv('ANALYTICS_LOG_TABLE')

db_name = os.getenv('CLINICAL_DB_PARAMETER_NAME')
db_port = os.getenv('DATABASE_PORT_PARAMETER_NAME')
db_host = os.getenv('DATABASE_HOST_PARAMETER_NAME')
db_user = os.getenv('DATABASE_USER_PARAMETER_NAME')
db_pass = os.getenv('DATABASE_PASSWORD_PARAMETER_NAME')

ssm_client = boto3.client('ssm')


def get_target_database():
    def get_ssm_value(app_path, parameter_name):
        response = ssm_client.get_parameter(Name=f'{app_path}/{parameter_name}', WithDecryption=True)
        return response['Parameter']['Value']

    ssm_path = f'/app/{app_environment}/{app_name}'

    return {'host': get_ssm_value(ssm_path, db_host),
            'port': get_ssm_value(ssm_path, db_port),
            'database': get_ssm_value(ssm_path, db_name),
            'user': get_ssm_value(ssm_path, db_user),
            'password': get_ssm_value(ssm_path, db_pass)}


def is_refresh_allowed(cursor):
    cursor.execute(f"SELECT COUNT(1) FROM pg_matviews where matviewname = '{view_name}';")
    view_count = cursor.fetchone()[0]
    logger.info(f'view count: {view_count}')
    return view_count > 0


def refresh_analytics_view(event, context):
    refresh_count = 0
    dsn = get_target_database()
    db_conn = psycopg2.connect(**dsn)

    with db_conn.cursor() as cursor:
        if is_refresh_allowed(cursor):
            cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name};")
            cursor.execute(
                f"INSERT INTO {log_table_name} (id, created_at) VALUES (DEFAULT, now());")
            refresh_count += 1

    db_conn.commit()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Processed {app_name} database, {refresh_count} view(s) refreshed.",
        }),
    }
