import jwt
import json
from django.http import JsonResponse
from functools import wraps
from decouple import config

JWT_SECRET = config('SECRET_KEY_JWT', default='sua_chave_secreta_muito_forte_e_temporaria') 

def jwt_required(view_func):
    """
    Decorador para exigir um token JWT válido na requisição.
    O token deve ser enviado no cabeçalho: Authorization: Bearer <token>
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({
                "error": "Acesso negado. Token não fornecido ou formato inválido."
            }, status=401)

        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            request.user_info = payload
            return view_func(request, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token JWT expirado."}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({"error": "Token JWT inválido."}, status=401)
        except Exception as e:
            return JsonResponse({"error": f"Erro de autenticação interno: {e}"}, status=500)
            
    return wrapper