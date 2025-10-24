import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime


from nsnapp.services import save_developer_rates_service 
from pymongo.operations import ReplaceOne 


MOCK_DATE = datetime(2025, 1, 1, 10, 0, 0)

class DeveloperRatesServiceTest(unittest.TestCase):

    
    
    

    
    @patch('nsnapp.services.developer_rates_collection')
    
    @patch('nsnapp.services.datetime')
    
    
    @patch('nsnapp.services.ReplaceOne')
    def test_01_save_developer_rates_success(self, MockReplaceOne, MockDatetime, MockCollection):
        """
        Testa o sucesso na inserção/atualização de taxas, verificando se
        o bulk_write é chamado com as operações corretas.
        """
        
        
        MockDatetime.now.return_value = MOCK_DATE
        MockDatetime.datetime = datetime 
        
        
        mock_result = MagicMock()
        mock_result.upserted_count = 2 
        mock_result.inserted_count = 0 
        mock_result.modified_count = 1 
        MockCollection.bulk_write.return_value = mock_result
        
        
        
        operacao_mockada = MagicMock()
        MockReplaceOne.side_effect = [operacao_mockada] * 3 

        
        data = [
            {"id_desenvolvedor": "dev_novo_1", "valor_por_hora": 50.0},
            {"id_desenvolvedor": "dev_novo_2", "valor_por_hora": 75.25},
            {"id_desenvolvedor": "dev_existente_3", "valor_por_hora": 40.0}
        ]

        
        resultado = save_developer_rates_service(data)

        

        
        MockCollection.bulk_write.assert_called_once()
        
        
        self.assertEqual(MockReplaceOne.call_count, 3)

        
        primeira_chamada = MockReplaceOne.call_args_list[0]
        
        
        
        
        
        filtro = primeira_chamada.kwargs['filter']
        self.assertEqual(filtro, {'id_desenvolvedor': 'dev_novo_1'})
        
        
        replacement = primeira_chamada.kwargs['replacement']
        self.assertEqual(replacement['valor_por_hora'], 50.0)
        self.assertEqual(replacement['ultima_atualizacao'], MOCK_DATE)
        
        
        self.assertTrue(primeira_chamada.kwargs['upsert'])


        
        self.assertEqual(resultado["inserted"], 2) 
        self.assertEqual(resultado["modified"], 1)

    
    
    

    def test_02_save_developer_rates_invalid_rate(self):
        """Testa se a função levanta ValueError quando o valor_por_hora é inválido."""
        data = [
            {"id_desenvolvedor": "dev_1", "valor_por_hora": "quarenta"}, 
        ]

        with self.assertRaisesRegex(ValueError, "O campo 'valor_por_hora' deve ser um número válido."):
            save_developer_rates_service(data)

    def test_03_save_developer_rates_missing_field(self):
        """Testa se a função levanta ValueError quando o campo é faltante."""
        data = [
            {"id_desenvolvedor": "dev_1", "valor_por_hora": 50.0},
            {"id_desenvolvedor": "dev_2"}, 
        ]

        with self.assertRaisesRegex(ValueError, "Cada objeto deve ter 'id_desenvolvedor' e 'valor_por_hora'."):
            save_developer_rates_service(data)

    
    
    

    @patch('nsnapp.services.developer_rates_collection')
    def test_04_save_developer_rates_empty_list(self, MockCollection):
        """Testa se a função lida corretamente com uma lista vazia."""
        
        data = []
        resultado = save_developer_rates_service(data)

        MockCollection.bulk_write.assert_not_called() 
        
        self.assertEqual(resultado["inserted"], 0)
        self.assertEqual(resultado["modified"], 0)
        self.assertIn("Nenhum dado fornecido", resultado["message"])

if __name__ == '__main__':
    unittest.main()