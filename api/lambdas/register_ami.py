import boto3
import json

# TODO: 
database_name='ess_cmdb'
db_cluster_arn='arn:aws:rds:us-east-1:665243897136:cluster:ess-cmdb'
db_credentials_secrets_store_arn='arn:aws:secretsmanager:us-east-1:665243897136:secret:dev/cmdb/aurora-HlUTfC'

client = boto3.client('rds-data')
ami_valid_fields = ['aws_account', 'image_type', 'server_type', 'base_os', 'aws_root_ami_id', 
                    'aws_root_ami_region', 'release_version', 'ansible_playbook_label', 
                    'cm_state', 'jenkins_info']

def key_missing_or_empty_value(d, key):
    return not key in d or not d[key]

def validate_ami_path_parameters(event):
    if key_missing_or_empty_value(event, 'pathParameters'):
        raise ValueError('Invalid input - missing aws_image_id and aws_region as part of path parameters')
    if key_missing_or_empty_value(event['pathParameters'], 'aws_image_id'):
        raise ValueError('Invalid input - missing aws_image_id as part of path parameters')
    if key_missing_or_empty_value(event['pathParameters'], 'aws_region'):
        raise ValueError('Invalid input - missing aws_region as part of path parameters')
    return event['pathParameters']['aws_image_id'], event['pathParameters']['aws_region']

def validate_ami_fields(record):
    for key in record.keys():
        if key not in ami_valid_fields:
            raise ValueError('Invalid input - attribute {} is invalid'.format(key))
    if key_missing_or_empty_value(record, 'aws_account'):
        raise ValueError('Invalid input - missing aws_account field for AMI')
    if key_missing_or_empty_value(record, 'image_type'):
        raise ValueError('Invalid input - missing image_type field for AMI')
    if key_missing_or_empty_value(record, 'server_type'):
        raise ValueError('Invalid input - missing server_type field for AMI')
    if key_missing_or_empty_value(record, 'base_os'):
        raise ValueError('Invalid input - missing base_os field for AMI')
    if record['image_type'] != 'root' and key_missing_or_empty_value(record, 'aws_root_ami_id'):
        raise ValueError('Invalid input - missing aws_root_ami_id field for non-root AMI')
    if record['image_type'] != 'root' and key_missing_or_empty_value(record, 'aws_root_ami_region'):
        raise ValueError('Invalid input - missing aws_root_ami_region field for non-root AMI')
    if record['image_type'] == 'root' and key_missing_or_empty_value(record, 'cm_state'):
        raise ValueError('Invalid input - missing cm_state field for root AMI')
    return record

def create_ami_record(event):
    aws_image_id, aws_region = validate_ami_path_parameters(event)
    if key_missing_or_empty_value(event, 'body'):
        raise ValueError('Invalid input - body must contain AMI mandatory attributes')
    record = validate_ami_fields(json.loads(event['body']))
    record['aws_image_id'] =  aws_image_id
    record['aws_region'] = aws_region
    return record

def build_sql_statement(record):
    sql = list()
    sql.append(f'INSERT INTO ami (')
    sql.append(', '.join(record.keys()))
    sql.append(') VALUES (')
    sql.append(', '.join(f'"{v}"' for v in record.values()))
    sql.append(')')
    return ''.join(sql)

def store_ami(event):
    record = create_ami_record(event)
    sql_stmt = build_sql_statement(record)
    print(f'Store AMI SQL statement: {sql_stmt}')
    response = client.execute_sql(
        awsSecretStoreArn=db_credentials_secrets_store_arn,
        database=database_name,
        dbClusterOrInstanceArn=db_cluster_arn,
        sqlStatements=sql_stmt
    )
    return record, response

def success(output):
    return {
        'statusCode': 200,
        'body': json.dumps(output)
    }

def error(error_code, error):
    return {
        'statusCode': error_code,
        'body': json.dumps({
            'error_message': error
        })
    }

def handler(event, context):
    try:
        record, response = store_ami(event)
        output = {
            # 'event': event,
            # 'db_response': response,
            'new_record': record
        }
        return success(output)
    except Exception as e:
        print(f'Error: {e}')
        return error(400, str(e))

if __name__ == "__main__":
    event={
        "resource": "/ami/{aws_image_id}/{aws_region}",
        "path": "/ami/ami-00000001/us-east-1",
        "httpMethod": "POST",
        "headers": {
            "Accept": "*/*",
            "accept-encoding": "gzip, deflate",
            "cache-control": "no-cache",
            "Content-Type": "application/json",
            "Host": "9ru2poro88.execute-api.us-east-1.amazonaws.com",
            "Postman-Token": "4b9e5218-978d-42ea-9b18-ba4568f62df0",
            "User-Agent": "PostmanRuntime/7.3.0",
            "X-Amzn-Trace-Id": "Root=1-5c747f89-9713cbc075d265403910db80",
            "X-Forwarded-For": "72.21.196.65",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https"
        },
        "pathParameters": {
            "aws_image_id": "ami-00000008",
            "aws_region": "us-east-1"
        },
        "requestContext": {
            "resourceId": "trf23c",
            "resourcePath": "/ami/{aws_image_id}/{aws_region}",
            "httpMethod": "POST",
            "extendedRequestId": "VrjdiHUmoAMF41Q=",
            "requestTime": "25/Feb/2019:23:51:37 +0000",
            "path": "/Prod/ami/ami-00000001/us-east-1",
            "accountId": "665243897136",
            "protocol": "HTTP/1.1",
            "stage": "Prod",
            "domainPrefix": "9ru2poro88",
            "requestTimeEpoch": 1551138697815,
            "requestId": "4a4fa73d-3958-11e9-93b4-d1d6bd8c8dc1",
            "domainName": "9ru2poro88.execute-api.us-east-1.amazonaws.com",
            "apiId": "9ru2poro88"
        },
        "body": "{\n    \"aws_account\": \"123456789012\", \n    \"image_type\": \"root\",\n    \"server_type\": \"mail server\",\n    \"base_os\": \"centos 7-5.1804\",\n    \"aws_root_ami_id\": \"ami-10000001\",\n    \"aws_root_ami_region\": \"us-east-1\",     \n    \"release_version\": \"mojave\",\n    \"ansible_playbook_label\": \"playbook-1\",\n    \"cm_state\": \"ami-created\",\n    \"jenkins_info\": \"jenkins job 0001\"\n}"
        # "body": "{\n    \"aws_account\": \"123456789012\", \n    \"image_type\": \"root\",\n    \"server_type\": \"mail server\",\n    \"base_os\": \"centos 7-5.1804\",\n    \"aws_root_ami_id\": \"ami-10000001\",\n    \"aws_root_ami_region\": \"us-east-1\",     \n    \"release_version\": \"mojave\",\n    \"ansible_playbook_label\": \"playbook-1\",\n    \"jenkins_info\": \"jenkins job 0001\"\n}"
    }
    result = handler(event,{})
    print(f"Result: {result}")
