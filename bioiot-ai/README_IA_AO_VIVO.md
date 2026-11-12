# BioIoT AI – Etapa 1: serviço de inferência experimental

Copiar estes arquivos para `bioiot-ai/` **sem substituir** os arquivos existentes.
O treino anterior deve ter gerado `bioiot-ai/modelos/bioiot_isolation_forest.joblib`.

## Testar sem iniciar site/ESP32

No PowerShell, na raiz BioIoT:

```powershell
docker run --rm -v "${PWD}\bioiot-ai:/workspace" -w /workspace python:3.12-slim sh -c "pip install --no-cache-dir --disable-pip-version-check -q -r requirements.txt && python -m unittest -v teste_api_ia"
```

## Criar imagem isolada (opcional, após os testes)

```powershell
docker build -f .\bioiot-ai\Dockerfile.ia -t bioiot-ai:experimental .\bioiot-ai
```

Não publicar a porta de inferência externamente nem usar sua resposta para disparar alarmes clínicos. A próxima etapa é a integração entre o Node.js e o serviço, com tratamento explícito de amostragem temporal.
