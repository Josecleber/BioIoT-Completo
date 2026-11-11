import csv
import json
import math
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
DADOS = BASE / "dados" / "bidmc"
RESULTADOS = BASE / "resultados"

ORIGEM = RESULTADOS / "catalogo_demonstracao.json"
DESTINO = RESULTADOS / "catalogo_interativo.json"


def numero(valor):
    try:
        n = float(valor.strip())
        return n if math.isfinite(n) else None
    except (ValueError, TypeError, AttributeError):
        return None


with ORIGEM.open("r", encoding="utf-8") as f:
    catalogo = json.load(f)

if len(catalogo["casos"]) != 6:
    raise RuntimeError("Esperados exatamente 6 casos.")

for caso in catalogo["casos"]:
    arquivo = caso["arquivo"]

    # Aceita somente nomes oficiais esperados.
    if not re.fullmatch(r"bidmc_\d{2}_Numerics\.csv", arquivo):
        raise ValueError(f"Arquivo inesperado: {arquivo}")

    inicio = float(caso["inicio_segundo"])
    caminho = DADOS / arquivo

    if not caminho.is_file():
        raise FileNotFoundError(caminho)

    serie = []

    with caminho.open("r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f, skipinitialspace=True)

        for linha in leitor:
            linha = {chave.strip(): valor for chave, valor in linha.items()}

            tempo = numero(linha.get("Time [s]"))

            if tempo is None:
                continue

            if inicio <= tempo < inicio + 60:
                pulse = numero(linha.get("PULSE"))
                spo2 = numero(linha.get("SpO2"))

                if pulse is None or spo2 is None:
                    raise ValueError(f"Valor ausente em {arquivo}, " f"segundo {tempo}")

                serie.append(
                    {
                        "segundo": int(round(tempo - inicio)),
                        "pulse": pulse,
                        "spo2": spo2,
                    }
                )

    # Verifica se realmente temos os 60 segundos.
    if len(serie) != 60:
        raise ValueError(
            f"{arquivo}: esperados 60 pontos, " f"encontrados {len(serie)}"
        )

    segundos = [p["segundo"] for p in serie]

    if segundos != list(range(60)):
        raise ValueError(f"{arquivo}: tempos nao consecutivos")

    # Verifica se os dados originais correspondem
    # as medias ja presentes no catalogo da IA.
    media_pulse = sum(p["pulse"] for p in serie) / 60

    media_spo2 = sum(p["spo2"] for p in serie) / 60

    if not math.isclose(media_pulse, float(caso["pulse_media"]), abs_tol=0.01):
        raise ValueError(f"Media de pulso divergente: {arquivo}")

    if not math.isclose(media_spo2, float(caso["spo2_media"]), abs_tol=0.01):
        raise ValueError(f"Media de SpO2 divergente: {arquivo}")

    caso["serie_temporal"] = serie

    print(
        f"OK: {arquivo} | "
        f"inicio={inicio:g}s | "
        f"60 pontos | "
        f"PULSE={media_pulse:.2f} | "
        f"SpO2={media_spo2:.2f}"
    )

catalogo["tipo_dados"] = "historicos_cientificos"
catalogo["analise_ao_vivo"] = False
catalogo["aviso"] = (
    "Dados historicos cientificos da base BIDMC. "
    "Resultados de aprendizado de maquina "
    "experimentais, sem finalidade diagnostica. "
    "Nao representam leituras ao vivo do visitante."
)

with DESTINO.open("w", encoding="utf-8") as f:
    json.dump(catalogo, f, ensure_ascii=False, indent=2, allow_nan=False)

print("\n===== BIOIOT AI - SERIES TEMPORAIS =====")
print("Casos:", len(catalogo["casos"]))
print("Pontos por caso:", 60)
print("Total de pontos:", 60 * len(catalogo["casos"]))
print("Arquivo gerado:", DESTINO)
