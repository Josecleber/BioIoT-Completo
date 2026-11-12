import joblib

caminho = "modelos/bioiot_isolation_forest_esp32.joblib"

artefato = joblib.load(caminho)

print("===== VERIFICAÇÃO DO MODELO ESP32 =====")
print("Chaves:", list(artefato.keys()))
print("Amostras:", artefato["quantidade_amostras"])
print("Intervalo:", artefato["intervalo_referencia_segundos"])
print("Modelo:", type(artefato["modelo"]).__name__)
print("Status: modelo carregado com sucesso")
