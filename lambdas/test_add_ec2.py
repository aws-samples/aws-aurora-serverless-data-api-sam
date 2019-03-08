import boto3
import os

rds_stack_name = os.getenv('rds_stack_name', 'dev-ec2-inv-database-stack')

def get_cfn_output(key, outputs):
    result = [ v['OutputValue'] for v in outputs if v['OutputKey'] == key ]
    return result[0] if len(result) > 0 else ''

cloudformation = boto3.resource('cloudformation')
stack = cloudformation.Stack(rds_stack_name)

x=get_cfn_output('DatabaseName', stack.outputs)
os.environ["DB_NAME"] = get_cfn_output('DatabaseName', stack.outputs)
os.environ["DB_CLUSTER_ARN"] =  get_cfn_output('DatabaseClusterArn', stack.outputs)
os.environ["DB_CRED_SECRETS_STORE_ARN"] = get_cfn_output('DatabaseSecretArn', stack.outputs)

import add_ec2_info
if __name__ == "__main__":
    event={
        "resource": "/ami/{aws_instance_id}",
        "path": "/ami/i-0000000001",
        "httpMethod": "POST",
        "headers": {
            "Accept": "*/*",
            "accept-encoding": "gzip, deflate",
            "cache-control": "no-cache",
            "Content-Type": "application/json",
            "Host": "9ru2poro88.execute-api.us-east-1.amazonaws.com",
            "Postman-Token": "4b9e5218-978d-42ea-9b18-ba4568f62df0",
            "User-Agent": "PostmanRuntime/7.3.0",
            "X-Amzn-Trace-Id": "Root=1-5c747f89-9713cbc075d265403910db80",
            "X-Forwarded-For": "72.21.196.65",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https"
        },
        "pathParameters": {
            "aws_instance_id": "i-0000000001",
        },
        "requestContext": {
            "resourceId": "trf23c",
            "resourcePath": "/ami/i-0000000001",
            "httpMethod": "POST",
            "extendedRequestId": "VrjdiHUmoAMF41Q=",
            "requestTime": "25/Feb/2019:23:51:37 +0000",
            "path": "/Prod/ami/ami-00000001/us-east-1",
            "accountId": "665243897136",
            "protocol": "HTTP/1.1",
            "stage": "Prod",
            "domainPrefix": "9ru2poro88",
            "requestTimeEpoch": 1551138697815,
            "requestId": "4a4fa73d-3958-11e9-93b4-d1d6bd8c8dc1",
            "domainName": "9ru2poro88.execute-api.us-east-1.amazonaws.com",
            "apiId": "9ru2poro88"
        },
        'body':'{"aws_account": "123456789012", "aws_region": "us-east-1", "packages": [{"package_name": "package-1", "package_version": "v1"}, {"package_name": "package-2", "package_version": "v2"}]}'
    }
    result = add_ec2_info.handler(event,{})
    print(f"Result: {result}")
