#!/bin/bash

#======================================================================
# Deploys RDS Aurora Serverless and related resources
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

aws cloudformation create-stack \
    --template-body "file://deploy_scripts/${rds_cfn_template}" \
    --stack-name $rds_stack_name \
    --parameters \
        ParameterKey="AppName",ParameterValue="$app_name" \
        ParameterKey="EnvType",ParameterValue="$env_type" \
        ParameterKey="DBClusterName",ParameterValue="$db_cluster_name" \
        ParameterKey="DatabaseName",ParameterValue="$db_name" \
        ParameterKey="DBMasterUserName",ParameterValue="$db_master_username" \
        ParameterKey="DBSubnetList",ParameterValue="\"${db_subnet_1},${db_subnet_2},${db_subnet_3}\"" \
    --capabilities \
        CAPABILITY_IAM

# TODO: wait stack creation/update completion
sleep 180

# Enable the Data API
aws rds modify-db-cluster --db-cluster-identifier $db_cluster_name --enable-http-endpoint

# TODO: we could trigger the schema creation under ddl_scripts/create_schema.py from here