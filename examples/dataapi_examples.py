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

rds_client = boto3.client('rds-data')

def execute_statement(sql, sql_parameters=[]):
    response = rds_client.execute_statement(
        secretArn=db_credentials_secrets_store_arn,
        database=database_name,
        resourceArn=db_cluster_arn,
        sql=sql,
        parameters=sql_parameters
    )
    return response

execute_statement('delete from package')
execute_statement('insert into package (package_name, package_version) values ("package100", "version-1")')
execute_statement('insert into package (package_name, package_version) values ("package101", "version-1")')

# Create the DB Schema (here just table package)
def example0():
    print('===== Example - create schema from DDL file =====')
    execute_statement(f'create database if not exists {database_name}')
    table_ddl_script_file = 'table_package.txt'
    print(f"Creating table from DDL file: {table_ddl_script_file}")
    with open(table_ddl_script_file, 'r') as ddl_script:
        ddl_script_content=ddl_script.read()
        execute_statement(ddl_script_content)

# Simple select example with no parameters
def example1():
    print('===== Example - Simple select statement =====')
    def execute_statement(sql):
        response = rds_client.execute_statement(
            secretArn=db_credentials_secrets_store_arn,
            database=database_name,
            resourceArn=db_cluster_arn,
            sql=sql
        )
        return response

    response = execute_statement(f'select * from package')
    print(response['records'])

# Simple select example with parameters
# Talk about parameters as a means to prevent SQL injections
def example2():
    print('===== Example - select with parameters =====')
    sql = 'select * from package where package_name=:package_name'
    package_name = 'package100'
    sql_parameters = [{'name':'package_name', 'value':{'stringValue': f'{package_name}'}}]
    response = execute_statement(sql, sql_parameters)
    print(response['records'])

# Fetch results
# Order of parameters on select is relevant (eg, package_name, package_version)
def example3():
    print('===== Example - fetch select results =====')

    def build_object_from_response(response):
        result = []
        records = response['records']
        for record in records:
            obj = {
                'package_name': record[0]['stringValue'],
                'package_version': record[1]['stringValue']
            }
            result.append(obj)
        return result

    sql = 'select package_name, package_version from package'
    response = execute_statement(sql)
    result = build_object_from_response(response)
    print(result)

# Simple insert example
def example4():
    print('===== Example - simple insert with parameters =====')
    sql = 'insert into package (package_name, package_version) values (:package_name, :package_version)'
    sql_parameters = [
        {'name':'package_name', 'value':{'stringValue': 'package-2'}},
        {'name':'package_version', 'value':{'stringValue': 'version-1'}}
    ]
    response = execute_statement(sql, sql_parameters)
    print(f'Number of records updated: {response["numberOfRecordsUpdated"]}')

# Handling exceptions
def example5():
    print('===== Example - handling exceptions =====')
    class DataAccessLayerException(Exception):
        pass
    def add_package():
        try:
            sql = 'insert into package (package_name, package_version) values (:package_name, :package_version)'
            sql_parameters = [
                {'name':'package_name', 'value':{'stringValue': 'package-2'}},
                {'name':'package_version', 'value':{'stringValue': 'version-1'}}
            ]
            response = execute_statement(sql, sql_parameters)
            print(f'Number of records updated: {response["numberOfRecordsUpdated"]}')
        except Exception as e:
            raise DataAccessLayerException(e) from e
    try:
        add_package()
    except DataAccessLayerException as e:
        print(e)

# Introduce batch inserts
def batch_execute_statement(sql, sql_parameter_sets):
    response = rds_client.batch_execute_statement(
        secretArn=db_credentials_secrets_store_arn,
        database=database_name,
        resourceArn=db_cluster_arn,
        sql=sql,
        parameterSets=sql_parameter_sets
    )
    return response

# Batch insert example
# Ask Data API what's the max batch size!
def example6():
    print('===== Example - batch SQL statements =====')
    sql = 'insert into package (package_name, package_version) values (:package_name, :package_version)'
    sql_parameter_sets = []
    for i in range(10,20):
        entry = [
                {'name':'package_name', 'value':{'stringValue': f'package{i}'}},
                {'name':'package_version', 'value':{'stringValue': 'version-1'}}
        ]
        sql_parameter_sets.append(entry)
    response = batch_execute_statement(sql, sql_parameter_sets)
    print(f'Number of records updated: {len(response["updateResults"])}')

# Transactions (commit and rollback)
def example7():
    print('===== Example - transactions with commit and rollback =====')
    # begin transaction
    transaction = rds_client.begin_transaction(
        secretArn=db_credentials_secrets_store_arn,
        resourceArn=db_cluster_arn,
        database=database_name)
    try:
        sql = 'insert into package (package_name, package_version) values (:package_name, :package_version)'
        sql_parameter_sets = []
        for i in range(30,40):
            entry = [
                    {'name':'package_name', 'value':{'stringValue': f'package{i}'}},
                    {'name':'package_version', 'value':{'stringValue': 'version-1'}}
            ]
            sql_parameter_sets.append(entry)
        response = batch_execute_statement(sql, sql_parameter_sets)
    except Exception:
        transaction_response = rds_client.rollback_transaction(
            secretArn=db_credentials_secrets_store_arn,
            resourceArn=db_cluster_arn,
            transactionId=transaction['transactionId'])
    else:
        transaction_response = rds_client.commit_transaction(
            secretArn=db_credentials_secrets_store_arn,
            resourceArn=db_cluster_arn,
            transactionId=transaction['transactionId'])
        print(f'Number of records updated: {len(response["updateResults"])}')
    print(f'Transaction Status: {transaction_response["transactionStatus"]}')

# Running our examples in sequence
example0()
example1()
example2()
example3()
example4()
example5()
example6()
example7()

