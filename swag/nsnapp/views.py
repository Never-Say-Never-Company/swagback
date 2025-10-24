from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
import copy
import requests 


from .services import (
    save_data_service, 
    get_project_by_period, 
    get_project_by_author, 
    filther_data,
    aggregate_project_periods_and_authors,
    list_users_service,
    list_user_by_Id_service,
    count_issues_grouped_by_project_service,
    count_issues_by_user_and_total_hours_service,
    paginate_date_service,
    save_developer_rates_service, 
    list_developer_rates_service  
)
from nsnapp.utils import convert_objectid_to_str





@csrf_exempt
def save_data(request):
    if request.method == "POST":
        try:
            
            result = save_data_service()
            return JsonResponse(result)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": str(e)}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Erro interno ao salvar dados: {e}"}, status=500)
    
@csrf_exempt
def get_project_per_period(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            if isinstance(data, list):
                data = data[0]

            begin = data.get("begin")
            end = data.get("end")

            if not begin or not end:
                return JsonResponse({"error": "Necessário ter 'begin' e 'end' nas chaves."}, status=400)
            
            result = list(get_project_by_period(begin, end))
            result = convert_objectid_to_str(result)
            
            return JsonResponse(result, safe=False)
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON inválido"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_project_per_author(request):
    if request.method == "POST":
        try:
            list_return = []
            data = json.loads(request.body)

            if not isinstance(data, list):
                return JsonResponse({"error": "O corpo deve ser uma lista de autores."}, status=400)
        
            for item in data:
                author = item.get("account_id")

                if not author:
                    return JsonResponse({"error": "Necessário ter 'account_id' na chave."}, status=400)
            
                results = get_project_by_author(author)
                results = convert_objectid_to_str(results)

                for result in results:
                    
                    
                    list_return.append(filther_data(copy.deepcopy(result), author)) 
            
            return JsonResponse(list_return, safe=False)
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON inválido"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
@csrf_exempt
def get_project_per_period_and_author(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido"}, status=405)

    try:
        data = json.loads(request.body)

        begin = data.get("begin")
        end = data.get("end")
        authors = data.get("authors")

        if not begin or not end:
            return JsonResponse({"error": "Necessário ter 'begin' e 'end' nas chaves."}, status=400)
        
        if not isinstance(authors, list) or not authors:
            return JsonResponse({"error": "O corpo deve conter uma lista não vazia de autores."}, status=400)

        
        list_return = aggregate_project_periods_and_authors(begin, end, authors)
            
        return JsonResponse(list_return, safe=False)

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except Exception as e:
        print(f"Erro inesperado em get_project_per_period_and_author: {e}") 
        return JsonResponse({"error": f"Erro interno no servidor: {e}"}, status=500)
    
def list_users(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Método não permitido. Use GET."}, status=405)

    try:
        filters = {}

        account_id = request.GET.get('accountId')
        if account_id:
            filters['accountId'] = account_id

        display_name = request.GET.get('displayName')
        if display_name:
            filters['displayName'] = {'$regex': display_name, '$options': 'i'}
        
        users = list_users_service(filters)
        return JsonResponse(users, safe=False)

    except Exception as e:
        return JsonResponse({"error": f"Falha ao acessar os usuários: {e}"}, status=500)

def list_user_by_Id(request, accountId):
    if request.method != 'GET':
        return JsonResponse({"error": "Método não permitido. Use GET."}, status=405)

    try:
        user = list_user_by_Id_service(accountId)

        if user:
            return JsonResponse(user, safe=False)
        else:
            return JsonResponse({"error": "Usuário não encontrado."}, status=404)

    except Exception as e:
        return JsonResponse({"error": f"Falha ao acessar o usuário: {e}"}, status=500)

def count_issues_grouped_by_project(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Método não permitido. Use GET."}, status=405)

    try:
        formatted = count_issues_grouped_by_project_service()
        return JsonResponse(formatted, safe=False)

    except Exception as e:
        return JsonResponse(
            {"error": f"Falha ao contar issues por projeto: {e}"},
            status=500
        )

def count_issues_by_user_and_total_hours(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Método não permitido. Use GET."}, status=405)

    try:
        formatted = count_issues_by_user_and_total_hours_service()
        return JsonResponse(formatted, safe=False)

    except Exception as e:
        return JsonResponse(
            {"error": f"Falha ao contar issues por projeto: {e}"},
            status=500
        )
               
@csrf_exempt 
@require_http_methods(["POST"])
def paginate_date(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Método não permitido. Use POST."}, status=405)
    
    try:
        data = json.loads(request.body)

        if data is None:
            return JsonResponse({"error": "Dados inválidos"}, status=400)
        
        init = data.get("init")
        end = data.get("end")

        if init is None or end is None:
             return JsonResponse({"Error": "Necessário ter 'init' e 'end' no corpo."}, status=400)
        
        paginate_datas = paginate_date_service(init, end)

        return JsonResponse(paginate_datas, safe=False)
    
    except ValueError as e:
        return JsonResponse({"Error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": f"Falha ao paginar dados: {e}"},
            status=500
        )
        




@csrf_exempt
@require_http_methods(["POST"])
def save_developer_rates(request):
    try:
        data = json.loads(request.body)

        if not isinstance(data, list):
            return JsonResponse({"error": "O corpo da requisição deve ser uma lista de desenvolvedores."}, status=400)
        
        
        result = save_developer_rates_service(data)

        return JsonResponse({
            "status": "success", 
            "message": result["message"],
            "inserted": result["inserted"],
            "modified": result["modified"]
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido na requisição."}, status=400)
    except ValueError as e:
        
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        print(f"Erro inesperado em save_developer_rates: {e}") 
        return JsonResponse({"error": f"Erro interno no servidor: {e}"}, status=500)
        
        
@require_http_methods(["GET"])
def list_developer_rates(request):
    """
    Novo endpoint GET para listar todos os documentos de taxas de desenvolvedores.
    """
    try:
        
        rates_list = list_developer_rates_service()
            
        
        return JsonResponse(rates_list, safe=False, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Erro ao listar dados: {str(e)}'}, status=500)