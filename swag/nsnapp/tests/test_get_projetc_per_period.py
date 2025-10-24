import json
from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from unittest.mock import patch, MagicMock
from nsnapp.views import get_project_per_period 

PATCH_PATH_GET_PERIOD = 'nsnapp.views.get_project_by_period'
PATCH_PATH_CONVERT = 'nsnapp.views.convert_objectid_to_str'

class GetProjectPerPeriodViewTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        
        self.valid_data = {'begin': '2025-01-01', 'end': '2025-01-31'}
        self.mock_db_result = [{'project_id': 1, '_id': '111'}, {'project_id': 2, '_id': '222'}]
        self.mock_converted_result = [{'project_id': 1, 'id_str': '111'}, {'project_id': 2, 'id_str': '222'}]

    @patch(PATCH_PATH_CONVERT)
    @patch(PATCH_PATH_GET_PERIOD)
    def test_post_success(self, mock_get_project_by_period, mock_convert_objectid_to_str):
        """Testa uma requisição POST válida e verifica o retorno e as chamadas das funções."""
        
        mock_get_project_by_period.return_value = self.mock_db_result
        mock_convert_objectid_to_str.return_value = self.mock_converted_result

        request = self.factory.post(
            '/mock-path/', 
            json.dumps(self.valid_data), 
            content_type='application/json'
        )
        
        response = get_project_per_period(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), self.mock_converted_result)

        mock_get_project_by_period.assert_called_once_with(self.valid_data['begin'], self.valid_data['end'])
        mock_convert_objectid_to_str.assert_called_once_with(list(self.mock_db_result))


    def test_non_post_method(self):
        """Testa que a view retorna um erro ou permite que o Django retorne 'Method Not Allowed' para métodos não-POST."""

        request = self.factory.get('/mock-path/')
        response = get_project_per_period(request)
        
        self.assertIsNone(response)


    # @patch(PATCH_PATH_GET_PERIOD) 
    # def test_invalid_json_decode_error(self, mock_get_project_by_period):
    #     """Testa o bloco except json.JSONDecodeError."""
    #     request = self.factory.post(
    #         '/mock-path/', 
    #         b'isto nao e json valido', 
    #         content_type='application/json'
    #     )
    #     response = get_project_per_period(request)
    #     self.assertEqual(response.status_code, 400)
    #     self.assertIn("JSON inválido", response.content.decode())
    #     mock_get_project_by_period.assert_not_called()

    # @patch(PATCH_PATH_GET_PERIOD) 
    # def test_missing_required_fields(self, mock_get_project_by_period):
    #     """Testa a validação de 'begin' e 'end'."""
        
    #     data_missing_end = json.dumps({'begin': '2025-01-01'})
    #     request = self.factory.post('/mock-path/', data_missing_end, content_type='application/json')
    #     response = get_project_per_period(request)
    #     self.assertEqual(response.status_code, 400)
    #     self.assertIn("Necessário ter 'begin' e 'end'", response.content.decode())
    #     mock_get_project_by_period.assert_not_called()
        
    #     data_missing_begin = json.dumps({'end': '2025-01-31'})
    #     request = self.factory.post('/mock-path/', data_missing_begin, content_type='application/json')
    #     response = get_project_per_period(request)
    #     self.assertEqual(response.status_code, 400)
    #     mock_get_project_by_period.assert_not_called()

    @patch(PATCH_PATH_CONVERT)
    @patch(PATCH_PATH_GET_PERIOD)
    def test_data_is_list(self, mock_get_project_by_period, mock_convert_objectid_to_str):
        """Testa o caso em que o payload é uma lista de um item e o item é usado."""
        
        mock_get_project_by_period.return_value = self.mock_db_result
        mock_convert_objectid_to_str.return_value = self.mock_converted_result

        list_payload = [self.valid_data]
        request = self.factory.post(
            '/mock-path/', 
            json.dumps(list_payload), 
            content_type='application/json'
        )
        response = get_project_per_period(request)

        self.assertEqual(response.status_code, 200)
        mock_get_project_by_period.assert_called_once_with(self.valid_data['begin'], self.valid_data['end'])

    @patch(PATCH_PATH_GET_PERIOD)
    def test_internal_exception(self, mock_get_project_by_period):
        """Testa o bloco except Exception geral (erro interno)"""
        
        mock_get_project_by_period.side_effect = Exception("Erro de conexão com o banco de dados")
        
        request = self.factory.post(
            '/mock-path/', 
            json.dumps(self.valid_data), 
            content_type='application/json'
        )
        response = get_project_per_period(request)
        
        self.assertEqual(response.status_code, 500)
        self.assertIn("Erro de conexão com o banco de dados", response.content.decode())

if __name__ == '__main__':
    unittest.main()