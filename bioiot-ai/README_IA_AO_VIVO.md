# BioIoT AI — Módulo 2: Inteligência Artificial Experimental

## 1. Visão geral

O BioIoT integra um sensor MAX30102 conectado ao ESP32, um servidor Node.js com SQLite, uma interface web e um serviço Python de análise estatística experimental por aprendizado de máquina.

Fluxo das medições:

```text
MAX30102 → ESP32 → HTTP/Wi-Fi → Node.js → Dashboard
                                    └→ Coletor de 28 amostras → Serviço Python → Isolation Forest → Painel da IA
```

A IA identifica **padrões estatísticos atípicos** em janelas de dados. **Não fornece diagnóstico médico, probabilidade clínica nem recomendação de tratamento.** Os alarmes do BioIoT permanecem independentes da classificação da IA.

## 2. Componentes

| Componente | Função |
|---|---|
| `site/server.js` | Recebe medições, controla sessões e integra o coletor de IA |
| `site/ia_coletor.js` | Reúne e valida janelas de 28 leituras por dispositivo/sessão; comunica-se com a API Python |
| `site/public/bioiot-ai-live.js` | Mostra coleta, progresso, resultados e mensagens no navegador |
| `site/public/bioiot-ai.css` | Estilos da experiência visual |
| `bioiot-ai/api_ia.py` | Serviço de inferência HTTP com modelos Isolation Forest |
| `bioiot-ai/Dockerfile.ia` | Imagem do serviço Python |
| `compose.ai.yaml` | Serviço Docker `ia`, comunicação interna e verificação de saúde |
| `bioiot-ai/treinar_modelo.py` | Treinamento original com janelas do conjunto BIDMC |
| `bioiot-ai/treinar_modelo_esp32.py` | Treinamento experimental adaptado à cadência observada no ESP32 |

## 3. Modelos e dados

A análise utiliza dois modelos experimentais:

1. **Modelo original BIDMC:** janelas de 60 leituras, correspondentes a aproximadamente 60 segundos na série de referência.
2. **Modelo adaptado ao ESP32:** janelas de **28 leituras válidas**, coletadas em aproximadamente **55–65 segundos**, com intervalos aceitos de cerca de **1,7–2,9 segundos** entre leituras.

Ambos usam 12 características derivadas de BPM e SpO₂: média, desvio-padrão, mínimo, máximo, amplitude e tendência de cada sinal.

Os modelos são baseados em dados de referência BIDMC. A adaptação temporal à cadência do ESP32 **não equivale a treinamento ou validação com uma população clínica medida pelo próprio dispositivo**. Movimentos, posicionamento do dedo e qualidade do sinal podem produzir padrões atípicos.

### Evidências experimentais registradas

| Experimento | Treino | Teste | Janelas sinalizadas no teste |
|---|---:|---:|---:|
| BIDMC original | 326 | 88 | 4 |
| BIDMC adaptado à cadência ESP32 | 318 | 87 | 4 |

Essas quantidades **não são métricas de acurácia, sensibilidade, especificidade nem valor preditivo**. Não há, neste experimento, validação clínica com rótulos diagnósticos suficientes para calculá-las.

## 4. Funcionamento em tempo real

O coletor acumula leituras válidas de cada dispositivo em memória e envia cada janela completa ao Python. O servidor principal continua operando mesmo quando a IA está indisponível.

- **Modo livre (Nenhum):** permite análise experimental sem gravar as leituras no histórico de paciente do SQLite.
- **Modo paciente:** continua registrando medições na rotina do monitoramento e solicita a análise da IA separadamente.
- **Retirada do dedo:** pausa a coleta, mas preserva o resultado da última janela completa na interface.
- **Nova janela:** mantém o resultado anterior identificado como anterior enquanto novas leituras são reunidas.
- **Encerramento de sessão:** limpa o estado da IA ligado ao dispositivo/sessão para não apresentar o resultado do paciente encerrado como se pertencesse a outro.

O estado da IA pode ser consultado em `GET /api/ia/estado/ESP32-BANCADA-01` no servidor Node.js. O serviço Python atende internamente, entre outros, `GET /health` e `POST /analisar-esp32`.

## 5. Requisitos

- Windows com PowerShell, ou outro sistema com Docker e Docker Compose compatíveis.
- Docker Desktop iniciado.
- Arquivos do repositório BioIoT.
- Os **três artefatos experimentais** indicados a seguir, fornecidos separadamente do Git.
- Para a demonstração com medições reais: ESP32 com MAX30102 configurado para enviar dados ao servidor.

### Artefatos que não estão no Git

O arquivo `BioIoT-IA-artefatos.zip` deve ter esta estrutura interna:

```text
modelos/
  bioiot_isolation_forest.joblib
  bioiot_isolation_forest_esp32.joblib
resultados/
  catalogo_interativo.json
```

Após obter o pacote de uma fonte confiável, extrair seu conteúdo **dentro de `bioiot-ai/`**, preservando as subpastas. O Dockerfile requer esses caminhos para construir a imagem `ia`.

> Atenção: arquivos `.joblib` podem executar código durante a desserialização. Nunca carregar modelos obtidos de fontes desconhecidas. Guarde o ZIP em backup separado e protegido. O Git sozinho não inclui os modelos.

## 6. Inicializar no Windows

Abrir o PowerShell na pasta raiz do BioIoT e executar:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml up -d --build
```

Verificar o estado:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml ps
```

Os serviços `site` e `ia` deverão atingir o estado `healthy`. A interface local é acessível em `http://localhost:3000`.

Consultar o estado da coleta:

```powershell
Invoke-RestMethod `
  "http://localhost:3000/api/ia/estado/ESP32-BANCADA-01" |
  ConvertTo-Json -Depth 8
```

Se não houver coleta iniciada, é esperado `status: "aguardando"` e `amostras_coletadas: 0`.

**Não utilize `docker compose down -v`** para esses procedimentos: remover volumes pode eliminar dados persistentes do SQLite.

## 7. Testes

### Testes de API Python

Os arquivos `bioiot-ai/teste_api_ia.py` e `bioiot-ai/teste_api_esp32.py` validam entradas e saídas das rotas experimentais. Para executá-los sem modificar os serviços em funcionamento, em um ambiente Python com as dependências de `bioiot-ai/requirements.txt` instaladas:

```powershell
cd bioiot-ai
python -m unittest -v teste_api_ia teste_api_esp32
cd ..
```

### Testes de alarmes

Há oito arquivos em `site/testes-alarmes/`, cobrindo confirmação, integração, concorrência, banco, encerramento, rollback e recuperação. No ambiente de desenvolvimento, os oito passaram após ajustar o isolamento do teste de confirmação e a espera pela fila na integração.

Os testes foram executados em contêineres temporários, sem rede e usando banco de dados em memória. Isso **não substitui** uma validação médica ou uma prova exaustiva de todos os cenários operacionais.

## 8. Falhas e recuperação

Se o serviço Python parar, o monitoramento principal deve continuar operando independentemente. Para verificar os contêineres:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml ps
```

Para religar somente o serviço Python:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml start ia
```

Para ver mensagens recentes:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml logs --tail 80 ia
docker compose -f compose.yaml -f compose.ai.yaml logs --tail 80 site
```

Após a recuperação, iniciar uma **nova janela completa** de coleta para confirmar a retomada da inferência. Um resultado de janela anterior pode continuar visível quando a coleta está pausada ou reiniciada.

## 9. Reprodução científica e limitações

A **execução** dos modelos pode ser restaurada com o código versionado e o pacote de três artefatos. Já a **reprodução integral do treinamento** depende também do conjunto BIDMC, dos arquivos CSV preparados, dos critérios de divisão entre treino e teste e das versões das dependências. Esses insumos não estão integralmente contidos no Git.

A separação de treino e teste foi verificada por arquivo de origem, para evitar que janelas do mesmo arquivo aparecessem nos dois conjuntos. O modelo não foi validado como dispositivo médico e não deve acionar alarmes clínicos ou orientar decisões assistenciais.

## 10. Evidências de funcionamento

Foram observadas janelas reais de 28 medições recebidas do ESP32, análises concluídas em aproximadamente um minuto, apresentação do resultado anterior durante nova coleta, limpeza do estado ao encerrar paciente e recuperação da inferência após reiniciar o serviço Python. A gravação de leituras com identificação de paciente no SQLite também foi verificada.

Os resultados numéricos são experimentais e podem mudar entre janelas; uma pontuação acima ou abaixo do limiar apenas expressa a decisão estatística do Isolation Forest para aquela janela.

---

**Status:** implementação e integração experimental concluídas; documentação e empacotamento em revisão. Não possui finalidade diagnóstica.
