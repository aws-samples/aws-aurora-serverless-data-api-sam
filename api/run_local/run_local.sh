
set -e

function error() {
    echo "Error: $1"
    echo "Example: ./package.sh qa"
    exit -1
}

[[ -n "$1" ]] || error "Missing environment name (eg, dev, uat, prod)"
env_type=$1

. "../deploy_scripts/${env_type}-env.sh"

sam local invoke --template "../deploy_scripts/${cfn_template}" --event ../run_local/register_ami.json "RegisterAMILambda"
