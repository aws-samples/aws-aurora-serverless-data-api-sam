import json

def key_missing_or_empty_value(d, key):
    return not key in d or not d[key]

def success(output):
    return {
        'statusCode': 200,
        'body': json.dumps(output)
}

def error(error_code, error):
    return {
        'statusCode': error_code,
        'body': json.dumps({
            'error_message': error
        })
    }
