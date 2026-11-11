import csv
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
PASTA_DADOS = BASE / "dados" / "bidmc"
PASTA_RESULTADOS = BASE / "resultados"
TAMANHO_JANELA = 60

PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)


def converter_numero(valor):
    try:
        numero = float(valor.strip())
        return numero if math.isfinite(numero) else None
    except (ValueError, TypeError, AttributeError):
        return None


relatorio = {
    "origem": "BIDMC PPG and Respiration Dataset",
    "janela_segundos": TAMANHO_JANELA,
    "criterio": "PULSE e SpO2 numericos em todos os segundos",
    "registros": [],
    "total_linhas": 0,
    "total_janelas": 0,
    "janelas_aptas": 0,
    "janelas_descartadas": 0,
}

arquivos = sorted(PASTA_DADOS.glob("bidmc_*_Numerics.csv"))

if len(arquivos) != 53:
    raise RuntimeError(
        f"Esperados 53 arquivos Numerics.csv; encontrados {len(arquivos)}."
    )

for arquivo in arquivos:
    linhas = []

    with arquivo.open("r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f, skipinitialspace=True)

        for linha in leitor:
            linha = {chave.strip(): valor for chave, valor in linha.items()}

            linhas.append(
                {
                    "tempo": converter_numero(linha.get("Time [s]")),
                    "hr": converter_numero(linha.get("HR")),
                    "pulse": converter_numero(linha.get("PULSE")),
                    "spo2": converter_numero(linha.get("SpO2")),
                }
            )

    ausentes = {
        "HR": sum(l["hr"] is None for l in linhas),
        "PULSE": sum(l["pulse"] is None for l in linhas),
        "SpO2": sum(l["spo2"] is None for l in linhas),
    }

    aptas = 0
    descartadas = 0

    for inicio in range(0, len(linhas), TAMANHO_JANELA):
        janela = linhas[inicio : inicio + TAMANHO_JANELA]

        if len(janela) != TAMANHO_JANELA:
            continue

        completa = all(
            l["tempo"] is not None and l["pulse"] is not None and l["spo2"] is not None
            for l in janela
        )

        tempos = [l["tempo"] for l in janela]

        consecutiva = (
            all(
                math.isclose(tempos[i + 1] - tempos[i], 1.0)
                for i in range(len(tempos) - 1)
            )
            if all(t is not None for t in tempos)
            else False
        )

        if completa and consecutiva:
            aptas += 1
        else:
            descartadas += 1

    relatorio["registros"].append(
        {
            "arquivo": arquivo.name,
            "linhas": len(linhas),
            "ausentes": ausentes,
            "janelas_aptas": aptas,
            "janelas_descartadas": descartadas,
        }
    )

    relatorio["total_linhas"] += len(linhas)
    relatorio["total_janelas"] += aptas + descartadas
    relatorio["janelas_aptas"] += aptas
    relatorio["janelas_descartadas"] += descartadas

    print(
        f"{arquivo.stem}: "
        f"{len(linhas)} linhas | "
        f"{aptas} janelas aptas | "
        f"{descartadas} descartadas"
    )

destino = PASTA_RESULTADOS / "auditoria_bidmc.json"

with destino.open("w", encoding="utf-8") as f:
    json.dump(relatorio, f, ensure_ascii=False, indent=2)

print("\n===== RESUMO BIOIOT AI =====")
print("Arquivos:", len(arquivos))
print("Total de linhas:", relatorio["total_linhas"])
print("Janelas avaliadas:", relatorio["total_janelas"])
print("Janelas aptas:", relatorio["janelas_aptas"])
print("Janelas descartadas:", relatorio["janelas_descartadas"])
print("Relatorio salvo em:", destino)
