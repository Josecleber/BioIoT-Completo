"""Testes sem modificar o banco SQLite ou o ESP32."""
import json
import unittest
from pathlib import Path
from api_ia import analisar_janela

BASE = Path(__file__).resolve().parent


class TestesAPI(unittest.TestCase):
    def test_janela_constante_valida(self):
        amostras = [{'segundo': i, 'pulse': 80, 'spo2': 98} for i in range(60)]
        resposta = analisar_janela(amostras)
        self.assertEqual(resposta['status'], 'analisado')
        self.assertEqual(resposta['caracteristicas']['pulse_media'], 80)
        self.assertEqual(resposta['caracteristicas']['spo2_media'], 98)
        self.assertNotIn('diagnostico', resposta)

    def test_rejeita_lacuna(self):
        a = [{'segundo': i, 'pulse': 80, 'spo2': 98} for i in range(60)]
        a[27]['segundo'] = 28
        with self.assertRaises(ValueError):
            analisar_janela(a)

    def test_rejeita_dedo_ausente(self):
        a = [{'segundo': i, 'pulse': 80, 'spo2': 98} for i in range(60)]
        a[10]['pulse'] = 0
        with self.assertRaises(ValueError):
            analisar_janela(a)

    def test_rejeita_nao_numerico(self):
        a = [{'segundo': i, 'pulse': 80, 'spo2': 98} for i in range(60)]
        a[10]['spo2'] = None
        with self.assertRaises(ValueError):
            analisar_janela(a)

    def test_catalogo_bidmc_12(self):
        caminho = BASE / 'resultados' / 'catalogo_interativo.json'
        if not caminho.exists():
            self.skipTest('Catálogo histórico indisponível localmente.')
        catalogo = json.loads(caminho.read_text(encoding='utf-8'))
        caso = next(c for c in catalogo['casos'] if c['arquivo'] == 'bidmc_12_Numerics.csv')
        resultado = analisar_janela(caso['serie_temporal'])
        self.assertAlmostEqual(resultado['score'], caso['score'], places=5)
        self.assertEqual(resultado['padrao_atipico'], True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
