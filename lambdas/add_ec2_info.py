"""
  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Permission is hereby granted, free of charge, to any person obtaining a copy of this
  software and associated documentation files (the "Software"), to deal in the Software
  without restriction, including without limitation the rights to use, copy, modify,
  merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
  INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
  PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
  HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import os
from helper.dal import *
from helper.lambdautils import *
from helper.logger import get_logger

logger = get_logger(__name__)

database_name = os.getenv('DB_NAME')
db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
db_credentials_secrets_store_arn = os.getenv('DB_CRED_SECRETS_STORE_ARN')

dal = DataAccessLayer(database_name, db_cluster_arn, db_credentials_secrets_store_arn)

ec2_valid_fields = ['aws_account', 'aws_region', 'packages']

#-----------------------------------------------------------------------------------------------
# Input Validation
#-----------------------------------------------------------------------------------------------
def validate_ec2_path_parameters(event):
    if key_missing_or_empty_value(event, 'pathParameters'):
        raise ValueError('Invalid input - missing aws_instance_id as part of path parameters')
    if key_missing_or_empty_value(event['pathParameters'], 'aws_instance_id'):
        raise ValueError('Invalid input - missing aws_instance_id as part of path parameters')
    return event['pathParameters']['aws_instance_id']

def validate_ec2_input_parameters(input_fields):
    for field in input_fields:
        if field not in ec2_valid_fields:
            raise ValueError(f'Invalid EC2 input parameter: {field}')

def validate_input(event):
    aws_instance_id = validate_ec2_path_parameters(event)
    if key_missing_or_empty_value(event, 'body'):
        raise ValueError('Invalid input - body must contain EC2 mandatory attributes')
    input_fields = json.loads(event['body'])
    validate_ec2_input_parameters(input_fields.keys())
    return aws_instance_id, input_fields

#-----------------------------------------------------------------------------------------------
# Lambda Entrypoint
#-----------------------------------------------------------------------------------------------
def handler(event, context):
    try:
        logger.info(f'Event received: {event}')
        aws_instance_id, input_fields = validate_input(event)
        dal.save_ec2(aws_instance_id, input_fields)
        output = {'new_record': input_fields}
        logger.debug(f'Output: {output}')
        return success(output)
    except Exception as e:
        return handle_error(e)