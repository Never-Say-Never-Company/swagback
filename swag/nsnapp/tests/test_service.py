import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from bson import ObjectId

# Importa as funções do módulo services
from nsnapp.services import (
    extract_account_ids,
    clean_data,
    get_project_by_period,
    get_project_by_author,
    filter_projects_by_projects_author,
    filther_data,
    aggregate_project_periods_and_authors,
    save_developer_rates_service,
    list_developer_rates_service,
    list_projects_service,
    count_issues_by_user_and_total_hours_service,
)
from nsnapp.utils import (
    convert_objectid_to_str,
)  # Se a função for necessária para simular o retorno

# --- Simulações (Fixtures) ---


@pytest.fixture
def mock_mongo_collections():
    """Mocka as coleções do MongoDB usadas no services.py."""
    with (
        patch("nsnapp.services.project_collections") as mock_projects,
        patch("nsnapp.services.users_collection") as mock_users,
        patch("nsnapp.services.developer_rates_collection") as mock_rates,
    ):
        # Simula o drop para que não dê erro nas chamadas
        mock_projects.database.list_collection_names.return_value = [
            "projects_per_hours"
        ]
        yield {
            "projects": mock_projects,
            "users": mock_users,
            "rates": mock_rates,
        }


@pytest.fixture
def mock_convert_time():
    """Mocka a função de utilidade para conversão de tempo."""
    with patch(
        "nsnapp.services.convert_time_to_minutes", return_value=120
    ) as mock_convert:
        # Definido como 120 (minutos) para simular o "2h" do Log 2
        yield mock_convert


@pytest.fixture
def mock_get_project_by_period():
    """Mocka a função get_project_by_period para a agregação."""
    project_data = [
        {
            "_id": ObjectId("60d5ec49e7b3c1a2e3f4d5c6"),
            "id": "10000",
            "key": "SE",
            "name": "Project Alpha",
            "issues": [
                {
                    "issue_id": "10001",
                    "issue_key": "SE-1",
                    "author_logs": [
                        # Log 1: Pessoa selecionada, time_spent_seconds (3600s = 60 min)
                        {
                            "account_id": "author-A",
                            "display_name": "Dev A",
                            "jira_created_at": datetime(2025, 10, 15),
                            "time_spent": "1h",
                            "time_spent_seconds": 3600,
                        },
                        # Log 2: Outro autor. REMOVIDO time_spent_seconds para FORÇAR O USO DE convert_time_to_minutes
                        {
                            "account_id": "author-B",
                            "display_name": "Dev B",
                            "jira_created_at": datetime(2025, 10, 16),
                            "time_spent": "2h",
                        },
                    ],
                }
            ],
        }
    ]
    with patch("nsnapp.services.get_project_by_period") as mock_get:
        mock_get.return_value = project_data
        yield mock_get


# --- Testes de Funções Auxiliares ---


def test_extract_account_ids_should_return_correct_list():
    authors_list = [
        {"account_id": "id1", "name": "User 1"},
        {"account_id": "id2", "name": "User 2"},
        {"no_id_field": "test"},
        "not_a_dict",
    ]
    expected = ["id1", "id2"]
    assert extract_account_ids(authors_list) == expected


def test_clean_data_should_format_correctly():
    project = {"id": "proj-id", "key": "PROJ", "name": "Project Name"}
    issue = {
        "id": "issue-id",
        "key": "PROJ-1",
        "fields": {
            "worklog": {
                "worklogs": [
                    {
                        "author": {"accountId": "dev-A", "displayName": "Dev A"},
                        "created": "2025-10-20T10:00:00.000+0000",
                        "timeSpent": "1h",
                        "timeSpentSeconds": 3600,
                    }
                ]
            }
        },
    }
    expected = {
        "id": "proj-id",
        "key": "PROJ",
        "name": "Project Name",
        "issues": [
            {
                "issue_id": "issue-id",
                "issue_key": "PROJ-1",
                "author_logs": [
                    {
                        "account_id": "dev-A",
                        "display_name": "Dev A",
                        "jira_created_at": datetime(2025, 10, 20, 10, 0, 0),
                        "time_spent": "1h",
                        "time_spent_seconds": 3600,
                    }
                ],
            }
        ],
    }
    assert clean_data(project, issue) == expected


def test_filther_data_should_keep_only_target_author():
    data = {
        "id": "proj-id",
        "issues": [
            {
                "issue_id": "i1",
                "author_logs": [
                    {"account_id": "target-A", "time_spent": "1h"},
                    {"account_id": "other-B", "time_spent": "2h"},
                ],
            },
            {
                "issue_id": "i2",
                "author_logs": [
                    {"account_id": "target-A", "time_spent": "3h"},
                ],
            },
        ],
    }
    author_id = "target-A"
    filtered = filther_data(data, author_id)

    assert len(filtered["issues"][0]["author_logs"]) == 1
    assert filtered["issues"][0]["author_logs"][0]["account_id"] == author_id
    assert len(filtered["issues"][1]["author_logs"]) == 1
    assert filtered["issues"][1]["author_logs"][0]["account_id"] == author_id
    # Garante que a função está modificando o objeto in-place (ou uma cópia se o chamador usar deepcopy)
    assert filtered is data


# --- Testes de Interação com MongoDB (Buscas) ---


def test_get_project_by_period_should_call_find_with_correct_dates(
    mock_mongo_collections,
):
    mock_projects = mock_mongo_collections["projects"]
    mock_projects.find.return_value = ["proj1", "proj2"]

    begin = "2025-01-01"
    end = "2025-01-31"

    result = get_project_by_period(begin, end)

    assert result == ["proj1", "proj2"]

    expected_begin = datetime(2025, 1, 1)
    # end_formated é 2025-02-01 00:00:00 - 1 segundo = 2025-01-31 23:59:59
    expected_end = datetime(2025, 1, 31, 23, 59, 59)

    mock_projects.find.assert_called_once()
    query = mock_projects.find.call_args[0][0]

    assert (
        query["issues"]["$elemMatch"]["author_logs"]["$elemMatch"]["jira_created_at"][
            "$gte"
        ]
        == expected_begin
    )
    assert (
        query["issues"]["$elemMatch"]["author_logs"]["$elemMatch"]["jira_created_at"][
            "$lte"
        ]
        == expected_end
    )


def test_get_project_by_author_should_call_find_with_correct_accountId(
    mock_mongo_collections,
):
    mock_projects = mock_mongo_collections["projects"]
    mock_projects.find.return_value = ["projA", "projB"]

    account_id = "test-author-id"
    result = get_project_by_author(account_id)

    assert result == ["projA", "projB"]

    mock_projects.find.assert_called_once_with(
        {
            "issues": {
                "$elemMatch": {
                    "author_logs": {"$elemMatch": {"account_id": account_id}}
                }
            }
        }
    )


# --- Teste de Agregação de Período e Autor ---


def test_aggregate_project_periods_and_authors_should_calculate_minutes_correctly(
    mock_get_project_by_period, mock_convert_time
):
    begin = "2025-10-01"
    end = "2025-10-31"
    authors = [{"account_id": "author-A"}]  # author-A é selecionado

    # Log 1 (author-A): 3600s = 60 minutos
    # Log 2 (author-B): "2h" -> mock_convert_time retorna 120 minutos

    # Total equipe: Log 1 (60) + Log 2 (120) = 180
    # Pessoas selecionadas (author-A): Log 1 (60) = 60

    result = aggregate_project_periods_and_authors(begin, end, authors)

    assert result["toda_equipe"] == [
        {"nome_projeto": "Project Alpha", "minutos_projeto": 180}
    ]
    assert result["pessoas_selecionadas"] == [
        {"nome_projeto": "Project Alpha", "minutos_projeto": 60}
    ]
    # Agora assert_called_once_with funcionará, pois o campo time_spent_seconds foi removido do mock
    mock_convert_time.assert_called_once_with("2h")


# --- Teste de Taxas de Desenvolvedor ---


def test_save_developer_rates_service_success(mock_mongo_collections):
    mock_rates = mock_mongo_collections["rates"]
    mock_rates.bulk_write.return_value = MagicMock(
        upserted_count=1, inserted_count=0, modified_count=1
    )

    data = [
        {"id_desenvolvedor": "dev1", "valor_por_hora": 50.0},
        {
            "id_desenvolvedor": "dev2",
            "valor_por_hora": "65",
        },  # Testando string numérica
    ]

    result = save_developer_rates_service(data)

    mock_rates.delete_many.assert_called_once_with({})
    mock_rates.bulk_write.assert_called_once()

    assert result["inserted"] == 1
    assert result["modified"] == 1
    assert (
        result["message"] == "Taxas de desenvolvedores salvas/atualizadas com sucesso."
    )


def test_save_developer_rates_service_empty_data_raises_error(mock_mongo_collections):
    data = []
    result = save_developer_rates_service(data)
    assert result["message"] == "Nenhum dado fornecido para salvar."


def test_save_developer_rates_service_invalid_data_raises_valueerror():
    # Teste para dado faltando
    with pytest.raises(
        ValueError, match="Cada objeto deve ter 'id_desenvolvedor' e 'valor_por_hora'."
    ):
        save_developer_rates_service([{"id_desenvolvedor": "dev1"}])

    # Teste para valor_por_hora inválido
    with pytest.raises(
        ValueError, match="O campo 'valor_por_hora' deve ser um número válido."
    ):
        save_developer_rates_service(
            [{"id_desenvolvedor": "dev1", "valor_por_hora": "invalid"}]
        )


def test_list_developer_rates_service_success(mock_mongo_collections):
    mock_rates = mock_mongo_collections["rates"]

    # Simula o retorno do aggregate já projetado
    expected_result_from_pipeline = [
        {
            "id_desenvolvedor": "dev1",
            "valor_por_hora": 50.0,
            "ultima_atualizacao": "2025-10-20T00:00:00",
            "nome_desenvolvedor": "Dev A",
        }
    ]

    with patch.object(
        mock_rates, "aggregate", return_value=expected_result_from_pipeline
    ) as mock_aggregate:
        result = list_developer_rates_service()

    assert result == expected_result_from_pipeline
    mock_aggregate.assert_called_once()


# --- Teste de Listagem de Projetos ---


def test_list_projects_service_success(mock_mongo_collections):
    mock_projects = mock_mongo_collections["projects"]

    # Simula o retorno da agregação (que já formata o output)
    expected_projects = [
        {"id": "10000", "name": "Project Alpha"},
        {"id": "10001", "name": "Project Beta"},
    ]
    with patch.object(
        mock_projects, "aggregate", return_value=expected_projects
    ) as mock_aggregate:
        result = list_projects_service()

    assert result == expected_projects
    mock_aggregate.assert_called_once()


# --- Teste de Contagem de Issues e Horas ---


def test_count_issues_by_user_and_total_hours_service_no_project_id(
    mock_mongo_collections,
):
    mock_projects = mock_mongo_collections["projects"]

    # Simula o resultado da agregação com os campos finais
    expected_result = [
        {
            "nome": "Dev B",
            "quantidade_issues": 1,
            "total_horas": 3.0,
            "valor_por_hora": 30.0,
            "custo_total": 90.0,
        },
        {
            "nome": "Dev A",
            "quantidade_issues": 2,
            "total_horas": 5.5,
            "valor_por_hora": None,
            "custo_total": None,
        },
    ]
    with patch.object(
        mock_projects, "aggregate", return_value=expected_result
    ) as mock_aggregate:
        result = count_issues_by_user_and_total_hours_service(project_id=None)

    assert result == expected_result
    mock_aggregate.assert_called_once()
    # CORRIGIDO: O pipeline sem $match tem 9 passos.
    assert len(mock_aggregate.call_args[0][0]) == 9


def test_count_issues_by_user_and_total_hours_service_with_project_id(
    mock_mongo_collections,
):
    mock_projects = mock_mongo_collections["projects"]

    project_id = "10001"

    expected_result = [
        {
            "nome": "Dev C",
            "quantidade_issues": 1,
            "total_horas": 2.0,
            "valor_por_hora": 45.0,
            "custo_total": 90.0,
        },
    ]
    with patch.object(
        mock_projects, "aggregate", return_value=expected_result
    ) as mock_aggregate:
        result = count_issues_by_user_and_total_hours_service(project_id=project_id)

    assert result == expected_result
    mock_aggregate.assert_called_once()
    # CORRIGIDO: O pipeline com $match tem 10 passos.
    pipeline = mock_aggregate.call_args[0][0]
    assert len(pipeline) == 10
    # Verifica se o $match inicial está correto
    assert pipeline[0] == {"$match": {"id": project_id}}
