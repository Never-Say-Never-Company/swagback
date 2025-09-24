from django.http import  JsonResponse
from requests.auth import HTTPBasicAuth
from decouple import config
import requests
from pymongo import MongoClient
from django.conf import settings



API_URL_USERS = config("JIRA_URL_USERS")
API_USER_NAME = config("JIRA_USER_NAME")
API_TOKEN = config("JIRA_TOKEN")
MONGO_PATH = config("MONGO_PATH")

client = MongoClient(MONGO_PATH)
db = client["swag"]
users_collection = db["users"]

def get_api_data_users():
    response = requests.get(
        API_URL_USERS,
        auth=HTTPBasicAuth(API_USER_NAME, API_TOKEN)
    )
    response.raise_for_status()
    return response.json()

print(get_api_data_users())
def clean_user_data(user):
    return {
        "accountId": user.get("accountId"),
        "displayName": user.get("displayName"),
        "accountType": user.get("accountType"),
        "avatarUrls": user.get("avatarUrls", {}),  
        "active": user.get("active"),
        "timeZone": user.get("timeZone"),
        "locale": user.get("locale")
    }

def save_users():
    users_data = get_api_data_users() 

    if isinstance(users_data, list):
        cleaned_data = [clean_user_data(u) for u in users_data]
        users_collection.drop()  
        users_collection.insert_many(cleaned_data)  
    elif isinstance(users_data, dict):
        cleaned_data = clean_user_data(users_data)
        users_collection.drop()
        users_collection.insert_one(cleaned_data)
        
save_users()


#def get_users(request):
    # Pega todos os documentos da collection
 #   users = list(users_collection.find({}, {"_id": 0}))  # _id = 0 para não retornar o campo _id

  #  return JsonResponse(users, safe=False)


def get_users(request):
    return JsonResponse({"ok": True})

