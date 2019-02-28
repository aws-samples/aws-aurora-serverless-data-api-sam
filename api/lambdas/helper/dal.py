#-----------------------------------------------------------------------------------------------
# Data Access Layer
# - Contains a data access layer class that interfaces with CM-DB to store and query entities
#   such as AMIs, AMI events, and RPMs
#-----------------------------------------------------------------------------------------------

import boto3
import json
import os

client = boto3.client('rds-data')

ami_table_name = os.getenv('AMI_TABLE_NAME', 'ami')
rpm_table_name = os.getenv('RPM_TABLE_NAME', 'rpm')
ami_rpm_table_name = os.getenv('AMI_RPM_TABLE_NAME', 'ami_rpm')

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
    # RPM Functions
    #-----------------------------------------------------------------------------------------------
    def find_rpm(self, name, version, repo):
        sql = f'select * from {rpm_table_name} where name="{name}" and version="{version}" and repo="{repo}"'
        response = self.execute_sql(sql)
        return self._build_object_from_db_response(response)

    def save_rpm(self, name, version, repo, ignore_key_conflict=True):
        ignore = 'ignore' if ignore_key_conflict else ''
        sql = f'insert {ignore} into {rpm_table_name} (name, version, repo) values ("{name}","{version}","{repo}")'
        response = self.execute_sql(sql)
        return response

    def save_rpms_batch(self, rpm_list, batch_size=200, ignore_key_conflict=True):
        ignore = 'ignore' if ignore_key_conflict else ''
        sql_stmt = ''
        for idx, rpm in enumerate(rpm_list):
            rpm_sql = f'insert {ignore} into {rpm_table_name} (name, version, repo) values ("{rpm["name"]}","{rpm["version"]}","{rpm["repo"]}")'
            sql_stmt = f'{rpm_sql};{sql_stmt}'
            if (1+idx) % batch_size == 0:
                self.execute_sql(sql_stmt)
                sql_stmt = ''
        if len(sql_stmt) > 0:
            self.execute_sql(sql_stmt)

    #-----------------------------------------------------------------------------------------------
    # AMI-RPM Functions
    #-----------------------------------------------------------------------------------------------
    def _find_ami_rpm_relations(self, aws_image_id, aws_region):
        sql = f'select * from {ami_rpm_table_name} where aws_image_id="{aws_image_id}" and aws_region="{aws_region}"'
        response = self.execute_sql(sql)
        return self._build_object_from_db_response(response)

    def _save_ami_rpm_relation(self, aws_image_id, aws_region, rpm_name, rpm_version, rpm_repo):
        sql = f'insert into {ami_rpm_table_name} (aws_image_id, aws_region, rpm_name, rpm_version, rpm_repo) values ("{aws_image_id}", "{aws_region}", "{rpm_name}", "{rpm_version}", "{rpm_repo}")'
        response = self.execute_sql(sql)
        return response

    def _save_ami_rpm_relations_batch(self, aws_image_id, aws_region, rpm_list, batch_size=200, ignore_key_conflict=True):
        ignore = 'ignore' if ignore_key_conflict else ''
        sql_stmt = ''
        for idx, rpm in enumerate(rpm_list):
            relation_sql = f'insert {ignore} into {ami_rpm_table_name} (aws_image_id, aws_region, rpm_name, rpm_version, rpm_repo) values ("{aws_image_id}", "{aws_region}", "{rpm["name"]}","{rpm["version"]}","{rpm["repo"]}")'
            sql_stmt = f'{relation_sql};{sql_stmt}'
            if (1+idx) % batch_size == 0:
                self.execute_sql(sql_stmt)
                sql_stmt = ''
        if len(sql_stmt) > 0:
            self.execute_sql(sql_stmt)

    #-----------------------------------------------------------------------------------------------
    # AMI Functions
    #-----------------------------------------------------------------------------------------------
    def _build_ami_record(self, aws_image_id, aws_region, fields):
        record = fields.copy()
        record['aws_image_id'] =  aws_image_id
        record['aws_region'] = aws_region
        return record

    def _build_ami_insert_sql_statement(self, record):
        sql = list()
        sql.append(f'INSERT INTO {ami_table_name} (')
        sql.append(', '.join(record.keys()))
        sql.append(') VALUES (')
        sql.append(', '.join(f'"{v}"' for v in record.values()))
        sql.append(')')
        return ''.join(sql)

    def find_ami(self, aws_image_id, aws_region):
        sql = f'select * from {ami_table_name} where aws_image_id="{aws_image_id}" and aws_region="{aws_region}"'
        response = self.execute_sql(sql)
        amis = self._build_object_from_db_response(response)
        for ami_obj in amis:
            # find ami-rpm relations and add rpms to returned ami object
            ami_rpm_relations = self._find_ami_rpm_relations(aws_image_id, aws_region)
            ami_obj['rpms'] = [ {'rpm_name': rpm['rpm_name'], 'rpm_version': rpm['rpm_version'], 'rpm_repo': rpm['rpm_repo']} for rpm in ami_rpm_relations]
        return amis

    def save_ami(self, aws_image_id, aws_region, input_fields):
        # rpms have their own table, so remove it to construct the ami record
        ami_fields = input_fields.copy()
        ami_fields.pop('rpms')
        ami_record = self._build_ami_record(aws_image_id, aws_region, ami_fields)
        sql_stmt = self._build_ami_insert_sql_statement(ami_record)
        response = self.execute_sql(sql_stmt)
        if 'rpms' in input_fields:
            self.save_rpms_batch(input_fields['rpms'])
            self._save_ami_rpm_relations_batch(aws_image_id, aws_region, input_fields['rpms'] )

