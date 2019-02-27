import boto3
import json
from helper.dal import *
from helper.utils import *

database_name = os.getenv('DB_NAME', 'ess_cmdb')
db_cluster_arn = os.getenv('DB_CLUSTER_ARN', 'arn:aws:rds:us-east-1:665243897136:cluster:ess-cmdb')
db_credentials_secrets_store_arn = os.getenv('DB_CRED_SECRETS_STORE_ARN', 'arn:aws:secretsmanager:us-east-1:665243897136:secret:dev/cmdb/aurora-HlUTfC')

dal = DataAccessLayer(database_name, db_cluster_arn, db_credentials_secrets_store_arn)

#-----------------------------------------------------------------------------------------------
# Input Validation
#-----------------------------------------------------------------------------------------------
def validate_ami_path_parameters(event):
    if key_missing_or_empty_value(event, 'pathParameters'):
        raise ValueError('Invalid input - missing aws_image_id and aws_region as part of path parameters')
    if key_missing_or_empty_value(event['pathParameters'], 'aws_image_id'):
        raise ValueError('Invalid input - missing aws_image_id as part of path parameters')
    if key_missing_or_empty_value(event['pathParameters'], 'aws_region'):
        raise ValueError('Invalid input - missing aws_region as part of path parameters')
    return event['pathParameters']['aws_image_id'], event['pathParameters']['aws_region']

def handler(event, context):
    try:
        aws_image_id, aws_region = validate_ami_path_parameters(event)
        list_amis = dal.find_ami(aws_image_id, aws_region)
        output = {
            # 'event': event,
            # 'db_response': response
            'record': list_amis[0] if len(list_amis) > 0 else {},
            'record_found': len(list_amis) > 0
        }
        print(f'Output: {output}')
        return success(output)
    except Exception as e:
        print(f'Error: {e}')
        return error(400, str(e)) 