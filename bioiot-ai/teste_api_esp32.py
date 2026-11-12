import unittest

from api_ia import analisar_janela_esp32


def criar_amostras():
    return [
        {
            "segundo": round(i * (59 / 27), 6),
            "pulse": 80 + (i % 5),
            "spo2": 98,
        }
        for i in range(28)
    ]


class TestesESP32(unittest.TestCase):

    def test_janela_valida(self):
        resultado = analisar_janela_esp32(criar_amostras())

        self.assertEqual(resultado["status"], "analisado")
        self.assertEqual(resultado["amostras"], 28)
        self.assertEqual(resultado["modelo"], "isolation_forest_esp32")
        self.assertFalse(resultado["avaliacao_clinica"])

    def test_rejeita_lacuna(self):
        amostras = criar_amostras()
        amostras[10]["segundo"] += 5

        with self.assertRaises(ValueError):
            analisar_janela_esp32(amostras)

    def test_rejeita_dedo_ausente(self):
        amostras = criar_amostras()
        amostras[10]["pulse"] = 0

        with self.assertRaises(ValueError):
            analisar_janela_esp32(amostras)

    def test_rejeita_valor_nao_numerico(self):
        amostras = criar_amostras()
        amostras[10]["spo2"] = None

        with self.assertRaises(ValueError):
            analisar_janela_esp32(amostras)


if __name__ == "__main__":
    unittest.main(verbosity=2)
