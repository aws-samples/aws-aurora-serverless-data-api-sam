#!/bin/bash

#======================================================================
# Creates Databse schema
#======================================================================

set -e

function error() {
    echo "Error: $1"
    exit -1
}
[[ -n "$1" ]] || error "Missing environment name (eg, dev, qa, prod)"
env_type=$1

. "../${env_type}-env.sh"

python dataapi_examples.py
