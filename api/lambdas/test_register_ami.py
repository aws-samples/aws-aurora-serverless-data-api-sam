import register_ami

if __name__ == "__main__":
    event={
        "resource": "/ami/{aws_image_id}/{aws_region}",
        "path": "/ami/ami-00000001/us-east-1",
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
            "aws_image_id": "test1-ami-00210008",
            "aws_region": "us-east-1"
        },
        "requestContext": {
            "resourceId": "trf23c",
            "resourcePath": "/ami/{aws_image_id}/{aws_region}",
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
        'body':'{\n "aws_account": "123456789012", \n "image_type": "root",\n "server_type": "mail server",\n "base_os": "centos 7-5.1804",\n "aws_root_ami_id": "ami-10000001",\n "aws_root_ami_region": "us-east-1", \n "release_version": "mojave",\n "ansible_playbook_label": "playbook-1",\n "cm_state": "created",\n "jenkins_info": "jenkins job 0001",\n "rpms": [\n \t{"name": "aaa-1", "version": "v1", "repo": "repo-1"},\n \t{"name": "aaa-1", "version": "v2", "repo": "repo-1"},\n \t{"name": "aaa-2", "version": "v1", "repo": "repo-1"},\n \t{"name": "aaa-3", "version": "v1", "repo": "repo-1"},\n \t{"name": "aaa-4", "version": "v1", "repo": "repo-1"},\n \t{"name": "aaa-5", "version": "v1", "repo": "repo-1"},\n \t{"name": "aaa-6", "version": "v1", "repo": "repo-1"},\n \t{"name": "aaa-7", "version": "v1", "repo": "repo-1"},\n \t{"name": "aaa-8", "version": "v1", "repo": "repo-2"}\n ]\n}'
    }
    result = register_ami.handler(event,{})
    print(f"Result: {result}")
