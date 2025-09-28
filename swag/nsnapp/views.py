from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from requests.auth import HTTPBasicAuth
from decouple import config
from pymongo import MongoClient
from datetime import datetime, timedelta
from nsnapp.utils import convert_objectid_to_str # Presumimos que esta função existe
import requests
import json
import copy
import os
import re

# Configurações e Conexão com MongoDB
API_URL_PROJECT = config("JIRA_URL_PROJECT")
API_URL_ISSUES = config("JIRA_URL_ISSUES")
JIRA_URL_USERS = config("JIRA_URL_USERS")
API_USER_NAME = config("JIRA_USER_NAME")
API_TOKEN = config("JIRA_TOKEN")
MONGO_PATH = config("MONGO_PATH")

client = MongoClient(MONGO_PATH)
db = client["swag"]
project_collections = db["projects_per_hours"]
users_collection = db["users"]

# --- FUNÇÕES AUXILIARES ---

# Função auxiliar: Converte a string de tempo (ex: "3h 26m") para minutos.
def convert_time_to_minutes(time_str):
    """Converte uma string de tempo (ex: '3h 26m', '1h', '30m') para o total de minutos."""
    if not time_str:
        return 0
    total_minutes = 0
    
    # Busca por horas (h)
    hours_match = re.search(r'(\d+)\s*h', time_str)
    if hours_match:
        total_minutes += int(hours_match.group(1)) * 60
        
    # Busca por minutos (m)
    minutes_match = re.search(r'(\d+)\s*m', time_str)
    if minutes_match:
        total_minutes += int(minutes_match.group(1))
        
    return total_minutes

# Função auxiliar: Extrai uma lista simples de account_ids
def extract_account_ids(authors_list):
    """Extrai uma lista de strings de account_id da lista de dicionários de autores."""
    # Garante que só pega IDs válidos
    return [author['account_id'] for author in authors_list if isinstance(author, dict) and author.get('account_id')]

# --- FUNÇÕES DE ACESSO À API E MONGO EXISTENTES ---

def get_api_data_project(user_name, token):
    response = requests.get(
            f"{API_URL_PROJECT}",
            auth=HTTPBasicAuth(user_name, token),
        )
    response.raise_for_status()
    return response.json()

def get_api_data_issues():
    params = {
        "jql": "project IN (SE, SM2)",
        "fields": ["worklog", "key"],
        "maxResults": 1000
    }
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Cookie': os.getenv('JIRA_COOKIE'),
    }
    

    response = requests.post(
            API_URL_ISSUES,
            headers=headers,
            auth=(API_USER_NAME, API_TOKEN),
            json=params
        )
    response.raise_for_status()
    return response.json()

def clean_data(project, issue):
    worklogs = issue.get("fields", {}).get("worklog", {}).get("worklogs", [])
    
    author_logs = []
    for w in worklogs:
        author_logs.append({
            "account_id": w.get("author", {}).get("accountId"),
            "display_name": w.get("author", {}).get("displayName"),
            "jira_created_at": datetime.strptime(w.get("created").split(".")[0], "%Y-%m-%dT%H:%M:%S"),
            "time_spent": w.get("timeSpent"),
            "time_spent_seconds": w.get("timeSpentSeconds"),
        })

    return {
        "id": project.get("id"),
        "key": project.get("key"),
        "name": project.get("name"),
        "issues": [
            {
                "issue_id": issue.get("id"),
                "issue_key": issue.get("key"),
                "author_logs": author_logs
            }
        ]
    }

def get_api_data_users(user_name, token):
    params = {
        "maxResults": 1000,
        "orderBy": "displayName"
    }
    
    response = requests.get(
        f"{JIRA_URL_USERS}",
        auth=HTTPBasicAuth(user_name, token),
        params=params 
    )
    response.raise_for_status()
    return response.json()

@csrf_exempt
def save_data(request):
    if request.method == "POST":
        data = json.loads(request.body)

        if data is None:
            return JsonResponse({"error": "Dados inválidos"}, status=400)

        user_name = data.get("user_name")
        token = data.get("token")

        save_users(user_name, token)
        project_data = get_api_data_project(user_name, token)
        issues_data = get_api_data_issues()
        issues_list = issues_data.get("issues", [])

        try:
            if isinstance(project_data, list) and isinstance(issues_list, list):
                cleaned_data = []
                for project in project_data:
                    for issue in issues_list:
                        worklogs = issue.get("fields", {}).get("worklog", {}).get("worklogs", [])
                        if worklogs:
                            issue_key = issue["key"]
                            issue_key = issue_key.split("-")[0]
                            
                            if project["key"] == issue_key:
                                cleaned_data.append(clean_data(project, issue))
                all_collection = project_collections.database.list_collection_names()
                if project_collections.name in all_collection:
                    project_collections.drop()
                project_collections.insert_many(cleaned_data)
                
                return JsonResponse({"status": "success", "message": "Dados salvos"})
            elif isinstance(project_data, dict) and isinstance(issues_data, dict):
                cleaned_project_data = clean_data(project_data, issues_data)
                project_collections.insert_one(cleaned_project_data)
        except requests.exceptions.RequestException as e:
            return requests.Response.json()
    
def get_project_by_period(begin, end):    
    begin_formated = datetime.strptime(begin, "%Y-%m-%d")
    end_formated = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    results = project_collections.find({
        "issues": {
            "$elemMatch": {
                "author_logs": {
                    "$elemMatch": {
                        "jira_created_at": {
                            "$gte": begin_formated,
                            "$lte": end_formated
                        }
                    }
                }
            }
        }
    })
    finded_projects = list(results)

    return finded_projects

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

def get_project_by_author(accountId):
    results = project_collections.find({
        "issues": {
            "$elemMatch": {
                "author_logs": {
                    "$elemMatch": {
                        "account_id": accountId
                    }
                }
            }
        }
    })
    finded_projects = list(results)
    return finded_projects

def filter_projects_by_projects_author(projects, account_id):
    filtered = []

    for project in projects:
        for issue in project.get("issues", []):
            for author_log in issue.get("author_logs", []):
                print(author_log.get("display_name"))

        has_author_log = False
        for issue in project.get("issues", []):
            filtered_logs = [
                log for log in issue.get("author_logs", [])
                if log.get("account_id") == account_id
            ]
            if filtered_logs:
                has_author_log = True
                issue["author_logs"] = filtered_logs
        if has_author_log:
            filtered.append(project)
    return filtered

def filther_data(data, author):
    for issue in data["issues"]:
        issue["author_logs"] = [
            log for log in issue["author_logs"]
            if log["account_id"] == author
        ]
    
    return data

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
                    return JsonResponse({"error": "Necessário ter 'author' na chave."}, status=400)
            
                results = get_project_by_author(author)
                results = convert_objectid_to_str(results)

                for result in results:
                    list_return.append(filther_data(result, author))
            
            print(list_return)
            return JsonResponse(list_return, safe=False)
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON inválido"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
# --- FUNÇÃO PRINCIPAL CORRIGIDA ---

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

        # 1. Buscando e preparando os projetos
        projects = get_project_by_period(begin, end)
        projects = convert_objectid_to_str(projects)
        projects_original = copy.deepcopy(projects) 
        
        # 2. Extraindo os account_ids selecionados
        selected_author_ids = extract_account_ids(authors)
        
        # Inicializar os dicionários de agregação (Nome do Projeto: Total de Minutos)
        total_team_aggregation = {}
        selected_people_aggregation = {}

        # 3. Processamento e Agregação de Logs (CORRIGIDO)
        for project in projects_original:
            project_name = project.get("name")
            
            if not project_name:
                continue

            total_team_minutes = 0
            selected_people_minutes = 0
            
            # NOVO: Iterar sobre a lista de 'issues', que contém os 'author_logs'
            for issue in project.get("issues", []):
                
                # Iterar sobre a lista de 'author_logs' dentro de cada issue
                for log in issue.get("author_logs", []):
                    account_id = log.get("account_id")
                    
                    time_in_minutes = 0
                    if isinstance(log.get("time_spent_seconds"), int):
                        # time_spent_seconds geralmente é em segundos, então divide por 60
                        time_in_minutes = log["time_spent_seconds"] / 60
                    else:
                        # Se não, converte a string
                        time_in_minutes = convert_time_to_minutes(log.get("time_spent"))
                    
                    # Acumular para o total da equipe
                    total_team_minutes += time_in_minutes
                    
                    # Acumular para as pessoas selecionadas
                    if account_id in selected_author_ids:
                        selected_people_minutes += time_in_minutes
            
            # Acumular no nível do projeto
            if total_team_minutes > 0:
                total_team_aggregation[project_name] = total_team_aggregation.get(project_name, 0) + total_team_minutes

            if selected_people_minutes > 0:
                selected_people_aggregation[project_name] = selected_people_aggregation.get(project_name, 0) + selected_people_minutes


        # 4. Formatação Final
        formatted_team_list = []
        for name, minutes in total_team_aggregation.items():
            formatted_team_list.append({
                "nome_projeto": name,
                "minutos_projeto": round(minutes) # Arredonda para inteiro
            })

        formatted_selected_list = []
        for name, minutes in selected_people_aggregation.items():
            formatted_selected_list.append({
                "nome_projeto": name,
                "minutos_projeto": round(minutes) # Arredonda para inteiro
            })

        # Estrutura de retorno final
        list_return = {
            "toda_equipe": formatted_team_list,
            "pessoas_selecionadas": formatted_selected_list
        }
            
        return JsonResponse(list_return, safe=False)

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except Exception as e:
        # É sempre bom logar o erro 'e' aqui para depuração
        print(f"Erro inesperado em get_project_per_period_and_author: {e}") 
        return JsonResponse({"error": f"Erro interno no servidor: {e}"}, status=500)
    
def save_users(user_name, token):

    try:
        users_data = get_api_data_users(user_name, token)

        users_collection.delete_many({})

        if users_data:
            users_collection.insert_many(users_data)

    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": f"Erro ao acessar API Jira: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Ocorreu um erro inesperado: {str(e)}"}, status=500)


from django.http import JsonResponse
from pymongo import MongoClient

# Assumindo que MONGO_PATH está definido em algum lugar
# Assumindo que o ambiente Django ou similar está configurado

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
            # A busca por REGEX (parcial, case-insensitive) não muda
            filters['displayName'] = {'$regex': display_name, '$options': 'i'}


        users_collection = db["users"]
        
        # 🎯 MUDANÇA AQUI: Adiciona o .sort()
        users = list(
            users_collection.find(filters, {"_id": 0, "accountId": 1, "displayName": 1})
            .sort("displayName", 1)  # Ordena pelo campo 'displayName' em ordem ascendente (1)
        )

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