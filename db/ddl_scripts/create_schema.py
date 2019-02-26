import boto3
import json

client = boto3.client('rds-data')
table_ddl_script_files = [
    'table_ami_ddl.txt', 
    'table_ami_events.txt', 
    'table_rpm_ddl.txt', 
    'table_ami_rpm_ddl.txt'
]

# TODO: fetch values below from CFN output
db_credentials_secrets_store_arn='arn:aws:secretsmanager:us-east-1:665243897136:secret:dev/cmdb/aurora-HlUTfC'
database_name='ess_cmdb'
db_cluster_arn='arn:aws:rds:us-east-1:665243897136:cluster:ess-cmdb'


for table_ddl_script_file in table_ddl_script_files:
    print(f"Creating table from DDL file: {table_ddl_script_file}")
    with open(table_ddl_script_file, 'r') as ddl_script:
        ddl_script_content=ddl_script.read()
        print(ddl_script_content)
        response = client.execute_sql(
            awsSecretStoreArn=db_credentials_secrets_store_arn,
            database=database_name,
            dbClusterOrInstanceArn=db_cluster_arn,
            sqlStatements=ddl_script_content
        )
        print(response)


