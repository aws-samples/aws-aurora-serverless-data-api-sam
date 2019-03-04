#-----------------------------------------------------------------------------------------------
# Data Access Layer
#-----------------------------------------------------------------------------------------------

import boto3
import json
import os

client = boto3.client('rds-data')

ec2_table_name = os.getenv('EC2_TABLE_NAME', 'ec2')
package_table_name = os.getenv('PACKAGE_TABLE_NAME', 'package')
ec2_package_table_name = os.getenv('EC2_PACKAGE_TABLE_NAME', 'ec2_package')

class DataAccessLayer:

    def __init__(self, database_name, db_cluster_arn, db_credentials_secrets_store_arn):
        self._database_name = database_name
        self._db_cluster_arn = db_cluster_arn
        self._db_credentials_secrets_store_arn = db_credentials_secrets_store_arn

    def execute_sql(self, sql_stmt):
        print(f'Running SQL: {sql_stmt}')
        return client.execute_sql(
            awsSecretStoreArn=self._db_credentials_secrets_store_arn,
            database=self._database_name,
            dbClusterOrInstanceArn=self._db_cluster_arn,
            sqlStatements=sql_stmt
    )

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
    def find_package(self, name, version, repo):
        sql = f'select * from {package_table_name} where name="{name}" and version="{version}" and repo="{repo}"'
        response = self.execute_sql(sql)
        return self._build_object_from_db_response(response)

    def save_package(self, name, version, repo, ignore_key_conflict=True):
        ignore = 'ignore' if ignore_key_conflict else ''
        sql = f'insert {ignore} into {package_table_name} (name, version, repo) values ("{name}","{version}","{repo}")'
        response = self.execute_sql(sql)
        return response

    def save_packages_batch(self, package_list, batch_size=200, ignore_key_conflict=True):
        ignore = 'ignore' if ignore_key_conflict else ''
        sql_stmt = ''
        for idx, package in enumerate(package_list):
            package_sql = f'insert {ignore} into {package_table_name} (name, version, repo) values ("{package["name"]}","{package["version"]}","{package["repo"]}")'
            sql_stmt = f'{package_sql};{sql_stmt}'
            if (1+idx) % batch_size == 0:
                self.execute_sql(sql_stmt)
                sql_stmt = ''
        if len(sql_stmt) > 0:
            self.execute_sql(sql_stmt)

    #-----------------------------------------------------------------------------------------------
    # EC2-PACKAGE Functions
    #-----------------------------------------------------------------------------------------------
    def _find_ec2_package_relations(self, aws_image_id, aws_region):
        sql = f'select * from {ec2_package_table_name} where aws_image_id="{aws_image_id}" and aws_region="{aws_region}"'
        response = self.execute_sql(sql)
        return self._build_object_from_db_response(response)

    def _save_ec2_package_relation(self, aws_image_id, aws_region, package_name, package_version, package_repo):
        sql = f'insert into {ec2_package_table_name} (aws_image_id, aws_region, package_name, package_version, package_repo) values ("{aws_image_id}", "{aws_region}", "{package_name}", "{package_version}", "{package_repo}")'
        response = self.execute_sql(sql)
        return response

    def _save_ec2_package_relations_batch(self, aws_image_id, aws_region, package_list, batch_size=200, ignore_key_conflict=True):
        ignore = 'ignore' if ignore_key_conflict else ''
        sql_stmt = ''
        for idx, package in enumerate(package_list):
            relation_sql = f'insert {ignore} into {ec2_package_table_name} (aws_image_id, aws_region, package_name, package_version, package_repo) values ("{aws_image_id}", "{aws_region}", "{package["name"]}","{package["version"]}","{package["repo"]}")'
            sql_stmt = f'{relation_sql};{sql_stmt}'
            if (1+idx) % batch_size == 0:
                self.execute_sql(sql_stmt)
                sql_stmt = ''
        if len(sql_stmt) > 0:
            self.execute_sql(sql_stmt)

    #-----------------------------------------------------------------------------------------------
    # EC2 Functions
    #-----------------------------------------------------------------------------------------------
    def _build_ec2_record(self, aws_image_id, aws_region, fields):
        record = fields.copy()
        record['aws_image_id'] =  aws_image_id
        record['aws_region'] = aws_region
        return record

    def _build_ec2_insert_sql_statement(self, record):
        sql = list()
        sql.append(f'INSERT INTO {ec2_table_name} (')
        sql.append(', '.join(record.keys()))
        sql.append(') VALUES (')
        sql.append(', '.join(f'"{v}"' for v in record.values()))
        sql.append(')')
        return ''.join(sql)

    def find_ec2(self, aws_image_id, aws_region):
        sql = f'select * from {ec2_table_name} where aws_image_id="{aws_image_id}" and aws_region="{aws_region}"'
        response = self.execute_sql(sql)
        ec2s = self._build_object_from_db_response(response)
        for ec2_obj in ec2s:
            # find ec2-package relations and add packages to returned ec2 object
            ec2_package_relations = self._find_ec2_package_relations(aws_image_id, aws_region)
            ec2_obj['packages'] = [ {'package_name': package['package_name'], 'package_version': package['package_version'], 'package_repo': package['package_repo']} for package in ec2_package_relations]
        return ec2s

    def save_ec2(self, aws_image_id, aws_region, input_fields):
        # packages have their own table, so remove it to construct the ec2 record
        ec2_fields = input_fields.copy()
        ec2_fields.pop('packages')
        ec2_record = self._build_ec2_record(aws_image_id, aws_region, ec2_fields)
        sql_stmt = self._build_ec2_insert_sql_statement(ec2_record)
        response = self.execute_sql(sql_stmt)
        if 'packages' in input_fields:
            self.save_packages_batch(input_fields['packages'])
            self._save_ec2_package_relations_batch(aws_image_id, aws_region, input_fields['packages'] )

