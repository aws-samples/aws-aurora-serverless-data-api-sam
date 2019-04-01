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
import pymysql
from .logging import get_logger

logger = get_logger(__name__)

# AWS X-Ray support
from aws_xray_sdk.core import xray_recorder, patch_all
patch_all()

ec2_table_name = os.getenv('EC2_TABLE_NAME', 'ec2')
package_table_name = os.getenv('PACKAGE_TABLE_NAME', 'package')
ec2_package_table_name = os.getenv('EC2_PACKAGE_TABLE_NAME', 'ec2_package')

class DataAccessLayer:

    def __init__(self, database_name, db_cluster_arn, db_credentials_secrets_store_arn):
        self._rdsdata_client = boto3.client('rds-data')
        self._database_name = database_name
        self._db_cluster_arn = db_cluster_arn
        self._db_credentials_secrets_store_arn = db_credentials_secrets_store_arn

    def _xray_add_metadata(self, name, value):
        if xray_recorder and xray_recorder.current_subsegment():
            return xray_recorder.current_subsegment().put_metadata(name, value)

    @staticmethod
    def _escape_sql_string(string_value):
        escaped_string = pymysql.escape_string(string_value.strip())
        logger.debug(f'Escaped SQL String [before: {string_value}, after: {escaped_string}]')
        return escaped_string

    @xray_recorder.capture('execute_sql')
    def execute_sql(self, sql_stmt):
        logger.debug(f'Running SQL: {sql_stmt}')
        self._xray_add_metadata('sql_statement', sql_stmt)
        result = self._rdsdata_client.execute_sql(
            awsSecretStoreArn=self._db_credentials_secrets_store_arn,
            database=self._database_name,
            dbClusterOrInstanceArn=self._db_cluster_arn,
            sqlStatements=sql_stmt)
        self._xray_add_metadata('rdsdata_executesql_result', json.dumps(result))
        return result

    @xray_recorder.capture('build_object_from_db_response')
    def _build_object_from_db_response(self, db_response):
        list_objs = []
        num_records = len(db_response['sqlStatementResults'][0]['resultFrame']['records'])
        if num_records > 0:
            for i in range(0,num_records):
                obj = dict()
                values = db_response['sqlStatementResults'][0]['resultFrame']['records'][i]['values']
                names = db_response['sqlStatementResults'][0]['resultFrame']['resultSetMetadata']['columnMetadata']
                for idx, metadata in enumerate(names):
                    field_name = metadata['name']
                    field_value = values[idx]['stringValue']
                    obj[field_name] = field_value
                list_objs.append(obj)
        return list_objs

    #-----------------------------------------------------------------------------------------------
    # Package Functions
    #-----------------------------------------------------------------------------------------------
    @xray_recorder.capture('find_package')
    def find_package(self, package_name, package_version):
        sql = f'select package_name, package_version' \
              f' from {package_table_name}' \
              f' where package_name="{DataAccessLayer._escape_sql_string(package_name)}"' \
              f' and package_version="{DataAccessLayer._escape_sql_string(package_version)}"'
        response = self.execute_sql(sql)
        return self._build_object_from_db_response(response)

    @xray_recorder.capture('save_package')
    def save_package(self, package_name, package_version, ignore_key_conflict=True):
        ignore = 'ignore' if ignore_key_conflict else ''
        package_name_esc = DataAccessLayer._escape_sql_string('package_name')
        package_version_esc = DataAccessLayer._escape_sql_string('package_version')
        sql = f'insert {ignore} into {package_table_name} ' \
              f' (package_name, package_version)' \
              f' values ("{package_name_esc}","{package_version_esc}")'
        response = self.execute_sql(sql)
        return response

    @xray_recorder.capture('save_packages_batch')
    def _save_packages_batch(self, package_list, batch_size=200, ignore_key_conflict=True):
        ignore = 'ignore' if ignore_key_conflict else ''
        sql_stmt = ''
        for idx, package in enumerate(package_list):
            package_name_esc = DataAccessLayer._escape_sql_string(package['package_name'])
            package_version_esc = DataAccessLayer._escape_sql_string(package['package_version'])
            package_sql = f'insert {ignore} into {package_table_name}' \
                          f' (package_name, package_version)' \
                          f' values ("{package_name_esc}","{package_version_esc}")'
            sql_stmt = f'{package_sql};{sql_stmt}'
            if (1+idx) % batch_size == 0:
                self.execute_sql(sql_stmt)
                sql_stmt = ''
        if len(sql_stmt) > 0:
            self.execute_sql(sql_stmt)

    #-----------------------------------------------------------------------------------------------
    # EC2-PACKAGE Functions
    #-----------------------------------------------------------------------------------------------
    @xray_recorder.capture('find_ec2_package_relations')
    def _find_ec2_package_relations(self, aws_instance_id):
        aws_instance_id_esc = DataAccessLayer._escape_sql_string(aws_instance_id)
        sql = f'select aws_instance_id, package_name, package_version' \
              f' from {ec2_package_table_name}' \
              f' where aws_instance_id="{aws_instance_id_esc}"'
        response = self.execute_sql(sql)
        return self._build_object_from_db_response(response)

    @xray_recorder.capture('save_ec2_package_relation')
    def _save_ec2_package_relation(self, aws_instance_id, package_name, package_version):
        aws_instance_id_esc = DataAccessLayer._escape_sql_string(aws_instance_id)
        package_name_esc = DataAccessLayer._escape_sql_string('package_name')
        package_version_esc = DataAccessLayer._escape_sql_string('package_version')
        sql = f'insert into {ec2_package_table_name}' \
              f' (aws_instance_id, package_name, package_version)' \
              f' values ("{aws_instance_id_esc}", "{package_name_esc}", "{package_version_esc}")'
        response = self.execute_sql(sql)
        return response

    @xray_recorder.capture('save_ec2_package_relations_batch')
    def _save_ec2_package_relations_batch(self, aws_instance_id, package_list, batch_size=200, ignore_key_conflict=True):
        ignore = 'ignore' if ignore_key_conflict else ''
        sql_stmt = ''
        aws_instance_id_esc = DataAccessLayer._escape_sql_string(aws_instance_id)
        for idx, package in enumerate(package_list):
            package_name_esc = DataAccessLayer._escape_sql_string(package['package_name'])
            package_version_esc = DataAccessLayer._escape_sql_string(package['package_version'])
            relation_sql = f'insert {ignore} into {ec2_package_table_name}' \
                           f' (aws_instance_id, package_name, package_version)' \
                           f' values ("{aws_instance_id_esc}", "{package_name_esc}","{package_version_esc}")'
            sql_stmt = f'{relation_sql};{sql_stmt}'
            if (1+idx) % batch_size == 0:
                self.execute_sql(sql_stmt)
                sql_stmt = ''
        if len(sql_stmt) > 0:
            self.execute_sql(sql_stmt)

    #-----------------------------------------------------------------------------------------------
    # EC2 Functions
    #-----------------------------------------------------------------------------------------------
    def _build_ec2_record(self, aws_instance_id, fields):
        record = fields.copy()
        record['aws_instance_id'] =  aws_instance_id
        return record

    def _build_ec2_insert_sql_statement(self, record):
        sql = list()
        sql.append(f'insert into {ec2_table_name} (')
        sql.append(', '.join(record.keys()))
        sql.append(') values (')
        sql.append(', '.join(f'"{DataAccessLayer._escape_sql_string(v)}"' for v in record.values()))
        sql.append(')')
        return ''.join(sql)

    @xray_recorder.capture('find_ec2')
    def find_ec2(self, aws_instance_id):
        self._xray_add_metadata('aws_instance_id', aws_instance_id)
        sql = f'select aws_instance_id, aws_region, aws_account, creation_date_utc' \
              f' from {ec2_table_name}' \
              f' where aws_instance_id="{DataAccessLayer._escape_sql_string(aws_instance_id)}"'

        response = self.execute_sql(sql)
        ec2s = self._build_object_from_db_response(response)
        for ec2_obj in ec2s:
            # find ec2-package relations and add packages to returned ec2 object
            ec2_package_relations = self._find_ec2_package_relations(aws_instance_id)
            ec2_obj['packages'] = [ {'package_name': package['package_name'], 'package_version': package['package_version']} for package in ec2_package_relations]
        return ec2s

    @xray_recorder.capture('save_ec2')
    def save_ec2(self, aws_instance_id, input_fields):
        num_ec2_packages = len(input_fields['packages']) if 'packages' in input_fields else 0
        self._xray_add_metadata('aws_instance_id', aws_instance_id)
        self._xray_add_metadata('num_ec2_packages', num_ec2_packages)
        # packages have their own table, so remove it to construct the ec2 record
        ec2_fields = input_fields.copy()
        ec2_fields.pop('packages')
        ec2_record = self._build_ec2_record(aws_instance_id, ec2_fields)
        sql_stmt = self._build_ec2_insert_sql_statement(ec2_record)
        response = self.execute_sql(sql_stmt)
        if 'packages' in input_fields:
            self._save_packages_batch(input_fields['packages'])
            self._save_ec2_package_relations_batch(aws_instance_id, input_fields['packages'] )
