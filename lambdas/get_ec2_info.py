from helper.dal import *
from helper.utils import *

database_name = os.getenv('DB_NAME')
db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
db_credentials_secrets_store_arn = os.getenv('DB_CRED_SECRETS_STORE_ARN')

dal = DataAccessLayer(database_name, db_cluster_arn, db_credentials_secrets_store_arn)

#-----------------------------------------------------------------------------------------------
# Input Validation
#-----------------------------------------------------------------------------------------------
def validate_path_parameters(event):
    if key_missing_or_empty_value(event, 'pathParameters'):
        raise ValueError('Invalid input - missing aws_instance_id as part of path parameters')
    if key_missing_or_empty_value(event['pathParameters'], 'aws_instance_id'):
        raise ValueError('Invalid input - missing aws_instance_id as part of path parameters')
    return event['pathParameters']['aws_instance_id']

def handler(event, context):
    try:
        aws_instance_id = validate_path_parameters(event)
        results = dal.find_ec2(aws_instance_id)
        output = {
            'record': results[0] if len(results) > 0 else {},
            'record_found': len(results) > 0
        }
        print(f'Output: {output}')
        return success(output)
    except Exception as e:
        print(f'Error: {e}')
        return error(400, str(e))