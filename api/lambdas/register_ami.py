import boto3
import json
import os

client = boto3.client('rds-data')

ami_table_name = os.getenv('AMI_TABLE_NAME', 'ami')
rpm_table_name = os.getenv('RPM_TABLE_NAME', 'rpm')
ami_rpm_table_name = os.getenv('AMI_RPM_TABLE_NAME', 'ami_rpm')

# TODO: use environment variables
database_name='ess_cmdb'
db_cluster_arn='arn:aws:rds:us-east-1:665243897136:cluster:ess-cmdb'
db_credentials_secrets_store_arn='arn:aws:secretsmanager:us-east-1:665243897136:secret:dev/cmdb/aurora-HlUTfC'

ami_valid_fields = ['aws_account', 'image_type', 'server_type', 'base_os', 'aws_root_ami_id', 
                    'aws_root_ami_region', 'release_version', 'ansible_playbook_label', 
                    'cm_state', 'jenkins_info', 'rpms']

#-----------------------------------------------------------------------------------------------
# Generic Functions
#-----------------------------------------------------------------------------------------------
def execute_sql(sql_stmt):
    print(f'Running SQL: {sql_stmt}')
    return client.execute_sql(
        awsSecretStoreArn=db_credentials_secrets_store_arn,
        database=database_name,
        dbClusterOrInstanceArn=db_cluster_arn,
        sqlStatements=sql_stmt
)

def key_missing_or_empty_value(d, key):
    return not key in d or not d[key]

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

def build_object_from_db_response(db_response):
    obj = dict()
    if len(db_response['sqlStatementResults'][0]['resultFrame']['records']) > 0:
        values = db_response['sqlStatementResults'][0]['resultFrame']['records'][0]['values']
        names = db_response['sqlStatementResults'][0]['resultFrame']['resultSetMetadata']['columnMetadata']
        for idx, metadata in enumerate(names):
            field_name = metadata['name']
            field_value = values[idx]['stringValue']
            obj[field_name] = field_value
    return obj

#-----------------------------------------------------------------------------------------------
# RPM Functions
#-----------------------------------------------------------------------------------------------
def find_rpm(name, version, repo):
    sql = f'select * from {rpm_table_name} where name="{name}" and version="{version}" and repo="{repo}"'
    response = execute_sql(sql)
    return build_object_from_db_response(response)

def insert_rpm(name, version, repo):
    sql = f'insert into {rpm_table_name} (name, version, repo) values ("{name}","{version}","{repo}")'
    response = execute_sql(sql)
    return response

#-----------------------------------------------------------------------------------------------
# AMI-RPM Functions
#-----------------------------------------------------------------------------------------------
def save_ami_to_db_rpm_relation(aws_image_id, aws_region, rpm_name, rpm_version, rpm_repo):
    sql = f'insert into {ami_rpm_table_name} (aws_image_id, aws_region, rpm_name, rpm_version, rpm_repo) values ("{aws_image_id}", "{aws_region}", "{rpm_name}", "{rpm_version}", "{rpm_repo}")'
    response = execute_sql(sql)
    return response

#-----------------------------------------------------------------------------------------------
# AMI Functions
#-----------------------------------------------------------------------------------------------
def build_ami_record(aws_image_id, aws_region, fields):
    record = fields.copy()
    record['aws_image_id'] =  aws_image_id
    record['aws_region'] = aws_region
    return record

def build_ami_insert_sql_statement(record):
    sql = list()
    sql.append(f'INSERT INTO {ami_table_name} (')
    sql.append(', '.join(record.keys()))
    sql.append(') VALUES (')
    sql.append(', '.join(f'"{v}"' for v in record.values()))
    sql.append(')')
    return ''.join(sql)

def save_ami_to_db(aws_image_id, aws_region, input_fields):
    # rpms have their own table, so remove it to construct the ami record
    ami_fields = input_fields.copy()
    ami_fields.pop('rpms')
    ami_record = build_ami_record(aws_image_id, aws_region, ami_fields)
    sql_stmt = build_ami_insert_sql_statement(ami_record)
    # insert ami record in db
    response = execute_sql(sql_stmt)

    # we might have to add rpms if they're new...
    if 'rpms' in input_fields:
        for rpm in input_fields['rpms']:
            rpm_obj = find_rpm(rpm['name'], rpm['version'], rpm['repo'])
            if not rpm_obj:
                insert_rpm(rpm['name'], rpm['version'], rpm['repo'])
            # also need to add an ami-rpm relationship regardless
            save_ami_to_db_rpm_relation(aws_image_id, aws_region, rpm['name'], rpm['version'], rpm['repo'])

#-----------------------------------------------------------------------------------------------
# Lambda-specific Functions
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

        save_ami_to_db(aws_image_id, aws_region, input_fields)
        output = {
            # 'event': event,
            # 'db_response': response,
            'new_record': input_fields
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
            "aws_image_id": "ami-00070008",
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
        'body':'{\n "aws_account": "123456789012", \n "image_type": "root",\n "server_type": "mail server",\n "base_os": "centos 7-5.1804",\n "aws_root_ami_id": "ami-10000001",\n "aws_root_ami_region": "us-east-1", \n "release_version": "mojave",\n "ansible_playbook_label": "playbook-1",\n "cm_state": "created",\n "jenkins_info": "jenkins job 0001",\n "rpms": [\n \t{"name": "rpm-1", "version": "v1", "repo": "repo-1"},\n \t{"name": "rpm-1", "version": "v2", "repo": "repo-1"},\n \t{"name": "rpm-2", "version": "v1", "repo": "repo-1"},\n \t{"name": "rpm-3", "version": "v1", "repo": "repo-2"}\n ]\n}'
        # "body": "{\n    \"aws_account\": \"123456789012\", \n    \"image_type\": \"root\",\n    \"server_type\": \"mail server\",\n    \"base_os\": \"centos 7-5.1804\",\n    \"aws_root_ami_id\": \"ami-10000001\",\n    \"aws_root_ami_region\": \"us-east-1\",     \n    \"release_version\": \"mojave\",\n    \"ansible_playbook_label\": \"playbook-1\",\n    \"cm_state\": \"ami-created\",\n    \"jenkins_info\": \"jenkins job 0001\"\n}"
        # "body": "{\n    \"aws_account\": \"123456789012\", \n    \"image_type\": \"root\",\n    \"server_type\": \"mail server\",\n    \"base_os\": \"centos 7-5.1804\",\n    \"aws_root_ami_id\": \"ami-10000001\",\n    \"aws_root_ami_region\": \"us-east-1\",     \n    \"release_version\": \"mojave\",\n    \"ansible_playbook_label\": \"playbook-1\",\n    \"jenkins_info\": \"jenkins job 0001\"\n}"
    }
    result = handler(event,{})
    print(f"Result: {result}")
    # rpm_obj = find_rpm('rpm-1', 'v1', 'repo-1')
    # if (rpm_obj):
    #     print(rpm_obj)
    # else:
    #     print('cant find rpm')
