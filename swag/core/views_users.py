from django.http import JsonResponse
import requests
import json
from pymongo import MongoClient
from requests.auth import HTTPBasicAuth
from decouple import config
from django.views.decorators.csrf import csrf_exempt

JIRA_URL_USERS = config("JIRA_URL_USERS")
MONGO_PATH = config("MONGO_PATH")
client = MongoClient(MONGO_PATH)
db = client["swag"]
users_collection = db["users"]

def get_api_data_users(user_name, token):
        response = requests.get(
            f"{JIRA_URL_USERS}",
            auth=HTTPBasicAuth(user_name, token)
        )
        response.raise_for_status()
        return response.json()

@csrf_exempt
def get_users(request):
    if request.method != 'POST':
        return JsonResponse(
            {"error": "Método não permitido. Por favor, use POST."}, 
            status=405
        )

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    user_name = data.get("user_name")
    token = data.get("token")

    if not user_name or not token:
        return JsonResponse(
            {"error": "Campos 'user_name' e 'token' são obrigatórios."}, 
            status=400
        )

    try:
        users_data = get_api_data_users(user_name, token)

        users_collection.delete_many({})

        if users_data:
            users_collection.insert_many(users_data)

        return JsonResponse(
            {"message": "Usuários salvos com sucesso!"}, status=200
        )

    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": f"Erro ao acessar API Jira: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Ocorreu um erro inesperado: {str(e)}"}, status=500)


def list_users(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Método não permitido. Use GET."}, status=405)
    
    try:
        client = MongoClient(MONGO_PATH)
        db = client["swag"]

        filters = {}

        account_id = request.GET.get('accountId')
        if account_id:
            filters['accountId'] = account_id

        display_name = request.GET.get('displayName')
        if display_name:
            filters['displayName'] = {'$regex': display_name, '$options': 'i'}


        users_collection = db["users"]
        users = list(users_collection.find(filters, {"_id": 0, "accountId": 1, "displayName": 1}))
        
        return JsonResponse(users, safe=False)
    
    except Exception as e:
        return JsonResponse({"error": f"Falha ao acessar os usuários: {e}"}, status=500)

def list_user_by_Id(request, accountId):
    if request.method != 'GET':
        return JsonResponse({"error": "Método não permitido. Use GET."}, status=405)
    
    try:
        client = MongoClient(MONGO_PATH)
        db = client["swag"]

        users_collection = db["users"]
        user = users_collection.find_one({"accountId": accountId}, {"_id": 0,  "accountId": 1, "displayName": 1})

        if user:
            return JsonResponse(user, safe=False)
        else:
            return JsonResponse({"error": "Usuário não encontrado."}, status=404)
        
    except Exception as e:
        return JsonResponse({"error": f"Falha ao acessar o usuário: {e}"}, status=500)