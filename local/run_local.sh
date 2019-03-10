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

. "../deploy_scripts/${env_type}-env.sh"

if [ -z "$virtual_env_location" ]; then
    virtual_env_location=`pipenv --venv`
fi

lambdas_dir="../lambdas"
env_variables_file="env_variables.json"
cfn_template_dir="../deploy_scripts"
pack_root_dir="/tmp/${app_name}"
pack_dist_dir="${pack_root_dir}/run_local/"

echo "Creating local environment under ${pack_dist_dir} ..."
rm -rf "$pack_root_dir"
mkdir -p $pack_dist_dir
# Copy SAM template
cp "${cfn_template_dir}/${api_cfn_template}" $pack_dist_dir
# Copy Lambda Python code
cp "${lambdas_dir}"/*.py $pack_dist_dir
# Copy Python dependencies from virtual environment
cp -R "${virtual_env_location}/lib/python3.6/site-packages/" $pack_dist_dir
# Copy Lambda event JSON and environment variables file
cp *.json $pack_dist_dir

echo "Running Lambda function locally: $lambda_function"
(cd $pack_dist_dir &&
  cat "${api_cfn_template}" | sed 's/\(CodeUri:\)\(.*\)$/\1 \./g' > template.yaml &&
  sam local invoke "${lambda_function}" \
    --event "${lambda_function}-event.json" \
    --env-vars $env_variables_file \
    --template template.yaml
)