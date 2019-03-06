#!/bin/bash

#======================================================================
# Package API resources for deployment
#======================================================================

# ./deploy.sh dev

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

pack_root_dir="/tmp/${app_name}"
pack_dist_dir="${pack_root_dir}/dist"

rm -rf "$pack_root_dir"
mkdir -p $pack_dist_dir
cp -R . $pack_dist_dir/
cp -R "${virtual_env_location}/lib/python3.6/site-packages/" "${pack_dist_dir}/lambdas"

echo "Creating deployment package under '${pack_dist_dir}' and uploading it to s3://${s3_bucket_deployment_artifacts}"
(cd $pack_dist_dir \
 && aws cloudformation package \
    --template-file "./deploy_scripts/${cfn_template}" \
    --s3-bucket $s3_bucket_deployment_artifacts \
    --output-template-file $gen_cfn_template \
 && cat $gen_cfn_template)
