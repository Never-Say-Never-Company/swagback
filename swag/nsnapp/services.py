import requests
from requests.auth import HTTPBasicAuth
from decouple import config
from pymongo import MongoClient
from pymongo.operations import ReplaceOne
from datetime import datetime, timedelta
import json
import copy
import os
import re

from nsnapp.utils import convert_objectid_to_str, convert_time_to_minutes 

API_URL_PROJECT = config("JIRA_URL_PROJECT")
API_URL_ISSUES = config("JIRA_URL_ISSUES")
JIRA_URL_USERS = config("JIRA_URL_USERS")
MONGO_PATH = config("MONGO_PATH")

from swag.settings import API_USER_NAME, API_TOKEN 

client = MongoClient(MONGO_PATH)
db = client["swag"]
project_collections = db["projects_per_hours"]
users_collection = db["users"]
developer_rates_collection = db["developer_rates"] 

def extract_account_ids(authors_list):
    """Extrai uma lista de strings de account_id da lista de dicionários de autores."""
    return [author['account_id'] for author in authors_list if isinstance(author, dict) and author.get('account_id')]

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

def save_users(user_name, token):
    try:
        users_data = get_api_data_users(user_name, token)
        users_collection.delete_many({})

        if users_data:
            users_collection.insert_many(users_data)
        return {"status": "success", "message": "Usuários salvos"}

    except requests.exceptions.RequestException as e:
        raise Exception(f"Erro ao acessar API Jira para usuários: {str(e)}")
    except Exception as e:
        raise Exception(f"Ocorreu um erro inesperado ao salvar usuários: {str(e)}")

def save_data_service():
    user_name = API_USER_NAME
    token = API_TOKEN

    save_users(user_name, token)
    project_data = get_api_data_project(user_name, token)
    issues_data = get_api_data_issues()
    issues_list = issues_data.get("issues", [])

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
        
        return {"status": "success", "message": "Dados salvos"}
    
    elif isinstance(project_data, dict) and isinstance(issues_data, dict):
        cleaned_project_data = clean_data(project_data, issues_data)
        project_collections.insert_one(cleaned_project_data)
        return {"status": "success", "message": "Dados salvos"}
    
    return {"status": "error", "message": "Estrutura de dados inesperada da API."}

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
    return list(results)

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
    return list(results)

def filter_projects_by_projects_author(projects, account_id):
    filtered = []
    for project in projects:
        has_author_log = False
        new_project = copy.deepcopy(project) 
        
        for issue in new_project.get("issues", []):
            filtered_logs = [
                log for log in issue.get("author_logs", [])
                if log.get("account_id") == account_id
            ]
            if filtered_logs:
                has_author_log = True
                issue["author_logs"] = filtered_logs
        
        if has_author_log:
            filtered.append(new_project)
            
    return filtered

def filther_data(data, author):
    for issue in data["issues"]:
        issue["author_logs"] = [
            log for log in issue["author_logs"]
            if log["account_id"] == author
        ]
    return data

def aggregate_project_periods_and_authors(begin, end, authors):
    projects = get_project_by_period(begin, end)
    projects_original = convert_objectid_to_str(projects)
    selected_author_ids = extract_account_ids(authors)
    
    total_team_aggregation = {}
    selected_people_aggregation = {}

    for project in projects_original:
        project_name = project.get("name")
        
        if not project_name:
            continue

        total_team_minutes = 0
        selected_people_minutes = 0
        
        for issue in project.get("issues", []):
            for log in issue.get("author_logs", []):
                account_id = log.get("account_id")
                
                time_in_minutes = 0
                if isinstance(log.get("time_spent_seconds"), int):
                    time_in_minutes = log["time_spent_seconds"] / 60
                else:
                    time_in_minutes = convert_time_to_minutes(log.get("time_spent"))
                
                total_team_minutes += time_in_minutes
                
                if account_id in selected_author_ids:
                    selected_people_minutes += time_in_minutes
        
        if total_team_minutes > 0:
            total_team_aggregation[project_name] = total_team_aggregation.get(project_name, 0) + total_team_minutes

        if selected_people_minutes > 0:
            selected_people_aggregation[project_name] = selected_people_aggregation.get(project_name, 0) + selected_people_minutes

    formatted_team_list = []
    for name, minutes in total_team_aggregation.items():
        formatted_team_list.append({
            "nome_projeto": name,
            "minutos_projeto": round(minutes)
        })

    formatted_selected_list = []
    for name, minutes in selected_people_aggregation.items():
        formatted_selected_list.append({
            "nome_projeto": name,
            "minutos_projeto": round(minutes)
        })

    return {
        "toda_equipe": formatted_team_list,
        "pessoas_selecionadas": formatted_selected_list
    }

def list_users_service(filters):
    users = list(
        users_collection.find(filters, {"_id": 0, "accountId": 1, "displayName": 1})
        .sort("displayName", 1)
    )
    return users

def list_user_by_Id_service(accountId):
    user = users_collection.find_one({"accountId": accountId}, {"_id": 0,  "accountId": 1, "displayName": 1})
    return user

def count_issues_grouped_by_project_service():
    pipeline = [
        {"$unwind": "$issues"},
        {
            "$group": {
                "_id": "$key",
                "issue_count": {"$sum": 1}
            }
        },
        {"$sort": {"issue_count": -1}}
    ]
    results = list(project_collections.aggregate(pipeline))

    return [
        {"projeto": r["_id"], "quantidade_issues": r["issue_count"]}
        for r in results
    ]

def count_issues_by_user_and_total_hours_service():
    """
    Calcula o total de issues, horas trabalhadas e o CUSTO TOTAL (Horas * Taxa)
    por desenvolvedor, AGRUPANDO PELO NOME e buscando a taxa via accountId na coleção users.
    Retorna NULL para valor_por_hora e custo_total se a taxa não for encontrada.
    """
    pipeline = [
        {"$unwind": "$issues"},
        {"$unwind": "$issues.author_logs"},
        
        {
            "$group": {
                "_id": "$issues.author_logs.display_name",  
                "issue_count": { "$sum": 1 },  
                "total_time_spent_minutes": {
                    "$sum": { "$divide": ["$issues.author_logs.time_spent_seconds", 60] }
                }  
            }
        },
        
        {
            "$lookup": {
                "from": "users",              
                "localField": "_id",         
                "foreignField": "displayName",   
                "as": "user_details"
            }
        },
        
        
        {
            "$unwind": {
                "path": "$user_details",
                "preserveNullAndEmptyArrays": True
            }
        },
        
        
        {
            "$lookup": {
                "from": "developer_rates",
                "localField": "user_details.accountId", 
                "foreignField": "id_desenvolvedor",     
                "as": "rate_info"
            }
        },
        
        
        {
            "$unwind": {
                "path": "$rate_info",
                "preserveNullAndEmptyArrays": True
            }
        },
        
        
        {
            "$project": {
                "_id": 0, 
                "nome": "$_id", 
                "quantidade_issues": "$issue_count",
                "total_horas": { "$round": [{ "$divide": ["$total_time_spent_minutes", 60] }, 2] },
                "valor_por_hora": {
                    
                    "$ifNull": ["$rate_info.valor_por_hora", None] 
                },
                "custo_total": {
                    "$let": {
                        "vars": {
                            "horas": { "$divide": ["$total_time_spent_minutes", 60] },
                            "taxa": { "$ifNull": ["$rate_info.valor_por_hora", None] } 
                        },
                        "in": {
                            "$cond": { 
                                "if": { "$eq": ["$$taxa", None] },
                                "then": None,
                                "else": { "$round": [{ "$multiply": ["$$horas", "$$taxa"] }, 2] }
                            }
                        }
                    }
                }
            }
        },
        
        
        {"$sort": {"custo_total": -1}}
    ]
    
    results = list(project_collections.aggregate(pipeline))
    return results

def paginate_date_service(init, end):
    if init > end:
        raise ValueError("'init' deve ser menor que o 'end'.")
    
    all_collection = list(project_collections.find())
    paginate_datas = []

    for i in range(init, end + 1):
        if i >= len(all_collection):
            break
        
        paginate_datas.append(convert_objectid_to_str(all_collection[i]))
        
    return paginate_datas





def save_developer_rates_service(data: list) -> dict:
    """
    Deleta TODOS os dados existentes e salva as novas taxas de desenvolvedores.
    """
    if not data:
        return {"inserted": 0, "modified": 0, "message": "Nenhum dado fornecido para salvar."}

    
    for item in data:
        dev_id = item.get("id_desenvolvedor")
        rate_value = item.get("valor_por_hora")

        if not dev_id or rate_value is None:
            raise ValueError("Cada objeto deve ter 'id_desenvolvedor' e 'valor_por_hora'.")
        
        try:
            rate_value = float(rate_value)
        except (ValueError, TypeError):
            raise ValueError("O campo 'valor_por_hora' deve ser um número válido.")

    
    delete_result = developer_rates_collection.delete_many({})
    print(f"Documentos deletados na coleção 'developer_rates': {delete_result.deleted_count}")

    
    operations = []
    for item in data:
        replacement_doc = {
            'id_desenvolvedor': item.get("id_desenvolvedor"),
            'valor_por_hora': float(item.get("valor_por_hora")),
            'ultima_atualizacao': datetime.now()
        }

        
        operations.append(
            ReplaceOne(
                filter={'id_desenvolvedor': item.get("id_desenvolvedor")},
                replacement=replacement_doc,
                upsert=True
            )
        )

    
    result = developer_rates_collection.bulk_write(operations)
    
    return {
        "inserted": result.upserted_count + result.inserted_count,
        "modified": result.modified_count,
        "message": "Taxas de desenvolvedores salvas/atualizadas com sucesso."
    }

def list_developer_rates_service() -> list:
    """
    Retorna todos os documentos da coleção developer_rates,
    juntando-os com o nome do usuário (displayName) da coleção users.
    """
    pipeline = [
        
        {
            "$lookup": {
                "from": "users",              
                "localField": "id_desenvolvedor", 
                "foreignField": "accountId",   
                "as": "user_info"             
            }
        },
        
        {
            "$unwind": {
                "path": "$user_info",
                "preserveNullAndEmptyArrays": True  
            }
        },
        
        {
            "$project": {
                "_id": 0,  
                "id_desenvolvedor": "$id_desenvolvedor",
                "valor_por_hora": "$valor_por_hora",
                "ultima_atualizacao": { "$dateToString": { "format": "%Y-%m-%dT%H:%M:%S", "date": "$ultima_atualizacao" } },
                "nome_desenvolvedor": {
                    "$ifNull": ["$user_info.displayName", "NOME NÃO ENCONTRADO"]
                }
            }
        }
    ]
    
    
    rates_list = list(developer_rates_collection.aggregate(pipeline))
    
    return rates_list