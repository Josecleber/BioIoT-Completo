import csv
from pathlib import Path

import joblib
import numpy as np

BASE = Path(__file__).resolve().parent
RESULTADOS = BASE / "resultados"
MODELOS = BASE / "modelos"

artefato = joblib.load(MODELOS / "bioiot_isolation_forest.joblib")

modelo = artefato["modelo"]
colunas = artefato["colunas"]
limiar = artefato["limiar"]

with (RESULTADOS / "dataset_janelas.csv").open(encoding="utf-8", newline="") as arquivo:
    registros = list(csv.DictReader(arquivo))

treino = [r for r in registros if r["conjunto"] == "treino"]

teste = [r for r in registros if r["conjunto"] == "teste"]


def matriz(linhas):
    return np.array(
        [[float(linha[c]) for c in colunas] for linha in linhas], dtype=np.float64
    )


X_treino = matriz(treino)
X_teste = matriz(teste)

medianas = np.median(X_treino, axis=0)
scores = modelo.score_samples(X_teste)

explicacoes = []

print("\n===== BIOIOT AI - EXPLICABILIDADE =====")

for indice, (registro, score) in enumerate(zip(teste, scores)):
    if score >= limiar:
        continue

    original = X_teste[indice].copy()
    impactos = []

    for coluna_indice, coluna in enumerate(colunas):
        modificado = original.copy()

        modificado[coluna_indice] = medianas[coluna_indice]

        novo_score = float(modelo.score_samples(modificado.reshape(1, -1))[0])

        diferenca = novo_score - float(score)

        impactos.append(
            {
                "caracteristica": coluna,
                "valor_original": float(original[coluna_indice]),
                "mediana_treino": float(medianas[coluna_indice]),
                "mudanca_score": diferenca,
            }
        )

    impactos.sort(key=lambda item: item["mudanca_score"], reverse=True)

    print(f"\n{registro['arquivo']} | " f"segundo {registro['inicio_segundo']}")
    print(f"Score original: {score:.6f}")

    print("Maiores mudancas positivas no score:")

    for item in impactos[:3]:
        print(f"  {item['caracteristica']}: " f"{item['mudanca_score']:+.6f}")

    explicacoes.append(
        {
            "arquivo": registro["arquivo"],
            "inicio_segundo": registro["inicio_segundo"],
            "score_original": float(score),
            "caracteristicas": impactos,
        }
    )

import json

destino = RESULTADOS / "explicacoes_modelo.json"

with destino.open("w", encoding="utf-8") as f:
    json.dump(
        {
            "metodo": "Substituicao individual pela mediana de treino",
            "limitacao": (
                "Teste de sensibilidade, nao explicacao "
                "causal. Caracteristicas correlacionadas "
                "podem produzir combinacoes artificiais."
            ),
            "resultados": explicacoes,
        },
        f,
        ensure_ascii=False,
        indent=2,
    )

print("\nJanelas investigadas:", len(explicacoes))
print("Relatorio salvo em:", destino)
