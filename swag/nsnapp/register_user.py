from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password # <-- Importação chave
from decouple import config
from pymongo import MongoClient
import json

# Suas variáveis de ambiente (reutilizadas)
MONGO_PATH = config("MONGO_PATH")

# Conexão com MongoDB (reutilize a que você já tem ou adapte)
def get_users_collection():
    client = MongoClient(MONGO_PATH)
    db = client["swag"]
    return db["users_api"] # <-- RECOMENDAÇÃO: Crie uma coleção separada para credenciais de LOGIN (ex: 'users_api')

@csrf_exempt
def register_user(request):
    """
    Cadastra um novo usuário no MongoDB com a senha criptografada.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido."}, status=405)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        # Você pode adicionar outros campos, como 'email' ou 'display_name'
        
        if not username or not password:
            return JsonResponse({"error": "Usuário e senha são obrigatórios."}, status=400)

        users_collection = get_users_collection()
        
        # 1. Verifica se o usuário já existe
        if users_collection.find_one({"username": username}):
            return JsonResponse({"error": "Este nome de usuário já está em uso."}, status=409)

        # 2. Criptografa a senha antes de salvar
        hashed_password = make_password(password)
        
        # 3. Salva o novo usuário no MongoDB
        user_data = {
            "username": username,
            "password": hashed_password, # Senha criptografada
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        users_collection.insert_one(user_data)
        
        return JsonResponse({"message": "Usuário cadastrado com sucesso."}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Erro interno no servidor: {e}"}, status=500)