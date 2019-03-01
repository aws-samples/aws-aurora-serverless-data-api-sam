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
export s3_bucket_deployment_artifacts=""
# RDS database name
export db_name=""
# RDS database cluster ARN
export db_cluster_arn=""
# ARN of secrets manager secret that stores the RDS user and password
export db_cred_secrets_store_arn=""
# ---------------------------------------------------------------

# You probably don't need to change these values
export app_name="cmdb"
export cfn_template="cfn_template.yaml"
export gen_cfn_template="generated-${cfn_template}"
