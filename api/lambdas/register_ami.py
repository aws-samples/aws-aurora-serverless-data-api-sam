import boto3
import json
import os
from helper.dal import *
from helper.utils import *

database_name = os.getenv('DB_NAME', 'ess_cmdb')
db_cluster_arn = os.getenv('DB_CLUSTER_ARN', 'arn:aws:rds:us-east-1:665243897136:cluster:ess-cmdb')
db_credentials_secrets_store_arn = os.getenv('DB_CRED_SECRETS_STORE_ARN', 'arn:aws:secretsmanager:us-east-1:665243897136:secret:dev/cmdb/aurora-HlUTfC')

dal = DataAccessLayer(database_name, db_cluster_arn, db_credentials_secrets_store_arn)

ami_valid_fields = ['aws_account', 'image_type', 'server_type', 'base_os', 'aws_root_ami_id', 
                    'aws_root_ami_region', 'release_version', 'ansible_playbook_label', 
                    'cm_state', 'jenkins_info', 'rpms']

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

def validate_ami_fields(fields):
    for key in fields.keys():
        if key not in ami_valid_fields:
            raise ValueError('Invalid input - attribute {} is invalid'.format(key))
    if key_missing_or_empty_value(fields, 'aws_account'):
        raise ValueError('Invalid input - missing aws_account field for AMI')
    if key_missing_or_empty_value(fields, 'image_type'):
        raise ValueError('Invalid input - missing image_type field for AMI')
    if key_missing_or_empty_value(fields, 'server_type'):
        raise ValueError('Invalid input - missing server_type field for AMI')
    if key_missing_or_empty_value(fields, 'base_os'):
        raise ValueError('Invalid input - missing base_os field for AMI')
    if fields['image_type'] != 'root' and key_missing_or_empty_value(fields, 'aws_root_ami_id'):
        raise ValueError('Invalid input - missing aws_root_ami_id field for non-root AMI')
    if fields['image_type'] != 'root' and key_missing_or_empty_value(fields, 'aws_root_ami_region'):
        raise ValueError('Invalid input - missing aws_root_ami_region field for non-root AMI')
    if fields['image_type'] == 'root' and key_missing_or_empty_value(fields, 'cm_state'):
        raise ValueError('Invalid input - missing cm_state field for root AMI')
    return fields

#-----------------------------------------------------------------------------------------------
# Lambda Entrypoint
#-----------------------------------------------------------------------------------------------
def handler(event, context):
    print(f'Event received: {event}')
    try:
        aws_image_id, aws_region = validate_ami_path_parameters(event)
        if key_missing_or_empty_value(event, 'body'):
            raise ValueError('Invalid input - body must contain AMI mandatory attributes')
        input_fields = validate_ami_fields(json.loads(event['body']))

        dal.save_ami(aws_image_id, aws_region, input_fields)
        output = {
            # 'event': event,
            # 'db_response': response,
            'new_record': input_fields
        }
        return success(output)
    except Exception as e:
        print(f'Error: {e}')
        return error(400, str(e)) 