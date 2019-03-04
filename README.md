## Intro

Sample AWS solution showing how to use Amazon Aurora Serverless and the Data API as the backend of a Serverless SAM API (API Gateway + Lambda).

## Python environment

Install ```pipenv``` (https://pipenv.readthedocs.io/en/latest/)

Eg, on Mac OS:

```
brew install pipenv
```

Then create the Python virtual environment and install the dependencies:

```
cd api/
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

### Deploying the Database

1) Log on the AWS Console for the account you want to the deploy the database
2) Navigate to the Cloudformation Console
3) Create a Cloudformation stack for the DB using the template in ```db/deploy_scripts/cfn_template.yaml```
4) Take note of the output parameters (you'll need them later)

### Creating the Database entities (database and tables)

DB DDL statements are available in plain text at ```db/ddl_scripts```.

1) Log on the AWS Console
2) Open the RDS Console
3) Click on 'Query Editor' (on the left)
4) Choose the database you created and credentials
5) Once the query editor opens clear its contents
6) Copy all content from file ```db/dll_scripts/create_db_and_tables.txt``` in the query editor
7) Click 'Run'


### Deploying the API

In order to deploy CM-DB to an AWS account a configuration file needs to be edited w/ account-specific resources. A sample file is provided called C`deploy_scripts/marcilio-dev-env.sh`. That file is used to deploy the solution to Marcilio's AWS account. Copy and paste that file into another file, say `cmdb-dev-env.sh` (it might already exist, so skip this step if so).

```bash
# from the project root directory
cd api/deploy_scripts/
cp marcilio-dev-env.sh cmdb-dev-env.sh
```

Open the newly created file `cmdb-dev-env.sh` and look at some of its environment variables. 

Update the following environment variables for your AWS account:

```bash
# All resources deployed (eg, API, Lambdas) will be prefix w/ the env type (eg, dev-register-ami-lambda)
export env_type="dev"
# S3 bucket to store packaged Lambdas
export s3_bucket_deployment_artifacts="replace w/ your s3 bucket"
# RDS database name
export db_name="replace w/ the database name"
# RDS database cluster ARN
export db_cluster_arn="replace w/ the db cluster arn"
# ARN of secrets manager secret that stores the RDS user and password
export db_cred_secrets_store_arn="replace w/ the secrets store secret arn"
# ---------------------------------------------------------------
```

The ```db_cluster_arn``` and ```db_cred_secrets_store_arn``` values come from step #4 from the 'Deploying the CM-DB Database' step you did previously (see above).

Once the configuration file is updated you're ready to deploy CM-DB into your account like this:

```bash
# from the project's root directory
cd api/
./deploy_scripts/package.sh cmdb-dev && ./deploy_scripts/deploy.sh cmdb-dev
```

Notice that we only specify the prefix of the file `cmdb-dev` not the full file name.

## APIs


### Add EC2 info to inventory
 
#### Request

```
POST: /ec2/{aws_instance_id}
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
}
```

**Error - HttpCode=400**

Example:

```
}
```

### Get EC2 info from inventory (includes packages)

#### Request

```
GET: /ec2/{aws_image_id}
```

#### Response

**Success - HttpCode=200 (AMI found)**

Example:

```
{
    "record": {
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
