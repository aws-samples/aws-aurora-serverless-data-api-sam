#!/bin/bash


# Python virtual environment location for packaging
if [ -z "$virtual_env_location" ]; then
    virtual_env_location=`pipenv --venv`
fi

# CHANGE THESE VALUES FOR YOUR AWS ACCOUNT  --------------------

# All resources deployed (eg, API, Lambdas) will be prefix w/ the env type (eg, dev-register-ami-lambda)

# ----- General Parameters ----- #

# Prefix to use to name provisioned resources
export env_type="dev"
# S3 bucket to store packaged Lambdas
export s3_bucket_deployment_artifacts="ec2-inventory-artifacts"

# ----- RDS Stack ----- #
# RDS database name (a-zA-Z0-9_)
export db_name="ec2_inventory_db"
# RDS Aurora Serverless Cluster Name (a-zA-Z0-9-)
export db_cluster_name="${env_type}-aurora-ec2-inventory-cluster"
# RDS Master Username
export db_master_username="db_user" # password will be create on-the-fly and associtated w/ this user
# RDS Aurora Serverless Cluster Subnets
export db_subnet_1="subnet-7659772f"
export db_subnet_2="subnet-590b1f2e"
export db_subnet_3="subnet-49550962"

# ----- API Stack ----- #
export api_stage_name="dev"
export log_level="DEBUG"  # debug/info/error

# ---------------------------------------------------------------

# You probably don't need to change these values
export app_name="ec2-inv"
export rds_cfn_template="rds_cfn_template.yaml"
export api_cfn_template="api_cfn_template.yaml"
export gen_api_cfn_template="generated-${api_cfn_template}"

export rds_stack_name="${env_type}-${app_name}-database-stack"
export api_stack_name="${env_type}-${app_name}-api-stack"