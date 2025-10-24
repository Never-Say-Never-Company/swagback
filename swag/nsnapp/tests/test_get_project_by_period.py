import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Importa a função a ser testada
from nsnapp.views import get_project_by_period

# O caminho para o patch deve ser onde a variável global project_collections está definida
# ASSUMINDO que está definida em nsnapp/views.py. Se estiver em outro lugar, ajuste o caminho.
PATCH_PATH = 'nsnapp.views.project_collections'


@patch(PATCH_PATH) # Aplica o mock na variável dentro do módulo views
class TestGetProjectByPeriod(unittest.TestCase):

    def setUp(self):
        # Dados mockados para o retorno do find
        self.mock_results = [{"project": "P1"}, {"project": "P2"}]

    # O mock injetado é o primeiro argumento (mock_collection)
    def test_date_formatting_and_query_call(self, mock_collection):
        """Testa se as datas são formatadas corretamente e se o 'find' é chamado com a query certa."""
        
        # Configura o mock retornado pelo .find()
        mock_collection.find.return_value = self.mock_results
        
        begin_str = "2025-10-01"
        end_str = "2025-10-31"

        begin_expected = datetime(2025, 10, 1)
        end_expected = datetime(2025, 10, 31, 23, 59, 59) 

        result = get_project_by_period(begin_str, end_str)

        self.assertEqual(result, self.mock_results)
        
        # Verifica a chamada no objeto mock injetado
        mock_collection.find.assert_called_once()

        actual_query = mock_collection.find.call_args[0][0]

        expected_query = {
            "issues": {
                "$elemMatch": {
                    "author_logs": {
                        "$elemMatch": {
                            "jira_created_at": {
                                "$gte": begin_expected,
                                "$lte": end_expected
                            }
                        }
                    }
                }
            }
        }
        
        self.assertEqual(actual_query, expected_query)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)