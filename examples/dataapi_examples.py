import boto3
import json
import os
import time

# Update these 3 parameters for your environment
database_name = 'ec2_inventory_db'
db_cluster_arn = 'arn:aws:rds:us-east-1:123456789012:cluster:dev-aurora-ec2-inventory-cluster'
db_credentials_secrets_store_arn = 'arn:aws:secretsmanager:us-east-1:123456789012:secret:dev-AuroraUserSecret-DhpkOI'

# This is the Data API client that will be used in our examples below
rds_client = boto3.client('rds-data')

#--------------------------------------------------------------------------------
# Helper Functions
#--------------------------------------------------------------------------------

# Timing function executions
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

#--------------------------------------------------------------------------------
# Various Examples of Using the Data API
#--------------------------------------------------------------------------------

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
    # populate table w/ some data for querying
    execute_statement('delete from package')
    for i in range(100,110):
        execute_statement(f'insert into package (package_name, package_version) values ("package-{i}", "version-1")')
        execute_statement(f'insert into package (package_name, package_version) values ("package-{i}", "version-2")')

# Simple select example with no parameters
@timeit
def example_simple_query():
    print('===== Example - Simple query =====')
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
@timeit
def example_parameterized_query():
    print('===== Example - Parameterized query =====')
    sql = 'select * from package where package_name=:package_name'
    package_name = 'package-100'
    sql_parameters = [{'name':'package_name', 'value':{'stringValue': f'{package_name}'}}]
    response = execute_statement(sql, sql_parameters)
    print(response['records'])

# Fetch results
# Order of parameters on select is relevant (eg, package_name, package_version)
@timeit
def example_format_query_results():
    print('===== Example - Format query results =====')

    # Formatting query returned Field
    def formatField(field):
        return list(field.values())[0]

    # Formatting query returned Record
    def formatRecord(record):
        return [formatField(field) for field in record]

    # Formatting query returned Field
    def formatRecords(records):
        return [formatRecord(record) for record in records]

    sql = 'select package_name, package_version from package'
    response = execute_statement(sql)
    print(formatRecords(response['records']))

# Simple insert example
@timeit
def example_simple_parameterized_insert():
    print('===== Example - Simple parameterized insert =====')
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
    print('===== Example - Exception handling - Duplicate Primary Key =====')
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
    print('===== Example - Batch insert =====')
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
# Here we redefine functions execute_statement() and batch_execute_statement() to support transactions
@timeit
def example_handling_transactions(package_start_idx, package_end_idx):

    @timeit
    def execute_statement(sql, sql_parameters=[], transaction_id=None):
        parameters = {
            'secretArn': db_credentials_secrets_store_arn,
            'database': database_name,
            'resourceArn': db_cluster_arn,
            'sql': sql,
            'parameters': sql_parameters
        }
        if transaction_id is not None:
            parameters['transactionId'] = transaction_id
        response = rds_client.execute_statement(**parameters)
        return response

    @timeit
    def batch_execute_statement(sql, sql_parameter_sets, transaction_id=None):
        parameters = {
            'secretArn': db_credentials_secrets_store_arn,
            'database': database_name,
            'resourceArn': db_cluster_arn,
            'sql': sql,
            'parameterSets': sql_parameter_sets
        }
        if transaction_id is not None:
            parameters['transactionId'] = transaction_id
        response = rds_client.batch_execute_statement(**parameters)
        return response

    print('===== Example - Handling transactions (commit and rollback) =====')
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
        response = batch_execute_statement(sql, sql_parameter_sets, transaction['transactionId'])
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

example_simple_query()
print('\n')

example_parameterized_query()
print('\n')

example_format_query_results()
print('\n')

example_simple_parameterized_insert()
print('\n')

example_exception_handling()
print('\n')

example_batch_insert()
print('\n')

# key 100 is a duplicate - transaction will rollback
example_handling_transactions(91,101)
print('\n')

# transaction will be committed successfully
example_handling_transactions(1000,1020)
