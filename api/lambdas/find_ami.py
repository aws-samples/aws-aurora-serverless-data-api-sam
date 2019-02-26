import boto3
import json

# TODO: 
database_name='ess_cmdb'
db_cluster_arn='arn:aws:rds:us-east-1:665243897136:cluster:ess-cmdb'
db_credentials_secrets_store_arn='arn:aws:secretsmanager:us-east-1:665243897136:secret:dev/cmdb/aurora-HlUTfC'

client = boto3.client('rds-data')

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

def build_ami_object(response):
    values = response['sqlStatementResults'][0]['resultFrame']['records'][0]
    names = response['sqlStatementResults'][0]['resultFrame']['resultSetMetadata'][0]
    for idx, name in enumerate(names):
        print(f'name: {values[idx]}')


def build_sql_statement(aws_image_id, aws_region):
    return f'SELECT * FROM ami WHERE aws_image_id="{aws_image_id}" AND aws_region="{aws_region}"'

def find_ami(event):
    aws_image_id, aws_region = validate_ami_path_parameters(event)
    sql_stmt = build_sql_statement(aws_image_id, aws_region)
    print(f'Search exact AMI (SQL statement): {sql_stmt}')
    response = client.execute_sql(
        awsSecretStoreArn=db_credentials_secrets_store_arn,
        database=database_name,
        dbClusterOrInstanceArn=db_cluster_arn,
        sqlStatements=sql_stmt
    )
    if len(response['sqlStatementResults'][0]['resultFrame']['records']) > 0:
        return build_ami_object(response), True
    return {}, False

def success(output):
    return {
        'statusCode': 200,
        'body': json.dumps(output)
    }

def error(error_code, error):
    return {
        'statusCode': error_code,
        'body': error
    }

def handler(event, context):
    try:
        response, was_ami_found = find_ami(event)
        output = {
            'event': event,
            'db_response': response
            # 'new_record': record
        }
        print(f'Output: {response}')
        return success(output)
    except Exception as e:
        print(f'Error: {e}')
        return error(str(e), 400)

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
            "aws_image_id": "ami-00000001",
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
        # "body": "{\n    \"aws_account\": \"123456789012\", \n    \"image_type\": \"root\",\n    \"server_type\": \"mail server\",\n    \"base_os\": \"centos 7-5.1804\",\n    \"aws_root_ami_id\": \"ami-10000001\",\n    \"aws_root_ami_region\": \"us-east-1\",     \n    \"release_version\": \"mojave\",\n    \"ansible_playbook_label\": \"playbook-1\",\n    \"cm_state\": \"ami-created\",\n    \"jenkins_info\": \"jenkins job 0001\"\n}"
        "body": "{\n    \"aws_account\": \"123456789012\", \n    \"image_type\": \"root\",\n    \"server_type\": \"mail server\",\n    \"base_os\": \"centos 7-5.1804\",\n    \"aws_root_ami_id\": \"ami-10000001\",\n    \"aws_root_ami_region\": \"us-east-1\",     \n    \"release_version\": \"mojave\",\n    \"ansible_playbook_label\": \"playbook-1\",\n    \"jenkins_info\": \"jenkins job 0001\"\n}"
    }
    handler(event,{})
