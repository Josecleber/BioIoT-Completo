import csv
import json
import math
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

BASE = Path(__file__).resolve().parent
RESULTADOS = BASE / "resultados"
MODELOS = BASE / "modelos"

MODELOS.mkdir(parents=True, exist_ok=True)

ARQUIVO_DADOS = RESULTADOS / "dataset_janelas.csv"

COLUNAS = [
    "pulse_media",
    "pulse_desvio",
    "pulse_minimo",
    "pulse_maximo",
    "pulse_amplitude",
    "pulse_tendencia",
    "spo2_media",
    "spo2_desvio",
    "spo2_minimo",
    "spo2_maximo",
    "spo2_amplitude",
    "spo2_tendencia",
]

SEMENTE = 42
FRACAO_REFERENCIA = 0.05


def carregar_dados():
    with ARQUIVO_DADOS.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)

        obrigatorias = set(COLUNAS + ["arquivo", "conjunto"])

        ausentes = obrigatorias - set(leitor.fieldnames or [])

        if ausentes:
            raise ValueError(f"Colunas ausentes: {sorted(ausentes)}")

        linhas = list(leitor)

    treino = [linha for linha in linhas if linha["conjunto"] == "treino"]

    teste = [linha for linha in linhas if linha["conjunto"] == "teste"]

    if not treino or not teste:
        raise ValueError("Treino ou teste sem registros.")

    arquivos_treino = {linha["arquivo"] for linha in treino}

    arquivos_teste = {linha["arquivo"] for linha in teste}

    if arquivos_treino & arquivos_teste:
        raise ValueError("Vazamento: arquivo presente em treino e teste.")

    def matriz(registros):
        dados = np.array(
            [[float(linha[col]) for col in COLUNAS] for linha in registros],
            dtype=np.float64,
        )

        if not np.isfinite(dados).all():
            raise ValueError("Existem valores nao finitos no dataset.")

        return dados

    return treino, teste, matriz(treino), matriz(teste)


def resumo_scores(scores):
    return {
        "minimo": float(np.min(scores)),
        "mediana": float(np.median(scores)),
        "maximo": float(np.max(scores)),
    }


treino, teste, X_treino, X_teste = carregar_dados()

print("\n===== BIOIOT AI - TREINAMENTO =====")
print("Janelas de treino:", len(treino))
print("Janelas de teste:", len(teste))
print("Caracteristicas:", len(COLUNAS))

modelo = IsolationForest(
    n_estimators=200,
    contamination="auto",
    random_state=SEMENTE,
    n_jobs=-1,
)

# O modelo aprende somente com os dados
# reservados ao treinamento.
modelo.fit(X_treino)

# No Isolation Forest, scores menores indicam
# padrões mais incomuns segundo o modelo.
scores_treino = modelo.score_samples(X_treino)

# Referencia experimental: percentil 5
# dos scores do conjunto de treino.
limiar = float(np.quantile(scores_treino, FRACAO_REFERENCIA))

scores_teste = modelo.score_samples(X_teste)

sinalizados_treino = scores_treino < limiar
sinalizados_teste = scores_teste < limiar

quantidade_teste = int(np.sum(sinalizados_teste))

percentual_teste = float(np.mean(sinalizados_teste) * 100)

print("\nModelo treinado com sucesso!")
print("Limiar experimental:", round(limiar, 6))
print("Janelas sinalizadas no treino:", int(np.sum(sinalizados_treino)))
print("Janelas sinalizadas no teste:", quantidade_teste)
print("Percentual sinalizado no teste:", round(percentual_teste, 2), "%")

# Guardamos o modelo e as informacoes
# necessarias para interpreta-lo.
artefato = {
    "modelo": modelo,
    "colunas": COLUNAS,
    "limiar": limiar,
    "tamanho_janela_segundos": 60,
    "tipo": "deteccao_estatistica_nao_supervisionada",
}

CAMINHO_MODELO = MODELOS / "bioiot_isolation_forest.joblib"
joblib.dump(artefato, CAMINHO_MODELO)

relatorio = {
    "modelo": "Isolation Forest",
    "natureza": "nao supervisionado",
    "semente": SEMENTE,
    "janelas_treino": len(treino),
    "janelas_teste": len(teste),
    "arquivos_treino": len({l["arquivo"] for l in treino}),
    "arquivos_teste": len({l["arquivo"] for l in teste}),
    "caracteristicas": COLUNAS,
    "fracao_referencia_treino": FRACAO_REFERENCIA,
    "limiar": limiar,
    "treino_scores": resumo_scores(scores_treino),
    "teste_scores": resumo_scores(scores_teste),
    "sinalizadas_treino": int(np.sum(sinalizados_treino)),
    "sinalizadas_teste": quantidade_teste,
    "percentual_sinalizado_teste": percentual_teste,
    "interpretacao": (
        "Sinalizacao estatistica de padroes "
        "incomuns. Nao representa diagnostico "
        "nem acuracia clinica."
    ),
    "validacao_clinica": False,
}

CAMINHO_RELATORIO = RESULTADOS / "avaliacao_modelo.json"

with CAMINHO_RELATORIO.open("w", encoding="utf-8") as arquivo:
    json.dump(relatorio, arquivo, ensure_ascii=False, indent=2)

# Relatorio por janela de teste para
# posterior visualizacao no Laboratorio da IA.
CAMINHO_JANELAS = RESULTADOS / "analises_teste.csv"

with CAMINHO_JANELAS.open("w", encoding="utf-8", newline="") as arquivo:
    campos = [
        "arquivo",
        "inicio_segundo",
        "score",
        "padrao_atipico",
    ]

    escritor = csv.DictWriter(arquivo, fieldnames=campos)
    escritor.writeheader()

    for linha, score, sinalizada in zip(teste, scores_teste, sinalizados_teste):
        escritor.writerow(
            {
                "arquivo": linha["arquivo"],
                "inicio_segundo": linha["inicio_segundo"],
                "score": float(score),
                "padrao_atipico": bool(sinalizada),
            }
        )

print("\nModelo salvo em:", CAMINHO_MODELO)
print("Avaliacao salva em:", CAMINHO_RELATORIO)
print("Analises salvas em:", CAMINHO_JANELAS)
print("\nAVISO: nenhuma acuracia clinica foi calculada.")
