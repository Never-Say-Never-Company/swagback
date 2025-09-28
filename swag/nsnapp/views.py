from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from requests.auth import HTTPBasicAuth
from decouple import config
from pymongo import MongoClient
from datetime import datetime, timedelta
from nsnapp.utils import convert_objectid_to_str
import requests
import json
import copy
import os

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

def get_api_data_project(user_name, token):
    response = requests.get(
            f"{API_URL_PROJECT}",
            auth=HTTPBasicAuth(user_name, token)
        )
    response.raise_for_status()
    return response.json()

def get_api_data_issues():
    params = {
        "jql": "project IN (SE, SM2)",
        "fields": ["worklog", "key"]
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
        response = requests.get(
            f"{JIRA_URL_USERS}",
            auth=HTTPBasicAuth(user_name, token)
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
            return JsonResponse({"error": "O corpo deve conter uma lista de autores."}, status=400)
        projects = get_project_by_period(begin, end)
        projects = convert_objectid_to_str(projects)
        projects_original = copy.deepcopy(projects)

        list_return = []

        for author_item in authors:
            account_id = author_item.get("account_id")
            if not account_id:
                return JsonResponse({"error": "Cada autor deve ter 'account_id'."}, status=400)

            projects_for_author = copy.deepcopy(projects_original)
            projects_by_author = filter_projects_by_projects_author(projects_for_author, account_id)

            for project in projects_by_author:
                list_return.append(filther_data(project, account_id))
            
            print("---------------------acabou aqui-----------------")

        return JsonResponse(list_return, safe=False)

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

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
