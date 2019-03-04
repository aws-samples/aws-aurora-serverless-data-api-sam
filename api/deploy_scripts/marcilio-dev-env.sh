#!/bin/bash


# Python virtual environment location for packaging
if [ -z "$virtual_env_location" ]; then
    virtual_env_location=`pipenv --venv`
fi

# CHANGE THESE VALUES FOR YOUR AWS ACCOUNT  --------------------
# Defined an environment name (eg, dev, qa, prod)
# All resources deployed (eg, API, Lambdas) will be prefix w/ the env type (eg, dev-register-ami-lambda)
export env_type="dev"
# S3 bucket to store packaged Lambdas
export s3_bucket_deployment_artifacts="cmdb-us-east-1-665243897136"
# RDS Cloudformation stack name
export db_cfn_stack_name=""
# RDS database name (a-zA-Z0-9_)
export db_name="ess_cmdb"
# RDS database cluster ARN
export db_cluster_arn="arn:aws:rds:us-east-1:665243897136:cluster:${db_name}"
# ARN of secrets manager secret that stores the RDS user and password
export db_cred_secrets_store_arn="arn:aws:secretsmanager:us-east-1:665243897136:secret:dev/cmdb/aurora-HlUTfC"
# ---------------------------------------------------------------

# You probably don't need to change these values
export app_name="cmdb"
export cfn_template="cfn_template.yaml"
export gen_cfn_template="generated-${cfn_template}"
