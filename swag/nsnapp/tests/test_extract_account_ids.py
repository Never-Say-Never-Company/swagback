import unittest
from nsnapp.views import extract_account_ids


class TestExtractAccountIds(unittest.TestCase):
    
    def test_basic_extraction(self):
        """Testa a extração padrão com dados válidos."""
        authors = [
            {'account_id': 'user_a123', 'display_name': 'Alice'},
            {'account_id': 'user_b456', 'display_name': 'Bob'},
        ]
        expected = ['user_a123', 'user_b456']
        self.assertEqual(extract_account_ids(authors), expected)

    def test_handles_missing_account_id(self):
        """Testa que autores sem 'account_id' são ignorados."""
        authors = [
            {'account_id': 'user_c789', 'display_name': 'Charlie'},
            {'display_name': 'Ignored User'},  # Falta 'account_id'
            {'account_id': 'user_d012', 'display_name': 'David'},
        ]
        expected = ['user_c789', 'user_d012']
        self.assertEqual(extract_account_ids(authors), expected)

    def test_handles_invalid_types(self):
        """Testa que elementos que não são dicionários (como strings ou None) são ignorados."""
        authors = [
            {'account_id': 'user_e345'},
            "isso é uma string",  # Não é dict
            None,                 # Não é dict
            {'account_id': 'user_f678'},
        ]
        expected = ['user_e345', 'user_f678']
        self.assertEqual(extract_account_ids(authors), expected)

    def test_empty_list(self):
        """Testa uma lista de entrada vazia."""
        self.assertEqual(extract_account_ids([]), [])

    def test_list_with_empty_dictionaries(self):
        """Testa uma lista contendo dicionários vazios."""
        authors = [{}, {}, {'account_id': 'final_user'}]
        expected = ['final_user']
        self.assertEqual(extract_account_ids(authors), expected)

# Para executar os testes
if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)