from django.http import JsonResponse
import requests
import json
from pymongo import MongoClient
from requests.auth import HTTPBasicAuth
from decouple import config
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def get_users(request):
    """
    Esta view recebe uma requisição POST com dados de autenticação no corpo,
    faz a requisição para a API do Jira, salva os dados no MongoDB,
    e retorna a lista de usuários como uma resposta JSON.
    """
    
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