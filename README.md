## Intro

Sample AWS solution showing how to use Amazon Aurora Serverless and the Data API as the backend of a Serverless SAM API (API Gateway + Lambda).

## Required software

* [AWS CLI](https://aws.amazon.com/cli/)
* [Python 3.6](https://www.python.org/downloads/)
* [Pipenv](https://pypi.org/project/pipenv/)

Make sure you have set up AWS credentials (typically placed under `~/.aws/credentials` or `~/.aws/config`). The credentials you're using should have "enough" privileges to provision all required services. You'll know the exact definition of "enough" when you get "permission denied" errors :)


## Python environment

Create the Python virtual environment and install the dependencies:

```
# from the project's root directory
pipenv --python 3.6
pipenv shell # enter the virtual environment
pipenv install (this will use the provided Pipfile to install dependencies)
```

To know where the virtual environments and the dependencies are installed type this:

```
pipenv --venv
```

## Deploying the Solution

### Deploying the Database

This uses the values from config file ```config-dev-env.sh```. 
__Important__: This file will be used everywhere! Make sure you edit the file with config value for your AWS account!

Now deploy the database resources like this (__important__: Notice that we only specify the prefix of the config file `config-dev` not the full file name).
)

```bash
# from project's root directory
./deploy_scripts/deploy_rds.sh config-dev
```

### Creating the Database entities (database and tables)

```bash
# from project's root directory
cd deploy_scripts/ddl_scripts
# run the script
./create_schema.sh config-dev
```

### Deploying the API

```bash
# from the project's root directory
./deploy_scripts/package_api.sh config-dev && ./deploy_scripts/deploy_api.sh config-dev
```

Notice that we only specify the prefix of the file `cmdb-dev` not the full file name.

## APIs

You can use [Postman](https://www.getpostman.com/downloads/) or ```curl``` to test the APIs.

Use the AWS Console to find out the API Endpoint for the stage named by variable ```api_stage_name``` in the ```config-dev-env.sh``` file.

### Add EC2 info to inventory
 
#### Request

POST: https://[Api-EndPoint]/ec2/{aws_instance_id}

Example:
```
POST: /ec2/instance-002
{
    "aws_region": "123456789012", 
    "aws_account": "123456789012",
    "packages": [
    	{"name": "package-1", "version": "v1"},
    	{"name": "package-1", "version": "v2"},
    	{"name": "package-2", "version": "v1"},
    	{"name": "package-3", "version": "v1"}
    ]
}
```

#### Response

**Success - HttpCode=200**

Example:

```
{
    "new_record": {
        "aws_account": "123456789012",
        "aws_region": "us-east-1",
        "packages": [
            {
                "package_name": "package-1",
                "package_version": "v1"
            },
            {
                "package_name": "package-1",
                "package_version": "v2"
            },
            {
                "package_name": "package-2",
                "package_version": "v1"
            }
        ]
    }
}
```

**Error - HttpCode=400**

Example:

```
{
    "error_message": "An error occurred (BadRequestException) when calling the ExecuteSql operation: Duplicate entry 'instance-002' for key 'PRIMARY'"
}
```

### Get EC2 info from inventory (includes packages)

#### Request

```
GET: https://[Api-EndPoint]/ec2/{aws_knstance_id}
```

Example:
```
GET: /ec2/instance-002
```

#### Response

**Success - HttpCode=200 (AMI found)**

Example:

```
{
    "record": {
        "aws_instance_id": "instance-002",
        "aws_region": "us-east-1",
        "aws_account": "123456789012",
        "creation_date_utc": "2019-03-06 02:45:32.0",
        "packages": [
            {
                "package_name": "package-2",
                "package_version": "v1"
            },
            {
                "package_name": "package-1",
                "package_version": "v2"
            },
            {
                "package_name": "package-1",
                "package_version": "v1"
            }
        ]
    },
    "record_found": true
}
```

**Success - HttpCode=200 (EC2 not found)**

{
    "record": {},
    "record_found": false
}

**Error - HttpCode=400**

Example:

```
{
    "error_message": "Some error message"
}
```
