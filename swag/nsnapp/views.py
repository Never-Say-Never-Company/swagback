from django.shortcuts import render
from django.http import HttpResponse
from requests.auth import HTTPBasicAuth
from decouple import config
import requests
from pymongo import MongoClient

API_URL_PROJECT = config("JIRA_URL_PROJECT")
API_URL_ISSUES = config("JIRA_URL_ISSUES")
API_USER_NAME = config("JIRA_USER_NAME")
API_TOKEN = config("JIRA_TOKEN")
MONGO_PATH = config("MONGO_PATH")

client = MongoClient(MONGO_PATH)
db = client["swag"]
project_collections = db["projects_per_hours"]

def get_api_data_project():
    response = requests.get(
            f"{API_URL_PROJECT}",
            auth=HTTPBasicAuth(API_USER_NAME, API_TOKEN)
        )
    response.raise_for_status()
    return response.json()

def get_api_data_issues():
    params = {
        "jql": "project IN (SE,SM2)",
        "fields": "worklog",
        "maxResults": 100
    }

    response = requests.get(
            API_URL_ISSUES,
            auth=HTTPBasicAuth(API_USER_NAME, API_TOKEN),
            params=params
        )
    response.raise_for_status()
    return response.json()

def clean_data(project, issue):
    worklogs = issue.get("fields", {}).get("worklog", {}).get("worklogs", [])
    
    author_logs = []
    for w in worklogs:
        author_logs.append({
            "display_name": w.get("author", {}).get("displayName"),
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

def save_data():
    project_data = get_api_data_project()
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
            project_collections.drop()
            project_collections.insert_many(cleaned_data)
        elif isinstance(project_data, dict) and isinstance(issues_data, dict):
            cleaned_project_data = clean_data(project_data, issues_data)
            project_collections.insert_one(cleaned_project_data)
    except requests.exceptions.RequestException as e:
        return requests.Response.json()
    
save_data()