#!/bin/bash

#======================================================================
# Deploys CM-DB solution on AWS
#======================================================================

# Sample invoke:
# ./deploy.sh dev

set -e

function error() {
    echo "Error: $1"
    exit -1
}
[[ -n "$1" ]] || error "Missing environment name (eg, dev, qa, prod)"
env_type=$1

. "./deploy_scripts/${env_type}-env.sh"

stack_name="${env_type}-${app_name}-stack"
pack_root_dir="/tmp/${app_name}"
pack_dist_dir="${pack_root_dir}/dist"

(cd $pack_dist_dir \
&& aws cloudformation deploy \
    --template-file $gen_cfn_template \
    --stack-name $stack_name \
    --parameter-overrides \
        ProjectName="$app_name" \
        EnvType="$env_type" \
        DBName="$db_name" \
        DBClusterARN="$db_cluster_arn" \
        DBCredSecretsStoresArn="$db_cred_secrets_store_arn" \
    --capabilities \
        CAPABILITY_IAM
)
