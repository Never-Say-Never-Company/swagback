import json
import re
from bson import ObjectId
import boto3
from botocore.exceptions import ClientError

def convert_objectid_to_str(obj):
    if isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj


def get_secret(secret_name, region_name="sa-east-1"):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    try:
        return json.loads(secret)
    except Exception:
     return secret
    
def convert_time_to_minutes(time_str):
    if not time_str:
        return 0
    total_minutes = 0
    
    hours_match = re.search(r'(\d+)\s*h', time_str)
    if hours_match:
        total_minutes += int(hours_match.group(1)) * 60
        
    minutes_match = re.search(r'(\d+)\s*m', time_str)
    if minutes_match:
        total_minutes += int(minutes_match.group(1))
        
    return total_minutes