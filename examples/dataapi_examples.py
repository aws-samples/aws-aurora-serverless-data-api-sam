import boto3
import json
import os
import time

# Update these 3 parameters for your environment
database_name = 'ec2_inventory_db'
db_cluster_arn = 'arn:aws:rds:us-east-1:665243897136:cluster:dev-aurora-ec2-inventory-cluster'
db_credentials_secrets_store_arn = 'arn:aws:secretsmanager:us-east-1:665243897136:secret:dev-AuroraUserSecret-DhpkOI'

# This is the Data API client that will be used in our examples below
rds_client = boto3.client('rds-data')

def timeit(f):
    def timed(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        print(f'Function: {f.__name__}')
        print(f'*  args: {args}')
        print(f'*  kw: {kw}')
        print(f'*  execution time: {(te-ts)*1000:8.2f} ms')
        return result
    return timed

@timeit
def execute_statement(sql, sql_parameters=[]):
    response = rds_client.execute_statement(
        secretArn=db_credentials_secrets_store_arn,
        database=database_name,
        resourceArn=db_cluster_arn,
        sql=sql,
        parameters=sql_parameters
    )
    return response

# Create the DB Schema (here just table package)
@timeit
def example_create_table():
    print('===== Example - create schema from DDL file =====')
    execute_statement(f'create database if not exists {database_name}')
    table_ddl_script_file = 'table_package.txt'
    print(f"Creating table from DDL file: {table_ddl_script_file}")
    with open(table_ddl_script_file, 'r') as ddl_script:
        ddl_script_content=ddl_script.read()
        execute_statement(ddl_script_content)
    # add some data
    execute_statement('delete from package')
    for i in range(100,110):
        execute_statement(f'insert into package (package_name, package_version) values ("package-{i}", "version-1")')
        execute_statement(f'insert into package (package_name, package_version) values ("package-{i}", "version-2")')

# Simple select example with no parameters
@timeit
def example_simple_select():
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
    print(f'response: {response}')

# Simple select example with parameters
# Talk about parameters as a means to prevent SQL injections
@timeit
def example_select_with_parameters():
    print('===== Example - select with parameters =====')
    sql = 'select * from package where package_name=:package_name'
    package_name = 'package-100'
    sql_parameters = [{'name':'package_name', 'value':{'stringValue': f'{package_name}'}}]
    response = execute_statement(sql, sql_parameters)
    print(f'response: {response}')

# Fetch results
# Order of parameters on select is relevant (eg, package_name, package_version)
@timeit
def example_fetch_select_results():
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
    print(f'result: {result}')

# Simple insert example
@timeit
def example_simple_insert_with_parameters():
    print('===== Example - simple insert with parameters =====')
    sql = 'insert into package (package_name, package_version) values (:package_name, :package_version)'
    sql_parameters = [
        {'name':'package_name', 'value':{'stringValue': 'package-1'}},
        {'name':'package_version', 'value':{'stringValue': 'version-1'}}
    ]
    response = execute_statement(sql, sql_parameters)
    print(f'Number of records updated: {response["numberOfRecordsUpdated"]}')

# Handling exceptions
@timeit
def example_exception_handling():
    print('===== Example - handling exceptions - Duplicate Primary Key =====')
    class DataAccessLayerException(Exception):
        pass
    def add_package():
        try:
            sql = 'insert into package (package_name, package_version) values (:package_name, :package_version)'
            sql_parameters = [
                {'name':'package_name', 'value':{'stringValue': 'package-1'}},
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
@timeit
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
@timeit
def example_batch_insert():
    print('===== Example - batch SQL Insert statements =====')
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
@timeit
def example_transactions(package_start_idx, package_end_idx):
    print('===== Example - transactions with commit and rollback =====')
    # begin transaction
    transaction = rds_client.begin_transaction(
        secretArn=db_credentials_secrets_store_arn,
        resourceArn=db_cluster_arn,
        database=database_name)
    try:
        sql = 'insert into package (package_name, package_version) values (:package_name, :package_version)'
        sql_parameter_sets = []
        for i in range(package_start_idx,package_end_idx):
            entry = [
                    {'name':'package_name', 'value':{'stringValue': f'package-{i}'}},
                    {'name':'package_version', 'value':{'stringValue': 'version-1'}}
            ]
            sql_parameter_sets.append(entry)
        response = batch_execute_statement(sql, sql_parameter_sets)
    except Exception as e:
        print(f'Error: {e}')
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


# Running our examples in order
example_create_table()
print('\n')

example_simple_select()
print('\n')

example_select_with_parameters()
print('\n')

example_fetch_select_results()
print('\n')

example_simple_insert_with_parameters()
print('\n')

example_exception_handling()
print('\n')

example_batch_insert()
print('\n')

# key 100 is a duplicate - transaction will rollback
example_transactions(91,101)
print('\n')

# transaction will be committed successfully
example_transactions(1000,1020)
