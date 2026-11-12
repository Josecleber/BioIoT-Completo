"""BioIoT AI - API experimental de inferência, sem diagnóstico.

Recebe uma janela de 60 amostras em segundos consecutivos (1 Hz).
Não faz interpolação e não dispara alarmes clínicos.
"""

import json
import math
import os
import statistics
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import joblib
import numpy as np

BASE = Path(__file__).resolve().parent
ARQUIVO_MODELO = BASE / "modelos" / "bioiot_isolation_forest.joblib"
ARTEFATO = joblib.load(ARQUIVO_MODELO)
MODELO = ARTEFATO["modelo"]
COLUNAS = ARTEFATO["colunas"]
LIMIAR = float(ARTEFATO["limiar"])
TAMANHO = int(ARTEFATO.get("tamanho_janela_segundos", 60))


def analisar_janela(amostras):
    if not isinstance(amostras, list) or len(amostras) != TAMANHO:
        raise ValueError(f"Esperadas {TAMANHO} amostras consecutivas a 1 Hz.")
    pulsos, spo2s, tempos = [], [], []
    for i, a in enumerate(amostras):
        if not isinstance(a, dict):
            raise ValueError("Amostra precisa ser um objeto.")
        t, p, s = a.get("segundo"), a.get("pulse"), a.get("spo2")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (t, p, s)):
            raise ValueError("Há campo ausente, NaN ou valor não numérico.")
        if not (40 <= p <= 160 and 75 <= s <= 100):
            raise ValueError("Leitura fora dos limites técnicos de entrada do sensor.")
        if not math.isclose(t, i, abs_tol=1e-6):
            raise ValueError(
                "Tempo irregular: são exigidas amostras consecutivas de 1 segundo."
            )
        tempos.append(t)
        pulsos.append(p)
        spo2s.append(s)

    def features(v, prefixo):
        return {
            f"{prefixo}_media": round(statistics.mean(v), 5),
            f"{prefixo}_desvio": round(statistics.pstdev(v), 5),
            f"{prefixo}_minimo": min(v),
            f"{prefixo}_maximo": max(v),
            f"{prefixo}_amplitude": round(max(v) - min(v), 5),
            f"{prefixo}_tendencia": round((v[-1] - v[0]) / (len(v) - 1), 5),
        }

    carac = {**features(pulsos, "pulse"), **features(spo2s, "spo2")}
    matriz = np.asarray([[carac[c] for c in COLUNAS]], dtype=np.float64)
    score = float(MODELO.score_samples(matriz)[0])
    return {
        "status": "analisado",
        "tipo": "analise_estatistica_experimental",
        "padrao_atipico": score < LIMIAR,
        "score": score,
        "limiar": LIMIAR,
        "janela_segundos": TAMANHO,
        "caracteristicas": carac,
        "mensagem": "Pontuação estatística relativa aos dados de treinamento; não é diagnóstico nem probabilidade clínica.",
    }


ARQUIVO_MODELO_ESP32 = BASE / "modelos" / "bioiot_isolation_forest_esp32.joblib"

ARTEFATO_ESP32 = joblib.load(ARQUIVO_MODELO_ESP32)

MODELO_ESP32 = ARTEFATO_ESP32["modelo"]
COLUNAS_ESP32 = ARTEFATO_ESP32["colunas"]
LIMIAR_ESP32 = float(ARTEFATO_ESP32["limiar"])
TAMANHO_ESP32 = int(ARTEFATO_ESP32["quantidade_amostras"])


def analisar_janela_esp32(amostras):
    if not isinstance(amostras, list) or len(amostras) != TAMANHO_ESP32:
        raise ValueError(f"Esperadas {TAMANHO_ESP32} amostras reais.")

    pulsos = []
    spo2s = []
    tempos = []

    for amostra in amostras:
        if not isinstance(amostra, dict):
            raise ValueError("Amostra inválida.")

        t = amostra.get("segundo")
        p = amostra.get("pulse")
        s = amostra.get("spo2")

        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (t, p, s)):
            raise ValueError("Valor ausente ou não numérico.")

        if not (40 <= p <= 160 and 75 <= s <= 100):
            raise ValueError("Leitura fora dos limites técnicos.")

        tempos.append(t)
        pulsos.append(p)
        spo2s.append(s)

    if not math.isclose(tempos[0], 0, abs_tol=0.01):
        raise ValueError("O tempo inicial deve ser zero.")

    intervalos = [tempos[i] - tempos[i - 1] for i in range(1, len(tempos))]

    if any(not 1.7 <= intervalo <= 2.9 for intervalo in intervalos):
        raise ValueError("Intervalos de medição incompatíveis ou com lacunas.")

    duracao = tempos[-1] - tempos[0]

    if not 55 <= duracao <= 65:
        raise ValueError("Duração incompatível com a janela experimental.")

    def features(valores, prefixo):
        return {
            f"{prefixo}_media": round(statistics.mean(valores), 5),
            f"{prefixo}_desvio": round(statistics.pstdev(valores), 5),
            f"{prefixo}_minimo": min(valores),
            f"{prefixo}_maximo": max(valores),
            f"{prefixo}_amplitude": round(max(valores) - min(valores), 5),
            f"{prefixo}_tendencia": round(
                (valores[-1] - valores[0]) / (len(valores) - 1), 5
            ),
        }

    caracteristicas = {
        **features(pulsos, "pulse"),
        **features(spo2s, "spo2"),
    }

    matriz = np.asarray([[caracteristicas[c] for c in COLUNAS_ESP32]], dtype=np.float64)

    score = float(MODELO_ESP32.score_samples(matriz)[0])

    return {
        "status": "analisado",
        "tipo": "analise_estatistica_experimental_esp32",
        "modelo": "isolation_forest_esp32",
        "padrao_atipico": score < LIMIAR_ESP32,
        "score": score,
        "limiar": LIMIAR_ESP32,
        "amostras": TAMANHO_ESP32,
        "duracao_real_segundos": round(duracao, 3),
        "intervalo_medio_segundos": round(statistics.mean(intervalos), 3),
        "caracteristicas": caracteristicas,
        "avaliacao_clinica": False,
        "mensagem": (
            "Análise estatística experimental. "
            "Não é diagnóstico nem probabilidade clínica."
        ),
    }


class Handler(BaseHTTPRequestHandler):
    def responder(self, status, obj):
        corpo = json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path == "/health":
            self.responder(
                200,
                {
                    "status": "ok",
                    "modelo_carregado": True,
                    "janela_segundos": TAMANHO,
                    "avaliacao_clinica": False,
                },
            )
        else:
            self.responder(404, {"erro": "Rota desconhecida."})

    def do_POST(self):

        if self.path not in ("/analisar", "/analisar-esp32"):
            self.responder(404, {"erro": "Rota desconhecida."})
            return

        try:
            tamanho = int(self.headers.get("Content-Length", "-1"))
            if not 0 < tamanho <= 20000:
                self.responder(413, {"erro": "Corpo ausente ou grande demais."})
                return
            payload = json.loads(self.rfile.read(tamanho))
            if not isinstance(payload, dict):
                raise ValueError("Corpo JSON deve ser objeto.")

            if self.path == "/analisar-esp32":
                resultado = analisar_janela_esp32(payload.get("amostras"))
            else:
                resultado = analisar_janela(payload.get("amostras"))

            self.responder(200, resultado)
        except (ValueError, TypeError, json.JSONDecodeError) as erro:
            self.responder(
                422, {"status": "dados_insuficientes_ou_invalidos", "erro": str(erro)}
            )
        except Exception:
            self.responder(500, {"erro": "Falha interna na inferência."})


if __name__ == "__main__":
    porta = int(os.environ.get("BIOIOT_AI_PORT", "8001"))
    servidor = ThreadingHTTPServer(("0.0.0.0", porta), Handler)
    print(
        f"[BIOIOT AI] API pronta na porta {porta}; resultados experimentais.",
        flush=True,
    )
    servidor.serve_forever()
