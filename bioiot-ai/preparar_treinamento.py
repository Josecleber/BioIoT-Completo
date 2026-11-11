import csv
import json
import math
import random
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parent
DADOS = BASE / "dados" / "bidmc"
RESULTADOS = BASE / "resultados"

TAMANHO_JANELA = 60
SEMENTE = 42

RESULTADOS.mkdir(parents=True, exist_ok=True)


def numero(valor):
    try:
        resultado = float(valor.strip())
        return resultado if math.isfinite(resultado) else None
    except (ValueError, TypeError, AttributeError):
        return None


def caracteristicas(valores, prefixo):
    media = statistics.mean(valores)

    return {
        f"{prefixo}_media": round(media, 5),
        f"{prefixo}_desvio": round(statistics.pstdev(valores), 5),
        f"{prefixo}_minimo": min(valores),
        f"{prefixo}_maximo": max(valores),
        f"{prefixo}_amplitude": round(max(valores) - min(valores), 5),
        f"{prefixo}_tendencia": round(
            (valores[-1] - valores[0]) / (len(valores) - 1), 5
        ),
    }


arquivos = sorted(DADOS.glob("bidmc_*_Numerics.csv"))

if len(arquivos) != 53:
    raise RuntimeError(f"Esperados 53 arquivos, encontrados {len(arquivos)}")

# Separamos arquivos inteiros antes de extrair
# as janelas. Nenhum registro entra nos dois grupos.
nomes = [arquivo.name for arquivo in arquivos]
random.Random(SEMENTE).shuffle(nomes)

quantidade_teste = math.ceil(len(nomes) * 0.20)
arquivos_teste = set(nomes[:quantidade_teste])

linhas_dataset = []
contagem = {"treino": 0, "teste": 0}
descartadas = 0

for arquivo in arquivos:
    conjunto = "teste" if arquivo.name in arquivos_teste else "treino"

    leituras = []

    with arquivo.open("r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f, skipinitialspace=True)

        for linha in leitor:
            linha = {chave.strip(): valor for chave, valor in linha.items()}

            leituras.append(
                {
                    "tempo": numero(linha.get("Time [s]")),
                    "pulse": numero(linha.get("PULSE")),
                    "spo2": numero(linha.get("SpO2")),
                }
            )

    for inicio in range(0, len(leituras), TAMANHO_JANELA):
        janela = leituras[inicio : inicio + TAMANHO_JANELA]

        if len(janela) != TAMANHO_JANELA:
            continue

        completa = all(
            item["tempo"] is not None
            and item["pulse"] is not None
            and item["spo2"] is not None
            for item in janela
        )

        if not completa:
            descartadas += 1
            continue

        tempos = [item["tempo"] for item in janela]

        consecutiva = all(
            math.isclose(tempos[i + 1] - tempos[i], 1.0) for i in range(len(tempos) - 1)
        )

        if not consecutiva:
            descartadas += 1
            continue

        pulsos = [item["pulse"] for item in janela]
        oxigenacao = [item["spo2"] for item in janela]

        registro = {
            "arquivo": arquivo.name,
            "conjunto": conjunto,
            "inicio_segundo": tempos[0],
        }

        registro.update(caracteristicas(pulsos, "pulse"))
        registro.update(caracteristicas(oxigenacao, "spo2"))

        linhas_dataset.append(registro)
        contagem[conjunto] += 1


if not linhas_dataset:
    raise RuntimeError("Nenhuma janela valida encontrada.")

caminho_csv = RESULTADOS / "dataset_janelas.csv"

with caminho_csv.open("w", encoding="utf-8", newline="") as f:
    escritor = csv.DictWriter(f, fieldnames=linhas_dataset[0].keys())
    escritor.writeheader()
    escritor.writerows(linhas_dataset)

resumo = {
    "origem": "BIDMC",
    "semente": SEMENTE,
    "tamanho_janela": TAMANHO_JANELA,
    "total_arquivos": len(arquivos),
    "arquivos_treino": len(arquivos) - len(arquivos_teste),
    "arquivos_teste": len(arquivos_teste),
    "janelas_treino": contagem["treino"],
    "janelas_teste": contagem["teste"],
    "janelas_descartadas": descartadas,
    "separacao": "Por arquivo de origem",
    "modelo_treinado": False,
}

with (RESULTADOS / "preparacao_treinamento.json").open("w", encoding="utf-8") as f:
    json.dump(resumo, f, ensure_ascii=False, indent=2)

print("\n===== BIOIOT AI - PREPARACAO =====")
print("Arquivos:", len(arquivos))
print("Arquivos de treino:", resumo["arquivos_treino"])
print("Arquivos de teste:", resumo["arquivos_teste"])
print("Janelas de treino:", contagem["treino"])
print("Janelas de teste:", contagem["teste"])
print("Janelas descartadas:", descartadas)
print("Total de janelas:", len(linhas_dataset))
print("Dataset salvo em:", caminho_csv)
print("Modelo treinado: NAO")
