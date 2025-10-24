import unittest
# Importa a função diretamente do módulo onde ela reside
# OBS: O re é usado dentro da função, então ele não precisa ser importado aqui.
from nsnapp.views import convert_time_to_minutes 
# ou, se a função estiver em outro arquivo, por exemplo:
# from nsnapp.utils import convert_time_to_minutes 

class TestConvertTimeToMinutes(unittest.TestCase):
    

    def test_hours_and_minutes(self):

        self.assertEqual(convert_time_to_minutes("3h 26m"), 206)

        self.assertEqual(convert_time_to_minutes("10h 0m"), 600)

    def test_only_hours(self):
        self.assertEqual(convert_time_to_minutes("1h"), 60)
        self.assertEqual(convert_time_to_minutes("24h"), 1440)

    def test_only_minutes(self):
        self.assertEqual(convert_time_to_minutes("45m"), 45)
        self.assertEqual(convert_time_to_minutes("90m"), 90)


    
    def test_varied_spacing_and_order(self):

        self.assertEqual(convert_time_to_minutes(" 2 h 5 m "), 125)

        self.assertEqual(convert_time_to_minutes("1h65m"), 125)

        self.assertEqual(convert_time_to_minutes("5m 2h"), 125)


    
    def test_empty_and_invalid_input(self):
        # String vazia
        self.assertEqual(convert_time_to_minutes(""), 0)
        # Apenas um valor numérico sem 'h' ou 'm'
        self.assertEqual(convert_time_to_minutes("100"), 0)
        # String aleatória
        self.assertEqual(convert_time_to_minutes("abc"), 0)
        # Zero horas e zero minutos
        self.assertEqual(convert_time_to_minutes("0h 0m"), 0)

# Para executar os testes (se rodado diretamente)
if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)