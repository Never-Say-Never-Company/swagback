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
import os

API_URL_PROJECT = config("JIRA_URL_PROJECT")
API_URL_ISSUES = config("JIRA_URL_ISSUES")
API_USER_NAME = config("JIRA_USER_NAME")
API_TOKEN = config("JIRA_TOKEN")
MONGO_PATH = config("MONGO_PATH")

client = MongoClient(MONGO_PATH)
db = client["swag"]
project_collections = db["projects_per_hours"]

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
        "fields": ["worklog", "key"],
        "maxResults": 100
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

@csrf_exempt
def save_data(request):
    if request.method == "POST":
        data = json.loads(request.body)
        print("retorno", data)

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
                if project_collections.name in project_collections.database.list_collection_names():
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

def get_project_by_author(author_name):
    results = project_collections.find({
        "issues": {
            "$elemMatch": {
                "author_logs": {
                    "$elemMatch": {
                        "display_name": author_name
                    }
                }
            }
        }
    })
    finded_projects = list(results)
    return finded_projects

def filther_data(data, author):
    for issue in data["issues"]:
        issue["author_logs"] = [
            log for log in issue["author_logs"]
            if log["display_name"] == author
        ]
    
    return data

@csrf_exempt
def get_project_per_author(request):
    if request.method == "POST":
        try:
            list_return = []
            data = json.loads(request.body)

            if isinstance(data, list):
                data = data[0]
            
            author = data.get("author")

            if not author:
                return JsonResponse({"error": "Necessário ter 'author' na chave."}, status=400)
            
            results = get_project_by_author(author)
            results = convert_objectid_to_str(results)

            for result in results:
                list_return.append(filther_data(result, author))

            return JsonResponse(list_return, safe=False)
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON inválido"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)