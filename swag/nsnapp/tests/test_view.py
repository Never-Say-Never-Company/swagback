import pytest
import json
from unittest.mock import patch, MagicMock
from django.urls import reverse
from datetime import datetime
from django.test import Client


@pytest.fixture
def mock_services():
    """Mocka todas as funções de serviço que interagem com o DB/API externas."""
    patchers = [
        patch("nsnapp.views.save_data_service"),
        patch("nsnapp.views.get_project_by_period"),
        patch("nsnapp.views.get_project_by_author"),
        patch("nsnapp.views.aggregate_project_periods_and_authors"),
        patch("nsnapp.views.list_users_service"),
        patch("nsnapp.views.list_user_by_Id_service"),
        patch("nsnapp.views.count_issues_grouped_by_project_service"),
        patch("nsnapp.views.count_issues_by_user_and_total_hours_service"),
        patch("nsnapp.views.paginate_date_service"),
        patch("nsnapp.views.save_developer_rates_service"),
        patch("nsnapp.views.list_developer_rates_service"),
        patch("nsnapp.views.list_projects_service"),
        patch("nsnapp.views.convert_objectid_to_str"),
        patch("nsnapp.views.filther_data"),
    ]
    mocks = [p.start() for p in patchers]

    mocks[1].return_value = []
    mocks[2].return_value = []
    mocks[12].return_value = {}
    mocks[11].return_value = lambda x: x

    service_mocks = {p.attribute.split(".")[-1]: m for p, m in zip(patchers, mocks)}

    yield service_mocks

    for p in patchers:
        p.stop()


def test_home_endpoint(client):
    url = "/"
    response = client.get(url)
    assert response.status_code == 200
    assert b"API Swag est\xc3\xa1 no ar" in response.content


def test_save_data_post_success(client, mock_services):
    mock_services["save_data_service"].return_value = {
        "status": "success",
        "message": "Dados salvos",
    }
    url = reverse("save_data")

    response = client.post(url, content_type="application/json")

    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Dados salvos"}
    mock_services["save_data_service"].assert_called_once()


def test_get_project_per_period_success(client, mock_services):
    begin = "2025-01-01"
    end = "2025-01-31"

    mock_services["get_project_by_period"].return_value = [{"key": "PROJ1"}]
    mock_services["convert_objectid_to_str"].return_value = [{"key": "PROJ1_str"}]

    url = reverse("project_per_period")
    data = {"begin": begin, "end": end}
    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 200
    assert response.json() == [{"key": "PROJ1_str"}]
    mock_services["get_project_by_period"].assert_called_once_with(begin, end)


def test_get_project_per_period_missing_params(client, mock_services):
    url = reverse("project_per_period")
    data = {"begin": "2025-01-01"}
    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 400
    assert "Necessário ter 'begin' e 'end' nas chaves" in response.json().get("error")


def test_get_project_per_author_success(client, mock_services):
    author_id = "user-A"

    mock_services["get_project_by_author"].return_value = [
        {"key": "PROJ1", "issues": []}
    ]
    mock_services["convert_objectid_to_str"].side_effect = lambda x: x
    mock_services["filther_data"].return_value = {"key": "PROJ1_filtered"}

    url = reverse("project_per_author")
    data = [{"account_id": author_id}]
    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 200
    assert response.json() == [{"key": "PROJ1_filtered"}]
    mock_services["get_project_by_author"].assert_called_once_with(author_id)

    mock_services["filther_data"].assert_called_once()
    assert mock_services["filther_data"].call_args[0][1] == author_id


def test_get_project_per_period_and_author_success(client, mock_services):
    begin = "2025-01-01"
    end = "2025-01-31"
    authors = [{"account_id": "user-A"}]
    expected_result = {"toda_equipe": [], "pessoas_selecionadas": []}

    mock_services["aggregate_project_periods_and_authors"].return_value = (
        expected_result
    )

    url = reverse("project_per_period_and_author")
    data = {"begin": begin, "end": end, "authors": authors}
    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 200
    assert response.json() == expected_result
    mock_services["aggregate_project_periods_and_authors"].assert_called_once_with(
        begin, end, authors
    )


def test_list_users_no_filters_success(client, mock_services):
    expected_users = [{"accountId": "user1", "displayName": "User One"}]
    mock_services["list_users_service"].return_value = expected_users

    url = reverse("list_users")
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == expected_users

    mock_services["list_users_service"].assert_called_once_with({})


def test_list_users_with_filters_success(client, mock_services):
    mock_services["list_users_service"].return_value = []

    url = reverse("list_users")
    response = client.get(f"{url}?accountId=user1&displayName=Test")

    assert response.status_code == 200
    expected_filters = {
        "accountId": "user1",
        "displayName": {"$regex": "Test", "$options": "i"},
    }
    mock_services["list_users_service"].assert_called_once_with(expected_filters)


def test_list_user_by_Id_found(client, mock_services):
    account_id = "user-A"
    expected_user = {"accountId": account_id, "displayName": "User A"}
    mock_services["list_user_by_Id_service"].return_value = expected_user

    url = reverse("list_user_by_accountId", kwargs={"accountId": account_id})
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == expected_user
    mock_services["list_user_by_Id_service"].assert_called_once_with(account_id)


def test_list_user_by_Id_not_found(client, mock_services):
    mock_services["list_user_by_Id_service"].return_value = None

    url = reverse("list_user_by_accountId", kwargs={"accountId": "non-existent"})
    response = client.get(url)

    assert response.status_code == 404
    assert "Usuário não encontrado" in response.json().get("error")


def test_save_developer_rates_success(client, mock_services):
    data = [{"id_desenvolvedor": "dev1", "valor_por_hora": 50.0}]
    mock_services["save_developer_rates_service"].return_value = {
        "inserted": 1,
        "modified": 0,
        "message": "Taxas salvas com sucesso.",
    }

    url = reverse("save_developer_rates")
    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["inserted"] == 1
    mock_services["save_developer_rates_service"].assert_called_once_with(data)


def test_save_developer_rates_invalid_value_error(client, mock_services):

    mock_services["save_developer_rates_service"].side_effect = ValueError(
        "Erro de validação."
    )
    data = [{"id_desenvolvedor": "dev1", "valor_por_hora": "invalido"}]

    url = reverse("save_developer_rates")
    response = client.post(url, json.dumps(data), content_type="application/json")

    assert response.status_code == 400
    assert response.json().get("error") == "Erro de validação."


def test_list_developer_rates_success(client, mock_services):
    expected_rates = [
        {
            "id_desenvolvedor": "dev1",
            "valor_por_hora": 50.0,
            "nome_desenvolvedor": "Dev A",
        }
    ]
    mock_services["list_developer_rates_service"].return_value = expected_rates

    url = reverse("list_developer_rates")
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == expected_rates
    mock_services["list_developer_rates_service"].assert_called_once()


def test_list_projects_success(client, mock_services):
    expected_projects = [{"id": "10000", "name": "Project Alpha"}]
    mock_services["list_projects_service"].return_value = expected_projects

    url = reverse("list_projects")
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == expected_projects
    mock_services["list_projects_service"].assert_called_once()


def test_count_issues_by_user_and_total_hours_no_id_success(client, mock_services):
    expected_result = [{"nome": "Dev A", "total_horas": 10.0}]
    mock_services["count_issues_by_user_and_total_hours_service"].return_value = (
        expected_result
    )

    url = reverse(
        "count_issues_by_user_and_total_hours_by_project", kwargs={"project_id": None}
    )
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == expected_result
    mock_services[
        "count_issues_by_user_and_total_hours_service"
    ].assert_called_once_with(None)


def test_count_issues_by_user_and_total_hours_with_id_success(client, mock_services):
    project_id = "10001"
    expected_result = [{"nome": "Dev B", "total_horas": 5.0}]
    mock_services["count_issues_by_user_and_total_hours_service"].return_value = (
        expected_result
    )

    url = reverse(
        "count_issues_by_user_and_total_hours_by_project",
        kwargs={"project_id": project_id},
    )
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == expected_result
    mock_services[
        "count_issues_by_user_and_total_hours_service"
    ].assert_called_once_with(project_id)
