import boto3
import json
import os

def get_cfn_output(key, outputs):
    result = [ v['OutputValue'] for v in outputs if v['OutputKey'] == key ]
    return result[0] if len(result) > 0 else ''

# Retrieve required parameters from RDS stack exported output values
rds_stack_name = os.getenv('rds_stack_name')
cloudformation = boto3.resource('cloudformation')
stack = cloudformation.Stack(rds_stack_name)
database_name = get_cfn_output('DatabaseName', stack.outputs)
db_cluster_arn = get_cfn_output('DatabaseClusterArn', stack.outputs)
db_credentials_secrets_store_arn = get_cfn_output('DatabaseSecretArn', stack.outputs)
print(f'Database info: [name={database_name}, cluster arn={db_cluster_arn}, secrets arn={db_credentials_secrets_store_arn}]')

# Run DDL commands idempotently to create database and tables
rds_client = boto3.client('rds-data')

table_ddl_script_files = [
    'table_ec2.txt', 
    'table_package.txt', 
    'table_ec2_package.txt'
]

def execute_sql(sql):
    print(f'Running SQL statement: {sql}')
    response = rds_client.execute_sql(
        awsSecretStoreArn=db_credentials_secrets_store_arn,
        database=database_name,
        dbClusterOrInstanceArn=db_cluster_arn,
        sqlStatements=sql
    )
    return response

execute_sql(f'create database if not exists {database_name}; use {database_name};')

for table_ddl_script_file in table_ddl_script_files:
    print(f"Creating table from DDL file: {table_ddl_script_file}")
    with open(table_ddl_script_file, 'r') as ddl_script:
        ddl_script_content=ddl_script.read()
        execute_sql(ddl_script_content)

response = execute_sql(f'show tables')
print(response)

