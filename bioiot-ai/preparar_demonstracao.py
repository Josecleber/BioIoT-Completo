import csv
import json
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESULTADOS = BASE / "resultados"


def ler_csv(nome):
    with (RESULTADOS / nome).open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def ler_json(nome):
    with (RESULTADOS / nome).open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def chave(registro):
    return (registro["arquivo"], float(registro["inicio_segundo"]))


dataset = ler_csv("dataset_janelas.csv")
analises = ler_csv("analises_teste.csv")
avaliacao = ler_json("avaliacao_modelo.json")
explicacoes = ler_json("explicacoes_modelo.json")

treino = [r for r in dataset if r["conjunto"] == "treino"]
teste = [r for r in dataset if r["conjunto"] == "teste"]

arquivos_treino = {r["arquivo"] for r in treino}
arquivos_teste = {r["arquivo"] for r in teste}

assert not arquivos_treino.intersection(
    arquivos_teste
), "Erro: arquivos compartilhados entre treino e teste"

assert len(teste) == len(analises), "Erro: total de analises diferente do teste"

mapa_teste = {chave(r): r for r in teste}
mapa_exp = {chave(r): r for r in explicacoes["resultados"]}

sinalizadas = [r for r in analises if r["padrao_atipico"].lower() == "true"]

nao_sinalizadas = [r for r in analises if r["padrao_atipico"].lower() == "false"]

assert len(sinalizadas) == 4, (
    "Quantidade de sinalizacoes mudou. " "Verifique os resultados antes de prosseguir."
)

# Seleciona exemplos proximos da mediana dos scores,
# evitando escolher apenas casos extremos.
mediana_score = statistics.median(float(r["score"]) for r in nao_sinalizadas)

comparacao = sorted(
    nao_sinalizadas, key=lambda r: abs(float(r["score"]) - mediana_score)
)

# Escolhe dois exemplos de arquivos diferentes.
selecionados_comparacao = []
arquivos_usados = set()

for registro in comparacao:
    if registro["arquivo"] not in arquivos_usados:
        selecionados_comparacao.append(registro)
        arquivos_usados.add(registro["arquivo"])

    if len(selecionados_comparacao) == 2:
        break

selecionados = sinalizadas + selecionados_comparacao

casos = []

for r in selecionados:
    origem = mapa_teste[chave(r)]
    explicacao = mapa_exp.get(chave(r))

    atipico = r["padrao_atipico"].lower() == "true"

    caso = {
        "id": f"{r['arquivo']}_{float(r['inicio_segundo']):g}",
        "arquivo": r["arquivo"],
        "inicio_segundo": float(r["inicio_segundo"]),
        "duracao_segundos": 60,
        "tipo": ("padrao_atipico" if atipico else "nao_sinalizado"),
        "score": float(r["score"]),
        "limiar": float(avaliacao["limiar"]),
        "pulse_media": float(origem["pulse_media"]),
        "pulse_desvio": float(origem["pulse_desvio"]),
        "pulse_amplitude": float(origem["pulse_amplitude"]),
        "spo2_media": float(origem["spo2_media"]),
        "spo2_minimo": float(origem["spo2_minimo"]),
        "spo2_amplitude": float(origem["spo2_amplitude"]),
        "sensibilidade": (explicacao["caracteristicas"][:3] if explicacao else []),
    }

    casos.append(caso)

catalogo = {
    "titulo": "BioIoT AI - Laboratorio Experimental",
    "origem": "BIDMC - PhysioNet",
    "modelo": "Isolation Forest",
    "janelas_treinamento": len(treino),
    "janelas_teste": len(teste),
    "total_sinalizadas_teste": len(sinalizadas),
    "metodo_explicacao": (
        "Teste de sensibilidade por substituicao " "individual pela mediana de treino"
    ),
    "aviso": (
        "Resultados estatisticos experimentais. "
        "Nao representam diagnosticos ou "
        "avaliacao clinica."
    ),
    "casos": casos,
}

destino = RESULTADOS / "catalogo_demonstracao.json"

with destino.open("w", encoding="utf-8") as arquivo:
    json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)

print("\n===== BIOIOT AI - DEMONSTRACAO =====")
print("Janelas de treinamento:", len(treino))
print("Janelas de teste:", len(teste))
print("Casos selecionados:", len(casos))
print("Casos sinalizados:", len(sinalizadas))
print("Casos de comparacao:", len(selecionados_comparacao))

for caso in casos:
    print(
        f"{caso['arquivo']} | "
        f"{caso['inicio_segundo']:g}s | "
        f"{caso['tipo']} | "
        f"score={caso['score']:.5f}"
    )

print("Catalogo salvo em:", destino)
