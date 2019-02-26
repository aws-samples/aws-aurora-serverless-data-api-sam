## Intro

CM-DB is ...

## Deploying the Solution

## APIs (Draft)


* AMI creation API (will add a 'ami-created' event record to table 'ami_events')
 
```json
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
    jenkins_info
}
```
  
* Log a lifecycle event associated w/ an existing AMI

```json
POST: /ami/{aws_image_id}/{aws_region}/event/
{
    event_type,
    event_data,
    user_agent
}
```

* get an AMI record (eg, what’s in an AMI?)

```json
GET: /ami/{aws_image_id}/{aws_region}
```

* search AMIs (which AMIs have RPM rpm-1)

```json
GET: /ami?rpm=rpm-1
```

* search AMIs (what’s in SI)

```json
GET: /ami?cm_state=IN_SI
```

* get AMI events within an interval

```json
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
