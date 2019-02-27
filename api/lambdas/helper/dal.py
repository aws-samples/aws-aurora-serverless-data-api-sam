import boto3
import json
import os

client = boto3.client('rds-data')

ami_table_name = os.getenv('AMI_TABLE_NAME', 'ami')
rpm_table_name = os.getenv('RPM_TABLE_NAME', 'rpm')
ami_rpm_table_name = os.getenv('AMI_RPM_TABLE_NAME', 'ami_rpm')

#-----------------------------------------------------------------------------------------------
# Data Access Layer class
#-----------------------------------------------------------------------------------------------
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
    def find_rpm(self, name, version, repo):
        sql = f'select * from {rpm_table_name} where name="{name}" and version="{version}" and repo="{repo}"'
        response = self.execute_sql(sql)
        return self._build_object_from_db_response(response)

    def insert_rpm(self, name, version, repo):
        sql = f'insert into {rpm_table_name} (name, version, repo) values ("{name}","{version}","{repo}")'
        response = self.execute_sql(sql)
        return response

    #-----------------------------------------------------------------------------------------------
    # AMI-RPM Functions
    #-----------------------------------------------------------------------------------------------
    def save_ami_to_db_rpm_relation(self, aws_image_id, aws_region, rpm_name, rpm_version, rpm_repo):
        sql = f'insert into {ami_rpm_table_name} (aws_image_id, aws_region, rpm_name, rpm_version, rpm_repo) values ("{aws_image_id}", "{aws_region}", "{rpm_name}", "{rpm_version}", "{rpm_repo}")'
        response = self.execute_sql(sql)
        return response

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

    def save_ami_to_db(self, aws_image_id, aws_region, input_fields):
        # rpms have their own table, so remove it to construct the ami record
        ami_fields = input_fields.copy()
        ami_fields.pop('rpms')
        ami_record = self._build_ami_record(aws_image_id, aws_region, ami_fields)
        sql_stmt = self._build_ami_insert_sql_statement(ami_record)
        # insert ami record in db
        response = self.execute_sql(sql_stmt)

        # we might have to add rpms if they're new...
        if 'rpms' in input_fields:
            for rpm in input_fields['rpms']:
                rpm_obj = self.find_rpm(rpm['name'], rpm['version'], rpm['repo'])
                if not rpm_obj:
                    self.insert_rpm(rpm['name'], rpm['version'], rpm['repo'])
                # also need to add an ami-rpm relationship regardless
                self.save_ami_to_db_rpm_relation(aws_image_id, aws_region, rpm['name'], rpm['version'], rpm['repo'])        

