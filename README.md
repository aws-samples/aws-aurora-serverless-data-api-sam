## Intro

CM-DB is ...

## Deploying the Solution

Make sure the AWS credentials are available in the deployment workstation (typically under ~./.aws/credentials or ~/.aws/config) and that the user has enough permissions.

Copy file `deploy_scripts/marcilio-dev-env.sh` into your own config file for the target AWS account.

```bash
# from the project root directory
cd api/deploy_scripts/
cp marcilio-dev-env.sh cmdb-dev-env.sh
```

You'll need a S3 bucket to deploy the artifacts. Enter the S3 bucket name in `cmdb-dev-env.sh` in variable `s3_bucket_deployment_artifacts`.

Now deploy the solution in your account:

`./deploy_scripts/package.sh cmdb-dev && ./deploy_scripts/deploy.sh cmdb-dev`

## APIs (Draft)


* AMI creation API (will add a 'ami-created' event record to table 'ami_events')
 
```
POST: /ami/{aws_image_id}/{aws_region}
{
    aws_account,
    image_type,  // root, child, goldenimage
    server_type,
    base_os,
    aws_root_ami_id,
    aws_root_ami_region,
    release_version,
    ansible_playbook_label,
    cm_state,
    jenkins_info,
    rpms
}
```
  
* Log a lifecycle event associated w/ an existing AMI

```
POST: /ami/{aws_image_id}/{aws_region}/event/
{
    event_type,
    event_data,
    user_agent
}
```

* get an AMI record (eg, what’s in an AMI?)

```
GET: /ami/{aws_image_id}/{aws_region}
```

* search AMIs (which AMIs have RPM rpm-1)

```
GET: /ami?rpm=rpm-1
```

* search AMIs (what’s in SI)

```
GET: /ami?cm_state=IN_SI
```

* get AMI events within an interval

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
