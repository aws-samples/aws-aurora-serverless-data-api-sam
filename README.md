## Intro

This project provides comprehensive sample code that shows how to build a Serverless application on AWS using [Amazon API Gateway](https://aws.amazon.com/api-gateway/), [AWS Lambda](https://aws.amazon.com/lambda/),[ Amazon Aurora Serverless](https://aws.amazon.com/rds/aurora/serverless/) (MySQL) and the new [Data API](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html). By using the Data API, our Lambda functions do not have to deal with persistent database connections. Instead, we interact with the Aurora Serverless MySQL database via an API. How cool, eh?

Check my blog post [Using the Data API to interact with an Amazon Aurora Serverless MySQL database](TODO) on the AWS Database Blog for detailed code samples exemplifying how to use the Data API for different use cases.

## Limitations

At the time of this writing (July 2019), the Data API is publicly available in US East (N. Virginia), US East (Ohio), US West (Oregon), Europe (Ireland), and Asia Pacific (Tokyo) Regions.

## Architecture

![Simple EC2 Inventory Serverless API Using Aurora Serverless and the Data API](docs/aurora-serverless-sam-architecture.png)

In this project, we build a simple Rest API to store and retrieve information about software packages installed in EC2 instances. The picture above shows the two Rest APIs (see the _POST_ and _GET_ APIs). Client applications send REST requests to an [Amazon API Gateway](https://aws.amazon.com/api-gateway/) endpoint which then routes the request to the appropriate Lambda function. The [Lambda](https://aws.amazon.com/lambda/) functions implement the core API logic and make use of database credentials stored on AWS Secrets Manager to connect to the Data API Endpoint for the [Aurora serverless](https://aws.amazon.com/rds/aurora/serverless/) MySQL cluster. By leveraging the Data API, Lambda functions do not have to manage database connections or connection pools. Instead, simple API calls are made via the Data API to issue SQL commands to the Aurora Serverless database.

By using Aurora Serverless MySQL we can take advantage of the optional auto-pause feature which allows us to automatically and seamlessly shut down and restart the database when needed without any impact to application code. This makes sense as the EC2 Inventory database will only be updated sporadically when EC2 instances are launched or terminated. In the occasional event of a large number of EC2 instances being launched simultaneously, the Aurora Serverless database will automatically scale up to meet traffic demands.

## Required software

You'll need to download and install the following software:

* [Python 3.6](https://www.python.org/downloads/)
* [Pipenv](https://pypi.org/project/pipenv/)
* [AWS CLI](https://aws.amazon.com/cli/)
* [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)

Make sure you have set up AWS credentials (typically placed under `~/.aws/credentials` or `~/.aws/config`). The credentials you're using should have "enough" privileges to provision all required services. You'll know the exact definition of "enough" when you get "permission denied" errors :)

Now, indicate which AWS profile should be used by the provided scripts, e.g,:

```bash
export AWS_PROFILE=[your-aws-profile]
```

## Python environment

Create the Python virtual environment and install the dependencies:

```bash
# from the project's root directory
pipenv --python 3.6 # creates Python 3.6 virtual environment
pipenv shell    # activate the virtual environment
pipenv install  # install dependencies
```

To know where the virtual environments and the dependencies are installed type this:

```bash
pipenv --venv
```

## Deploying the Solution

### Deploying the Database

The deployment script reads the values from config file ```config-dev-env.sh``` (__important__: This file will be used everywhere! Make sure you edit the file with config value for your AWS account!).

Create (or reuse) an S3 bucket to store Lambda packages. Your AWS credentials must give you access to put objects in that bucket.

```
# Creating an S3 bucket (if needed)
aws s3 mb s3://[your-s3-bucket-name]
```

Make sure you update file `config-dev-env.sh` with the S3 bucket name otherwise the deployment will fail.

```bash
# Specifying the S3 bucket that will store Lambda package artifacts
export s3_bucket_deployment_artifacts="[your-s3-bucket-name]"
```

Now deploy the database resources by invoking the deploy script and passing the config file as an input parameter (__important__: Notice that we only specify the prefix of the config file (eg, `config-dev`) not the full file name).

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

Upon completion, the deploy script will print the output parameters produced by the deployed API stack. Take note of the ```ApiEndpoint``` output parameter value.

## APIs

You can now use a REST API client such as [Postman](https://www.getpostman.com/downloads/) or the  ```curl``` command to invoke the EC2 Inventory API. You'll use the ```ApiEndpoint``` value you grabbed in the previous step for that (see next).

### Add EC2 info to inventory

Add a new EC2 to the inventory by specifying the EC2 instance id (```aws_instance_id```), AWS region, and AWS account as well as the packages that have been deployed to the instance (```package_name``` and ```package_version```).

#### Request

```POST: https://[EpiEndpoint]/ec2/{aws_instance_id}```

Example:

```
POST: /ec2/i-01aaae43feb712345
{
    "aws_region": "us-east-1",
    "aws_account": "123456789012",
    "packages": [
    	{"package_name": "package-1", "package_version": "v1"},
    	{"package_name": "package-1", "package_version": "v2"},
    	{"package_name": "package-2", "package_version": "v1"},
    	{"package_name": "package-3", "package_version": "v1"}
    ]
}
```

#### Responses

**Success - HttpCode: 200**

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

**Error - HttpCode: 400**

Example:

```
{
    "error_message": "An error occurred (BadRequestException) when calling the ExecuteSql operation: Duplicate entry 'instance-002' for key 'PRIMARY'"
}
```

### Get EC2 info from inventory (includes packages)

Get information about an EC2 from the inventory by specifying the EC2 instance id (```aws_instance_id```).

#### Request

```
GET: https://[EpiEndpoint]/ec2/{aws_instance_id}
```

Example:
```
GET: /ec2/i-01aaae43feb712345
```

#### Response

**Success - HttpCode=200 (AMI found)**

Example:

```
{
    "record": {
        "aws_instance_id": "i-01aaae43feb712345",
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

## Observability

We enabled observability of this application via [AWS X-Ray](https://aws.amazon.com/xray/). Take a look at the data access layer source file ([dal.py](https://github.com/aws-samples/aws-aurora-serverless-data-api-sam/blob/master/lambdas/helper/dal.py#L67)) for details. Search for terms `x-ray` and `xray`.

## Running Lambda Functions Locally

To run Lambda function ```GetEC2InfoLambda``` locally using the environment variables defined in ```local/env_variables.json``` and the event input file ```GetEC2InfoLambda-event.json``` do the following:

```
# from the project's root directory
local/run_local.sh config-dev GetEC2InfoLambda
```

Exercise: Create an event JSON file for the ```AddEC2InfoLambda``` Lambda function and invoke it locally.

## Running Integration Tests

A few integration tests are available under directory ```tests/```. The tests use the ```pytest``` framework to make API calls against our deployed API. So, before running the tests, make sure the API is actually deployed to AWS.

The API endpoint is discovered automatically from the test script based on the ```ApiEndpoint``` output parameter produced by the API CloudFormation stack.

To run the integration tests locally do this:

```bash
# from the project's root directory
./tests/run_tests.sh config-dev
```

## License Summary

This sample code is made available under a modified MIT license. See the LICENSE file for details.
