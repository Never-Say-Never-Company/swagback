import unittest
import json
from unittest.mock import patch, MagicMock
from nsnapp.views import count_issues_grouped_by_project 
from django.http import HttpRequest, JsonResponse


class TestIssueCounter(unittest.TestCase):

    def test_01_method_not_allowed(self):
        mock_request = HttpRequest()
        mock_request.method = 'POST'
        
        response = count_issues_grouped_by_project(mock_request)
        
        self.assertEqual(response.status_code, 405)
        
        expected_data = {"error": "Método não permitido. Use GET."}
        content = json.loads(response.content)
        self.assertEqual(content, expected_data)

    @patch('nsnapp.views.MongoClient')
    @patch('nsnapp.views.config')
    def test_02_successful_aggregation(self, mock_config, mock_mongo_client):
        
        mock_config.return_value = 'mongodb://db:27017/swag'
        
        mock_aggregation_results = [
            {"_id": "SM2", "issue_count": 68},
            {"_id": "SE", "issue_count": 11},
        ]

        # Configuração do Mocking Encadeado (CORRIGIDO)
        mock_project_collections = MagicMock()
        mock_project_collections.aggregate.return_value = mock_aggregation_results
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_project_collections
        
        mock_client = mock_mongo_client.return_value
        mock_client.__getitem__.return_value = mock_db

        # Preparação da Requisição e Execução
        mock_request = HttpRequest()
        mock_request.method = 'GET'
        
        response = count_issues_grouped_by_project(mock_request)
        
        # Verificações
        self.assertEqual(response.status_code, 200)
        
        expected_data = [
            {"projeto": "SM2", "quantidade_issues": 68},
            {"projeto": "SE", "quantidade_issues": 11},
        ]
        
        content = json.loads(response.content)
        self.assertEqual(content, expected_data)

        mock_mongo_client.assert_called_once_with('mongodb://db:27017/swag')
        mock_project_collections.aggregate.assert_called_once()
    
    @patch('nsnapp.views.MongoClient')
    @patch('nsnapp.views.config')
    def test_03_database_exception_handling(self, mock_config, mock_mongo_client):
        
        mock_config.return_value = 'dummy_mongo_path_from_config'
        
        # Força o MongoClient a levantar um erro (simula falha de conexão ou DB)
        simulated_error_message = "Connection refused by host"
        mock_mongo_client.side_effect = Exception(simulated_error_message)
        
        mock_request = HttpRequest()
        mock_request.method = 'GET'

        response = count_issues_grouped_by_project(mock_request)
        
        self.assertEqual(response.status_code, 500)
        
        content = json.loads(response.content)
        
        self.assertIn("Falha ao contar issues por projeto:", content["error"])
        self.assertIn(simulated_error_message, content["error"])

if __name__ == '__main__':
    unittest.main()