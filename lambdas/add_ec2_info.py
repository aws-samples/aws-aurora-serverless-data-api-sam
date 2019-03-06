import boto3
import json
import os
from helper.dal import *
from helper.utils import *

database_name = os.getenv('DB_NAME')
db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
db_credentials_secrets_store_arn = os.getenv('DB_CRED_SECRETS_STORE_ARN')

dal = DataAccessLayer(database_name, db_cluster_arn, db_credentials_secrets_store_arn)

ami_valid_fields = ['aws_account', 'image_type', 'server_type', 'base_os', 'aws_root_ami_id', 
                    'aws_root_ami_region', 'release_version', 'ansible_playbook_label', 
                    'cm_state', 'jenkins_info', 'rpms']

#-----------------------------------------------------------------------------------------------
# Input Validation
#-----------------------------------------------------------------------------------------------
def validate_ami_path_parameters(event):
    if key_missing_or_empty_value(event, 'pathParameters'):
        raise ValueError('Invalid input - missing aws_instance_id as part of path parameters')
    if key_missing_or_empty_value(event['pathParameters'], 'aws_instance_id'):
        raise ValueError('Invalid input - missing aws_instance_id as part of path parameters')
    return event['pathParameters']['aws_instance_id']

#-----------------------------------------------------------------------------------------------
# Lambda Entrypoint
#-----------------------------------------------------------------------------------------------
def handler(event, context):
    print(f'Event received: {event}')
    try:
        aws_instance_id = validate_ami_path_parameters(event)
        if key_missing_or_empty_value(event, 'body'):
            raise ValueError('Invalid input - body must contain AMI mandatory attributes')
        input_fields = json.loads(event['body'])

        dal.save_ec2(aws_instance_id, input_fields)
        output = {
            'new_record': input_fields
        }
        return success(output)
    except Exception as e:
        print(f'Error: {e}')
        return error(400, str(e))