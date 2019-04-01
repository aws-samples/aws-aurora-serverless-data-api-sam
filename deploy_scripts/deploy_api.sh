#!/bin/bash

#======================================================================
# Deploys API resources on AWS
#======================================================================

set -e

function error() {
    echo "Error: $1"
    exit -1
}
[[ -n "$1" ]] || error "Missing environment name (eg, dev, qa, prod)"
env_type=$1

. "./deploy_scripts/${env_type}-env.sh"

sam deploy \
    --template-file "${sam_build_dir}/${gen_api_cfn_template}" \
    --stack-name $api_stack_name \
    --parameter-overrides \
        ProjectName="$app_name" \
        EnvType="$env_type" \
        DatabaseStackName="${rds_stack_name}" \
        ApiStageName="${api_stage_name}" \
        LambdaLogLevel="${log_level}" \
    --capabilities \
        CAPABILITY_IAM

# Print the Stack Output
sleep 5 && aws cloudformation describe-stacks --stack-name $api_stack_name --query 'Stacks[0].Outputs'