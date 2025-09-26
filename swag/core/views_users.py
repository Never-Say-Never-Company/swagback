from django.http import JsonResponse
import requests
import json
from pymongo import MongoClient
from requests.auth import HTTPBasicAuth
from decouple import config
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def get_users(request):

    if request.method != 'POST':
        return JsonResponse({"error": "Método não permitido. Por favor, use POST."}, status=405)

    try:
        data = json.loads(request.body)
        jira_username = data.get("username")
        jira_api_token = data.get("token")
        
        if not jira_username or not jira_api_token:
            return JsonResponse({"error": "Por favor, forneça o 'username' e o 'token' no corpo da requisição."}, status=400)

        JIRA_URL_USERS = config("JIRA_URL", "https://necto.atlassian.net/rest/api/3/users/search")
        MONGO_URI = config("MONGO_URI", "mongodb://db:27017/")

    except json.JSONDecodeError:
        return JsonResponse({"error": "Corpo da requisição inválido. Deve ser um JSON."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Erro na configuração ou no corpo da requisição: {e}"}, status=500)

    try:
        client = MongoClient(MONGO_URI)
        db = client["swag"]
        users_collection = db["users"]
    except Exception as e:
        return JsonResponse({"error": f"Falha na conexão com o MongoDB: {e}"}, status=500)

    def get_api_data_users():
        response = requests.get(
            JIRA_URL_USERS,
            auth=HTTPBasicAuth(jira_username, jira_api_token)
        )
        response.raise_for_status()
        return response.json()

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

    try:
        users_data = get_api_data_users()
        if isinstance(users_data, list):
            cleaned_data = [clean_user_data(u) for u in users_data]
            users_collection.drop()
            users_collection.insert_many(cleaned_data)
        elif isinstance(users_data, dict):
            cleaned_data = clean_user_data(users_data)
            users_collection.drop()
            users_collection.insert_one(cleaned_data)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": f"Falha na requisição para a API do Jira: {e}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Ocorreu um erro inesperado durante o salvamento: {e}"}, status=500)

    users = list(users_collection.find({}, {"_id": 0}))
    return JsonResponse(users, safe=False)

def list_users(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Método não permitido. Use GET."}, status=405)
    
    try:
        MONGO_URI = config("MONGO_URI", "mongodb://db:27017/")
        client = MongoClient(MONGO_URI)
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
        MONGO_URI = config("MONGO_URI", "mongodb://db:27017/")
        client = MongoClient(MONGO_URI)
        db = client["swag"]

        users_collection = db["users"]
        user = users_collection.find_one({"accountId": accountId}, {"_id": 0,  "accountId": 1, "displayName": 1})

        if user:
            return JsonResponse(user, safe=False)
        else:
            return JsonResponse({"error": "Usuário não encontrado."}, status=404)
        
    except Exception as e:
        return JsonResponse({"error": f"Falha ao acessar o usuário: {e}"}, status=500)