'''
 * Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import os
import requests
import boto3
import pytest
import uuid
from http import HTTPStatus

def get_cfn_output(key, outputs):
    result = [ v['OutputValue'] for v in outputs if v['OutputKey'] == key ]
    return result[0] if len(result) > 0 else ''

@pytest.fixture(scope="module")
def api_endpoint():
    cloudformation = boto3.resource('cloudformation')
    api_stack_name = os.getenv('api_stack_name')
    stack = cloudformation.Stack(api_stack_name)
    return get_cfn_output('ApiEndpoint', stack.outputs)

@pytest.fixture()
def ec2_input_data():
    return {
        'instance_id': uuid.uuid4(),
        'input_data': {
            "aws_region": "us-east-1",
            "aws_account": "123456789012",
            "packages": [
                {"package_name": "package-1", "package_version": "v1"},
                {"package_name": "package-1", "package_version": "v2"},
                {"package_name": "package-2", "package_version": "v1"}
            ]
        }
    }

# TODO: add_ec2* tests have side effects (create DB record for test but does not delete it)
# TODO: Warm up Aurora Serverless with an initial request + sleep

def test_add_ec2_info_returns_expected_attributes(api_endpoint, ec2_input_data):
    r = requests.post(f'{api_endpoint}/ec2/{ec2_input_data["instance_id"]}', json = ec2_input_data['input_data'])
    assert  HTTPStatus.OK == r.status_code
    response = r.json()
    assert 'new_record' in response
    assert ec2_input_data['input_data']['aws_region'] == response['new_record']['aws_region']
    assert ec2_input_data['input_data']['aws_account'] == response['new_record']['aws_account']
    assert ec2_input_data['input_data']['packages'] == response['new_record']['packages']

def test_add_ec2_info_error_duplicate(api_endpoint, ec2_input_data):
    r = requests.post(f'{api_endpoint}/ec2/{ec2_input_data["instance_id"]}', json = ec2_input_data['input_data'])
    assert  HTTPStatus.OK == r.status_code

    r = requests.post(f'{api_endpoint}/ec2/{ec2_input_data["instance_id"]}', json = ec2_input_data['input_data'])
    response = r.json()
    assert  HTTPStatus. BAD_REQUEST == r.status_code

def test_add_ec2_info_invalid_input_field(api_endpoint):
    r = requests.post(f'{api_endpoint}/ec2/{uuid.uuid4()}', json = {'invalid_field_name': 'any-value'})
    assert  HTTPStatus. BAD_REQUEST == r.status_code

def test_get_ec2_info_record_found(api_endpoint, ec2_input_data):
    r = requests.post(f'{api_endpoint}/ec2/{ec2_input_data["instance_id"]}', json = ec2_input_data['input_data'])
    assert  HTTPStatus.OK == r.status_code

    r = requests.get(f'{api_endpoint}/ec2/{ec2_input_data["instance_id"]}')
    assert r.status_code ==  HTTPStatus.OK
    response = r.json()
    assert True == response['record_found']

def test_get_ec2_info_record_not_found(api_endpoint):
    instance_id = uuid.uuid4()
    r = requests.get(f'{api_endpoint}/ec2/{instance_id}')
    assert r.status_code ==  HTTPStatus.OK
    response = r.json()
    assert False == response['record_found']
