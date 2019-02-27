## Intro

CM-DB is a solution built by Symantec and AWS that will allow Symantec to continuously track an AMI's lifecycle and gain insights on the AMI CI/CD workflow for ESS. The solution comprises of injection points added to ESS's AMI CI/CD workflow and a back-end REST API (API Gateway+Lambda+Aurora) that will be called by those injection points to store AMI-lifecycle-related events. The API can also be used for querying purposes.

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


### AMI creation API (will add a 'ami-created' event record to table 'ami_events')
 
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

* Success - HttpCode=200 

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
}```

* Success - HttpCode=400

Example:

```
{
    "error_message": "An error occurred (BadRequestException) when calling the ExecuteSql operation: Duplicate entry 'ami-00011200-us-east-1' for key 'PRIMARY'"
}
  
### Log a lifecycle event associated w/ an existing AMI

```
POST: /ami/{aws_image_id}/{aws_region}/event/
{
    event_type,
    event_data,
    user_agent
}
```

### get an AMI record (eg, what’s in an AMI?)

```
GET: /ami/{aws_image_id}/{aws_region}
```

### search AMIs (which AMIs have RPM rpm-1)

```
GET: /ami?rpm=rpm-1
```

### search AMIs (what’s in SI)

```
GET: /ami?cm_state=IN_SI
```

### get AMI events within an interval

```
GET: /ami/{ami-id-region}/event?start=YYYYMMDDHmmmSS&end=YYYYMMDDHmmmSS
```

## Injection Points (examples)

TODO

## TODO
- API (POST: ami/): support RPMs as input
- API (GET: ami/): return AMI and RPMs
- API: allow updating the AMI state
- Pass db_credentials_secrets_store_arn, database_name, and db_cluster_arn to Lambda functions
- IaC: Cloudformation (YAML) for Aurora DB/Secrets Manager
- IaC: Cloudformation (YAML) for API/Lambda
- IaC: Automate: DB credentials in Secrets Manager
