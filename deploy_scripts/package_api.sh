#!/bin/bash

#======================================================================
# Package API resources for deployment
#======================================================================

set -e

function error() {
    echo "Error: $1"
    echo "Example: ./package.sh qa"
    exit -1
}

[[ -n "$1" ]] || error "Missing environment name (eg, dev, uat, prod)"
env_type=$1

. "./deploy_scripts/${env_type}-env.sh"

if [ -z "$virtual_env_location" ]; then
    virtual_env_location=`pipenv --venv`
fi

# create or update requirements.txt
# (cd lambdas/ && pipenv lock -r)

# install dependencies from requirements.txt
sam build \
   -t deploy_scripts/${api_cfn_template} \
   -s $lambdas_dir

# package lambdas and dependencies in S3
rm -f "${sam_build_dir}/${gen_api_cfn_template}"
sam package \
   --s3-bucket $s3_bucket_deployment_artifacts \
   --output-template-file "${sam_build_dir}/${gen_api_cfn_template}"
