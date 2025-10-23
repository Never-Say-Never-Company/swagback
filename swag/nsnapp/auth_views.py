import jwt
import json
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from decouple import config
from pymongo import MongoClient

# Variáveis e Configurações
MONGO_PATH = config("MONGO_PATH")
JWT_SECRET = config('SECRET_KEY_JWT', default='sua_chave_secreta_muito_forte_e_temporaria') 

def get_users_collection():
    """
    Função utilitária para retornar a coleção de credenciais de login no MongoDB.
    Recomendação: Usar uma coleção separada para credenciais locais (ex: 'users_api').
    """
    try:
        client = MongoClient(MONGO_PATH)
        db = client["swag"]
        return db["users_api"]
    except Exception as e:
        # Em caso de falha na conexão, é melhor retornar um erro 500
        raise Exception(f"Falha ao conectar ao MongoDB para usuários: {e}")

@csrf_exempt
def register_user(request):
    """
    View para cadastrar um novo usuário com senha criptografada.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido."}, status=405)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return JsonResponse({"error": "Usuário e senha são obrigatórios."}, status=400)

        users_collection = get_users_collection()
        
        # 1. Verifica unicidade do username
        if users_collection.find_one({"username": username}):
            return JsonResponse({"error": "Este nome de usuário já está em uso."}, status=409)

        # 2. Criptografa a senha com o hash do Django
        hashed_password = make_password(password)
        
        # 3. Salva no MongoDB
        user_data = {
            "username": username,
            "password": hashed_password,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        users_collection.insert_one(user_data)
        
        return JsonResponse({"message": "Usuário cadastrado com sucesso."}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Erro interno no servidor: {e}"}, status=500)

@csrf_exempt
def jwt_login_local(request):
    """
    View de login: Valida as credenciais locais no MongoDB e gera o Token JWT.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido"}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JsonResponse({"error": "Necessário 'username' e 'password'"}, status=400)

        users_collection = get_users_collection()
        user_doc = users_collection.find_one({"username": username})

        # 1. Verifica se o usuário existe
        if user_doc is None:
            return JsonResponse({"error": "Usuário ou senha inválidos."}, status=401)

        # 2. Verifica a senha criptografada
        if not check_password(password, user_doc.get("password")):
            return JsonResponse({"error": "Usuário ou senha inválidos."}, status=401)

        # 3. Se autenticado, gera o JWT
        payload = {
            'username': username,
            'user_id': str(user_doc["_id"]), # ID do Mongo para identificação
            'exp': datetime.utcnow() + timedelta(hours=24),  # Expiração em 24h
            'iat': datetime.utcnow()
        }
        
        # Gera e assina o token
        jwt_token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        
        return JsonResponse({
            "message": "Autenticação bem-sucedida",
            "token": jwt_token.decode('utf-8')
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except Exception as e:
        print(f"Erro no login: {e}")
        return JsonResponse({"error": f"Erro interno: {e}"}, status=500)