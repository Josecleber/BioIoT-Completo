import csv
import json
import math
import random
import statistics
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

BASE = Path(__file__).resolve().parent
DADOS = BASE / "dados" / "bidmc"
MODELOS = BASE / "modelos"
RESULTADOS = BASE / "resultados"

MODELOS.mkdir(exist_ok=True)
RESULTADOS.mkdir(exist_ok=True)

# Aproximadamente 60 segundos com 28 leituras.
AMOSTRAS = 28
DURACAO = 60
SEMENTE = 42

# Seleciona 28 posições dentro dos 60 segundos,
# sem repetir amostras nem interpolar valores.
POSICOES = [round(i * 59 / (AMOSTRAS - 1)) for i in range(AMOSTRAS)]

COLUNAS = [
    f"{prefixo}_{metrica}"
    for prefixo in ("pulse", "spo2")
    for metrica in ("media", "desvio", "minimo", "maximo", "amplitude", "tendencia")
]


def numero(valor):
    try:
        resultado = float(valor.strip())
        return resultado if math.isfinite(resultado) else None
    except (ValueError, TypeError, AttributeError):
        return None


def extrair(valores, prefixo):
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


# Reutilizamos a separação original por registro,
# evitando misturar arquivos de treino e teste.
with (RESULTADOS / "dataset_janelas.csv").open(encoding="utf-8", newline="") as arquivo:
    registros = list(csv.DictReader(arquivo))

conjuntos = {}

for registro in registros:
    nome = registro["arquivo"]
    conjunto = registro["conjunto"]

    if nome in conjuntos and conjuntos[nome] != conjunto:
        raise RuntimeError("Vazamento entre treino e teste.")

    conjuntos[nome] = conjunto

arquivos = sorted(DADOS.glob("bidmc_*_Numerics.csv"))

if len(arquivos) != 53 or len(conjuntos) != 53:
    raise RuntimeError("Conjunto BIDMC ou divisão de arquivos incompleta.")

treino = []
teste = []
descartadas = 0

for arquivo in arquivos:
    leituras = []

    with arquivo.open(encoding="utf-8-sig", newline="") as f:
        for linha in csv.DictReader(f, skipinitialspace=True):
            linha = {k.strip(): v for k, v in linha.items()}

            leituras.append(
                {
                    "tempo": numero(linha.get("Time [s]")),
                    "pulse": numero(linha.get("PULSE")),
                    "spo2": numero(linha.get("SpO2")),
                }
            )

    for inicio in range(0, len(leituras), DURACAO):
        janela = leituras[inicio : inicio + DURACAO]

        if len(janela) != DURACAO:
            continue

        selecionadas = [janela[i] for i in POSICOES]

        valida = all(
            item["tempo"] is not None
            and item["pulse"] is not None
            and item["spo2"] is not None
            and math.isclose(item["tempo"], inicio + posicao, abs_tol=0.01)
            for item, posicao in zip(selecionadas, POSICOES)
        )

        if not valida:
            descartadas += 1
            continue

        pulsos = [item["pulse"] for item in selecionadas]
        spo2s = [item["spo2"] for item in selecionadas]

        # Limites técnicos da entrada do ESP32.
        if not all(40 <= p <= 160 for p in pulsos):
            descartadas += 1
            continue

        if not all(75 <= s <= 100 for s in spo2s):
            descartadas += 1
            continue

        caracteristicas = {
            **extrair(pulsos, "pulse"),
            **extrair(spo2s, "spo2"),
        }

        vetor = [caracteristicas[coluna] for coluna in COLUNAS]

        if conjuntos[arquivo.name] == "treino":
            treino.append(vetor)
        else:
            teste.append(vetor)

if not treino or not teste:
    raise RuntimeError("Treinamento ou teste vazio.")

X_treino = np.asarray(treino, dtype=np.float64)
X_teste = np.asarray(teste, dtype=np.float64)

modelo = IsolationForest(
    n_estimators=200,
    contamination="auto",
    random_state=SEMENTE,
    n_jobs=-1,
)

modelo.fit(X_treino)

scores_treino = modelo.score_samples(X_treino)
scores_teste = modelo.score_samples(X_teste)

limiar = float(np.quantile(scores_treino, 0.05))
sinalizadas = int(np.sum(scores_teste < limiar))

artefato = {
    "modelo": modelo,
    "colunas": COLUNAS,
    "limiar": limiar,
    "quantidade_amostras": AMOSTRAS,
    "intervalo_referencia_segundos": 59 / 27,
    "duracao_aproximada_segundos": DURACAO,
    "tipo": "experimental_esp32",
}

arquivo_modelo = MODELOS / "bioiot_isolation_forest_esp32.joblib"

joblib.dump(artefato, arquivo_modelo)

relatorio = {
    "modelo": "Isolation Forest - ESP32 experimental",
    "origem": "BIDMC",
    "amostras_por_janela": AMOSTRAS,
    "posicoes_originais": POSICOES,
    "janelas_treino": len(treino),
    "janelas_teste": len(teste),
    "descartadas": descartadas,
    "limiar": limiar,
    "sinalizadas_teste": sinalizadas,
    "percentual_sinalizado_teste": round(100 * sinalizadas / len(teste), 2),
    "avaliacao_clinica": False,
}

with (RESULTADOS / "avaliacao_esp32.json").open("w", encoding="utf-8") as f:
    json.dump(relatorio, f, indent=2, ensure_ascii=False)

print("\n===== BIOIOT AI - MODELO ESP32 =====")
print("Amostras por janela:", AMOSTRAS)
print("Janelas de treinamento:", len(treino))
print("Janelas de teste:", len(teste))
print("Janelas descartadas:", descartadas)
print("Limiar experimental:", round(limiar, 6))
print("Sinalizadas no teste:", sinalizadas)
print("Modelo salvo em:", arquivo_modelo)
print("Acuracia clinica: NAO DETERMINADA")
