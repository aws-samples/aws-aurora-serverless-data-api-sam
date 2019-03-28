#!/bin/bash

#======================================================================
# Packages Lambda code and dependencies and runs it locally
#======================================================================

set -e

function error() {
    echo "Error: $1"
    exit -1
}

[[ -n "$1" ]] || error "Missing environment name (eg, dev, uat, prod)"
[[ -n "$2" ]] || error "Lambda function name"
env_type=$1
lambda_function=$2

. "deploy_scripts/${env_type}-env.sh"

if [ -z "$virtual_env_location" ]; then
    virtual_env_location=`pipenv --venv`
fi

# create or update requirements.txt
# (cd lambdas/ && pipenv lock -r)

# install dependencies from requirements.txt
sam build \
   -t deploy_scripts/${api_cfn_template} \
   -s $lambdas_dir

# run locally
env_variables_file="env_variables.json"
echo "Running Lambda function locally: $lambda_function"
sam local invoke "${lambda_function}" \
    --event "local/${lambda_function}-event.json" \
    --env-vars "local/${env_variables_file}"
