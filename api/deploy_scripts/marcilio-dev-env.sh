#!/bin/bash

# Environment name (eg, dev, qa, prod)
export env_type="dev"

# Python virtual environment location for packaging
if [ -z "$virtual_env_location" ]; then
    virtual_env_location=`pipenv --venv`
fi

# S3 bucket to store packaged Lambdas
export s3_bucket_deployment_artifacts="cmdb-us-east-1-665243897136"

# You probably don't need to change these values
export app_name="cmdb"
export cfn_template="cfn_template.yaml"
export gen_cfn_template="generated-${cfn_template}"
