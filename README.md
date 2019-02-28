## Intro

CM-DB is a solution built by Symantec and AWS that will allow Symantec to continuously track an AMI's lifecycle and gain insights on the AMI CI/CD workflow for ESS. The solution comprises of injection points added to ESS's AMI CI/CD workflow and a back-end REST API (API Gateway+Lambda+Aurora) that will be called by those injection points to store AMI-lifecycle-related events. The API can also be used for querying purposes.

## Python environment

Install ```pipenv``` (https://pipenv.readthedocs.io/en/latest/)

Eg, on Mac OS:

```
brew install pipenv
```

Then create the Python virtual environment and install the dependencies:

```
cd api/lambdas
pipenv --python 3.6
pipenv shell
pipenv install (this will read the Pipfile file to locate and install dependencies)
```

To know where the virtual environments and the dependencies are installed type this:

```
pipenv --venv
```

## Deploying the Solution

First things first. Make sure you have properly set up AWS credentials in the workstation that will trigger the deployment of CM-DB on AWS. Credentials are typically placed under `~/.aws/credentials` or `~/.aws/config`. The credentials you're using should have "enough" privileges to provision all required services.

In order to deploy CM-DB to an AWS account a configuration file needs to be edited w/ account-specific resources. A sample file is provided called C`deploy_scripts/marcilio-dev-env.sh`. That file is used to deploy the solution to Marcilio's AWS account. Copy and paste that file into another file, say `cmdb-dev-env.sh` (it might already exist, so skip this step if so).

```bash
# from the project root directory
cd api/deploy_scripts/
cp marcilio-dev-env.sh cmdb-dev-env.sh
```

Open the newly created file `cmdb-dev-env.sh` and look at some of its environment variables. Notice that there's a reference to a S3 bucket through variable ``s3_bucket_deployment_artifacts`` that will store deployment artifacts. Enter a valid S3 bucket for the account you're deploying the solution to. The `env_type` variable will be used to prefix every resource deployed in the cloud. For instance, if `env_type=john` every resouce will be prefixed by `john`, eg, john-lambda-function-X. `env_type` typically represents a deployment environment such as `dev`, `qa`, or `prod` but it can also hold arbitrary values.

Once the configuration file is updated you're ready to deploy CM-DB into your account like this:

`./deploy_scripts/package.sh cmdb-dev && ./deploy_scripts/deploy.sh cmdb-dev`

Notice that we only specify the prefix of the file `cmdb-dev` not the full file name.

## APIs (Draft)


### Register new AMI on CM-DB (Done)
 
#### Request

```
POST: /ami/{aws_image_id}/{aws_region}
{
    "aws_account": "123456789012", 
    "image_type": "root",
    "server_type": "mail server",
    "base_os": "centos 7-5.1804",
    "aws_root_ami_id": "ami-10000001",
    "aws_root_ami_region": "us-east-1",     
    "release_version": "mojave",
    "ansible_playbook_label": "playbook-1",
    "cm_state": "created",
    "jenkins_info": "jenkins job 0001",
    "rpms": [
    	{"name": "rpm-4", "version": "v1", "repo": "repo-3"},
    	{"name": "rpm-4", "version": "v2", "repo": "repo-3"},
    	{"name": "rpm-5", "version": "v1", "repo": "repo-3"},
    	{"name": "rpm-6", "version": "v1", "repo": "repo-4"}
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
        "image_type": "root",
        "server_type": "mail server",
        "base_os": "centos 7-5.1804",
        "aws_root_ami_id": "ami-10000001",
        "aws_root_ami_region": "us-east-1",
        "release_version": "mojave",
        "ansible_playbook_label": "playbook-1",
        "cm_state": "created",
        "jenkins_info": "jenkins job 0001",
        "rpms": [
            {
                "name": "rpm-4",
                "version": "v1",
                "repo": "repo-3"
            },
            {
                "name": "rpm-4",
                "version": "v2",
                "repo": "repo-3"
            },
            {
                "name": "rpm-5",
                "version": "v1",
                "repo": "repo-3"
            },
            {
                "name": "rpm-6",
                "version": "v1",
                "repo": "repo-4"
            }
        ]
    }
}
```

**Error - HttpCode=400**

Example:

```
{
    "error_message": "An error occurred (BadRequestException) when calling the ExecuteSql operation: Duplicate entry 'ami-00011200-us-east-1' for key 'PRIMARY'"
}
```

### Get an AMI record (Done)

#### Request (What's in an AMI?)

```
GET: /ami/{aws_image_id}/{aws_region}
```

#### Response

**Success - HttpCode=200 (AMI found)**

Example:

```
{
    "record": {
        "aws_image_id": "ami-00011300",
        "aws_region": "us-east-1",
        "aws_account": "123456789012",
        "image_type": "root",
        "server_type": "mail server",
        "base_os": "centos 7-5.1804",
        "aws_root_ami_id": "ami-10000001",
        "aws_root_ami_region": "us-east-1",
        "release_version": "mojave",
        "ansible_playbook_label": "playbook-1",
        "cm_state": "created",
        "jenkins_info": "jenkins job 0001",
        "creation_date_utc": "2019-02-27 16:52:46.0",
        "rpms": [
            {
                "name": "rpm-4",
                "version": "v1",
                "repo": "repo-3",
                "creation_date_utc": "2019-02-27 14:44:47.0"
            },
            {
                "name": "rpm-4",
                "version": "v2",
                "repo": "repo-3",
                "creation_date_utc": "2019-02-27 14:47:08.0"
            },
            {
                "name": "rpm-5",
                "version": "v1",
                "repo": "repo-3",
                "creation_date_utc": "2019-02-27 14:47:09.0"
            },
            {
                "name": "rpm-6",
                "version": "v1",
                "repo": "repo-4",
                "creation_date_utc": "2019-02-27 14:47:09.0"
            }
        ]
    },
    "record_found": true
}
```

**Success - HttpCode=200 (AMI not found)**

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

### Log a lifecycle event associated w/ an existing AMI

#### Request

```
POST: /ami/{aws_image_id}/{aws_region}/event/
{
    event_type,
    event_data,
    user_agent
}
```

### Search AMIs base on specific values

#### Request

```
GET: /ami?rpm=rpm-1
GET: /ami?cm_state=IN_SI
```

### Get AMI events within an interval

```
GET: /ami/{ami-id-region}/event?start=YYYYMMDDHmmmSS&end=YYYYMMDDHmmmSS
```

## How to create a new API

Let's say we need to create a new API to search all AMIs that reference a given RPM (name/version/repo).

First, we define now we want the API to look like, eg:

```GET /ami?rpm_name='rpm-1'&rpm_version='v1'&rpm_repo='repo-1'```

Notice that the API is generic, ie, it can search arbitrary fields on AMIs and hence can be used for other use cases.

Then we add the infrastructure as code piece to create the API resources on AWS via CloudFormation. 

```
cd api/deploy_scripts/
vi cfn_template.yaml
```

We add a new Lambda function in the CloudFormation template for our API. Let's calls the Lambda function ```SearchAMIsLambda```. This Lambda 

```
  SearchAMIsLambda:
    Type: 'AWS::Serverless::Function'
    Properties:
      Description: Search AMIs on CM-DB
      FunctionName: !Sub "${EnvType}-${AppName}-search-ami-lambda"
      Handler: search_ami.handler
      CodeUri: ../lambdas/
      Events:
        AMIPost:
          Type: Api
          Properties:
            Path: '/ami'
            Method: get
      Policies:
        - Version: '2012-10-17' # Policy Document
          Statement:
            - Effect: Allow
              Action:
                - rds-data:ExecuteSql
                - secretsmanager:GetSecretValue
              Resource: '*'
```

Now we're able to deploy a new API on AWS but the Lambda code is not there yet. If you noticed, the new Lambda we just added to the Cloudformation template ```SearchAMIsLambda``` refers to a Python source code file named ```search_ami```. We need to create that file (```search_ami.py```) and add an entrypoint function called ```handler``` to it. We can likely copy/paste an existing Lambda code to make things easier.

New Lambda source code file: ```api/lambdas/search_ami.py```

```
#-----------------------------------------------------------------------------------------------
# Lambda Entrypoint
#-----------------------------------------------------------------------------------------------
def handler(event, context):
    print(f'Event received: {event}')
    try:

        # TODO: Validate input parameters

        # TODO: call dal object (DataAccessLayer) to search AMIs

        # TODO: generate output

        return success(output)
    except Exception as e:
        print(f'Error: {e}')
        return error(400, str(e)) 
```

You can create a test file to test your Lambda function locally. Take a look at test files for other Lambda functions (```test_find_ami.py``` and ```test_register_ami.py```).

## TODO
- API (POST: ami/): support RPMs as input
- API (GET: ami/): return AMI and RPMs
- API: allow updating the AMI state
- Pass db_credentials_secrets_store_arn, database_name, and db_cluster_arn to Lambda functions
- IaC: Cloudformation (YAML) for Aurora DB/Secrets Manager
- IaC: Cloudformation (YAML) for API/Lambda
- IaC: Automate: DB credentials in Secrets Manager
