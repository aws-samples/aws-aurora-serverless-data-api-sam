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

import json
import os
import boto3
from .logger import get_logger

logger = get_logger(__name__)

is_lambda_environment = (os.getenv('AWS_LAMBDA_FUNCTION_NAME') != None)

# AWS X-Ray support
from aws_xray_sdk.core import xray_recorder, patch_all
if is_lambda_environment:
    patch_all()

ec2_table_name = os.getenv('EC2_TABLE_NAME', 'ec2')
package_table_name = os.getenv('PACKAGE_TABLE_NAME', 'package')
ec2_package_table_name = os.getenv('EC2_PACKAGE_TABLE_NAME', 'ec2_package')

class DataAccessLayerException(Exception):

    def __init__(self, original_exception):
        self.original_exception = original_exception

class DataAccessLayer:

    def __init__(self, database_name, db_cluster_arn, db_credentials_secrets_store_arn):
        self._rdsdata_client = boto3.client('rds-data')
        self._database_name = database_name
        self._db_cluster_arn = db_cluster_arn
        self._db_credentials_secrets_store_arn = db_credentials_secrets_store_arn

    @staticmethod
    def _xray_start(segment_name):
        if is_lambda_environment and xray_recorder:
            xray_recorder.begin_subsegment(segment_name)

    @staticmethod
    def _xray_stop():
        if is_lambda_environment and xray_recorder:
            xray_recorder.end_subsegment()

    @staticmethod
    def _xray_add_metadata(name, value):
        if is_lambda_environment and xray_recorder and xray_recorder.current_subsegment():
            return xray_recorder.current_subsegment().put_metadata(name, value)

    def execute_statement(self, sql_stmt, sql_params=[], transaction_id=None):
        parameters = f' with parameters: {sql_params}' if len(sql_params) > 0 else ''
        logger.debug(f'Running SQL statement: {sql_stmt}{parameters}')
        DataAccessLayer._xray_start('execute_statement')
        try:
            DataAccessLayer._xray_add_metadata('sql_statement', sql_stmt)
            parameters = {
                'secretArn': self._db_credentials_secrets_store_arn,
                'database': self._database_name,
                'resourceArn': self._db_cluster_arn,
                'sql': sql_stmt,
                'parameters': sql_params
            }
            if transaction_id is not None:
                parameters['transactionId'] = transaction_id
            result = self._rdsdata_client.execute_statement(**parameters)
        except Exception as e:
            logger.debug(f'Error running SQL statement (error class: {e.__class__})')
            raise DataAccessLayerException(e) from e
        else:
            DataAccessLayer._xray_add_metadata('rdsdata_executesql_result', json.dumps(result))
            return result
        finally:
           DataAccessLayer._xray_stop()

    def batch_execute_statement(self, sql_stmt, sql_param_sets, batch_size, transaction_id=None):
        parameters = f' with parameters: {sql_param_sets}' if len(sql_param_sets) > 0 else ''
        logger.debug(f'Running SQL statement: {sql_stmt}{parameters}')
        DataAccessLayer._xray_start('batch_execute_statement')
        try:
            array_length = len(sql_param_sets)
            num_batches = 1 + len(sql_param_sets)//batch_size
            results = []
            for i in range(0, num_batches):
                start_idx = i*batch_size
                end_idx = min(start_idx + batch_size, array_length)
                batch_sql_param_sets = sql_param_sets[start_idx:end_idx]
                if len(batch_sql_param_sets) > 0:
                    print(f'Running SQL statement: [batch #{i+1}/{num_batches}, batch size {batch_size}, SQL: {sql_stmt}]')
                    DataAccessLayer._xray_add_metadata('sql_statement', sql_stmt)
                    parameters = {
                        'secretArn': self._db_credentials_secrets_store_arn,
                        'database': self._database_name,
                        'resourceArn': self._db_cluster_arn,
                        'sql': sql_stmt,
                        'parameterSets': batch_sql_param_sets
                    }
                    if transaction_id is not None:
                        parameters['transactionId'] = transaction_id
                    result = self._rdsdata_client.batch_execute_statement(**parameters)
                    results.append(result)
        except Exception as e:
            logger.debug(f'Error running SQL statement (error class: {e.__class__})')
            raise DataAccessLayerException(e) from e
        else:
            DataAccessLayer._xray_add_metadata('rdsdata_executesql_result', json.dumps(result))
            return results
        finally:
           DataAccessLayer._xray_stop()

    #-----------------------------------------------------------------------------------------------
    # Package Functions
    #-----------------------------------------------------------------------------------------------
    def find_package(self, package_name, package_version):
        DataAccessLayer._xray_start('find_package')
        try:
            sql_parameters = [
                {'name':'package_name', 'value':{'stringValue': package_name}},
                {'name':'package_version', 'value':{'stringValue': package_version}},
            ]
            sql = f'select package_name, package_version' \
                f' from {package_table_name}' \
                f' where package_name=:package_name' \
                f' and package_version=:package_version'
            response = self.execute_statement(sql, sql_parameters)
            results = [
                {
                    'package_name': record[0]['stringValue'],
                    'package_version': record[1]['stringValue']
                }
                for record in response['records']
            ]
            return results
        except DataAccessLayerException as de:
            raise de
        except Exception as e:
            raise DataAccessLayerException(e) from e
        finally:
            DataAccessLayer._xray_stop()

    def _save_package(self, package_name, package_version, ignore_key_conflict=True):
        DataAccessLayer._xray_start('save_package')
        try:
            ignore = 'ignore' if ignore_key_conflict else ''
            sql_parameters = [
                {'name':'package_name', 'value':{'stringValue': package_name}},
                {'name':'package_version', 'value':{'stringValue': package_version}},
            ]
            sql = f'insert {ignore} into {package_table_name} ' \
                f' (package_name, package_version)' \
                f' values (:package_name,:package_version)'
            response = self.execute_statement(sql, sql_parameters)
            return response
        finally:
            DataAccessLayer._xray_stop()

    def _save_packages_batch(self, package_list, batch_size=200, ignore_key_conflict=True):
        DataAccessLayer._xray_start('save_packages_batch')
        try:
            ignore = 'ignore' if ignore_key_conflict else ''
            sql_parameter_sets = []
            for package in package_list:
                sql_parameters = [
                    {'name':'package_name', 'value':{'stringValue': package['package_name']}},
                    {'name':'package_version', 'value':{'stringValue': package['package_version']}}
                ]
                sql_parameter_sets.append(sql_parameters)
            sql = f'insert {ignore} into {package_table_name}' \
                f' (package_name, package_version)' \
                f' values (:package_name, :package_version)'
            response = self.batch_execute_statement(sql, sql_parameter_sets, batch_size)
            return response
        finally:
            DataAccessLayer._xray_stop()

    #-----------------------------------------------------------------------------------------------
    # EC2-PACKAGE Functions
    #-----------------------------------------------------------------------------------------------
    def _find_ec2_package_relations(self, aws_instance_id):
        DataAccessLayer._xray_start('find_ec2_package_relations')
        try:
            sql_parameters = [
                {'name':'aws_instance_id', 'value':{'stringValue': aws_instance_id}}
            ]
            sql = f'select aws_instance_id, package_name, package_version' \
                f' from {ec2_package_table_name}' \
                f' where aws_instance_id=:aws_instance_id'
            response = self.execute_statement(sql, sql_parameters)
            results = [
                {
                    'aws_instance_id': record[0]['stringValue'],
                    'package_name': record[1]['stringValue'],
                    'package_version': record[2]['stringValue']
                }
                for record in response['records']
            ]
            return results
        finally:
            DataAccessLayer._xray_stop()

    def _save_ec2_package_relation(self, aws_instance_id, package_name, package_version):
        DataAccessLayer._xray_start('save_ec2_package_relation')
        try:
            sql_parameters = [
                {'name':'aws_instance_id', 'value':{'stringValue': aws_instance_id}},
                {'name':'package_name', 'value':{'stringValue': package_name}},
                {'name':'package_version', 'value':{'stringValue': package_version}},
            ]
            sql = f'insert into {ec2_package_table_name}' \
                f' (aws_instance_id, package_name, package_version)' \
                f' values (:aws_instance_id, :package_name, :package_version)'
            response = self.execute_statement(sql, sql_parameters)
            return response
        finally:
            DataAccessLayer._xray_stop()

    def _save_ec2_package_relations_batch(self, aws_instance_id, package_list, batch_size=200, ignore_key_conflict=True):
        DataAccessLayer._xray_start('save_ec2_package_relations_batch')
        try:
            ignore = 'ignore' if ignore_key_conflict else ''
            sql_parameter_sets = []
            for package in package_list:
                sql_parameters = [
                    {'name':'aws_instance_id', 'value':{'stringValue': aws_instance_id}},
                    {'name':'package_name', 'value':{'stringValue': package['package_name']}},
                    {'name':'package_version', 'value':{'stringValue': package['package_version']}}
                ]
                sql_parameter_sets.append(sql_parameters)
            sql = f'insert {ignore} into {ec2_package_table_name}' \
                f' (aws_instance_id, package_name, package_version)' \
                f' values (:aws_instance_id, :package_name, :package_version)'
            response = self.batch_execute_statement(sql, sql_parameter_sets, batch_size)
            return response
        finally:
            DataAccessLayer._xray_stop()

    #-----------------------------------------------------------------------------------------------
    # EC2 Functions
    #-----------------------------------------------------------------------------------------------
    def find_ec2(self, aws_instance_id):
        DataAccessLayer._xray_start('find_ec2')
        try:
            DataAccessLayer._xray_add_metadata('aws_instance_id', aws_instance_id)
            sql_parameters = [
                {'name':'aws_instance_id', 'value':{'stringValue': aws_instance_id}}
            ]
            sql = f'select aws_instance_id, aws_region, aws_account' \
                  f' from {ec2_table_name}' \
                  f' where aws_instance_id=:aws_instance_id'
            response = self.execute_statement(sql, sql_parameters)
            record = dict()
            returned_records = response['records']
            if len(returned_records) > 0:
                record['instance_id'] = returned_records[0][0]['stringValue']
                record['aws_region'] = returned_records[0][1]['stringValue']
                record['aws_account'] = returned_records[0][2]['stringValue']
                # find ec2-package relations and add packages to returned ec2 object
                ec2_package_relations = self._find_ec2_package_relations(aws_instance_id)
                record['packages'] = [ {'package_name': package['package_name'], 'package_version': package['package_version']} for package in ec2_package_relations]
            return record
        except DataAccessLayerException as de:
            raise de
        except Exception as e:
            raise DataAccessLayerException(e) from e
        finally:
           DataAccessLayer._xray_stop()

    def save_ec2(self, aws_instance_id, input_fields, batch_size=200):
        DataAccessLayer._xray_start('save_ec2')
        try:
            num_ec2_packages = len(input_fields['packages']) if 'packages' in input_fields else 0
            DataAccessLayer._xray_add_metadata('aws_instance_id', aws_instance_id)
            DataAccessLayer._xray_add_metadata('num_ec2_packages', num_ec2_packages)
            # packages have their own table, so remove it to construct the ec2 record
            ec2_fields = input_fields.copy()
            ec2_fields.pop('packages')
            sql_parameters = [
                {'name':'aws_instance_id', 'value':{'stringValue': aws_instance_id}},
                {'name':'aws_region', 'value':{'stringValue': ec2_fields['aws_region']}},
                {'name':'aws_account', 'value':{'stringValue': ec2_fields['aws_account']}},
            ]
            sql = f'insert into {ec2_table_name}' \
                f' (aws_instance_id, aws_region, aws_account)' \
                f' values (:aws_instance_id, :aws_region, :aws_account)'
            response = self.execute_statement(sql, sql_parameters)
            if 'packages' in input_fields:
                self._save_packages_batch(input_fields['packages'], batch_size)
                self._save_ec2_package_relations_batch(aws_instance_id, input_fields['packages'], batch_size)
            return response
        except DataAccessLayerException as de:
            raise de
        except Exception as e:
            raise DataAccessLayerException(e) from e
        finally:
           DataAccessLayer._xray_stop()
