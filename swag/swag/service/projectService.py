from decouple import config
from pymongo import MongoClient
import requests
from requests.auth import HTTPBasicAuth
# from core.model import Project

API_HOST_PROJECT = config("API_HOST_PROJECT")
API_USERNAME = config("API_USERNAME")
API_TOKEN = config("API_TOKEN")

def get_api_data():
    response = requests.get(
            f"{API_HOST_PROJECT}",
            auth=HTTPBasicAuth(API_USERNAME, API_TOKEN)
        )
    response.raise_for_status()
    return response.json()

get_api = get_api_data()

for item in get_api:
    print(item["key"])