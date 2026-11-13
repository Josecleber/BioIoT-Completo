# BioIoT — Monitoramento IoT com ESP32 e Inteligência Artificial

Projeto acadêmico experimental que integra **ESP32 + MAX30102**, **Node.js**, **SQLite**, **Dashboard Web**, **Gêmeo Digital**, **alarmes** e **análise estatística com Inteligência Artificial (Isolation Forest)**.

> **Aviso:** o BioIoT é um protótipo acadêmico. Estimativas de BPM/SpO₂, alertas e resultados de IA **não são diagnósticos médicos** nem substituem equipamentos clínicos certificados.

## 1. Arquitetura

```text
MAX30102 → ESP32 → Wi-Fi → API Node.js → Dashboard Web
                              ├── SQLite (sessões/leituras de pacientes)
                              ├── Lógica de alarmes
                              └── Coletor de janelas → API Python / Isolation Forest
                                                       ↓
                                             Painel BioIoT AI
```

O servidor recebe leituras do ESP32 e atualiza o painel. No modo de paciente monitorado, há registro das medições no SQLite. No **modo livre**, as medições alimentam o painel e a IA sem serem salvas como leituras de um paciente. A análise de IA é **complementar**: os alarmes principais não dependem do Python.

## 2. Pré-requisitos

- **Docker Desktop** com Docker Compose (Windows, Linux ou macOS).
- Navegador para acessar o painel.
- Para o hardware: **ESP32**, sensor **MAX30102**, cabo USB, rede Wi-Fi **2,4 GHz**, **VS Code** e extensão **PlatformIO**.
- Para colaborar no código: **Git**.

## 3. Baixar o projeto

```powershell
git clone https://github.com/Josecleber/BioIoT-Completo.git
cd BioIoT-Completo
```

Também é possível usar **Code → Download ZIP** na página do repositório; neste caso, extraia a pasta antes de executar os comandos.

## 4. Iniciar o sistema completo

Na raiz do projeto:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml up -d --build
```

Conferir a inicialização:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml ps
```

Os serviços `site` (Node.js) e `ia` (Python) devem ficar **healthy**. O primeiro início pode levar mais tempo para instalar e compilar dependências.

Acesse: **http://localhost:3000**.

Para acompanhar logs:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml logs --tail 80 site ia
```

Para parar os serviços **sem apagar os volumes de dados**:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml stop
```

**Não use `docker compose down -v`**, pois isso pode apagar volumes persistentes, incluindo dados SQLite.

### Modelos de IA incluídos

A versão completa do projeto inclui, em `bioiot-ai/modelos/`:

- `bioiot_isolation_forest.joblib` — modelo experimental de referência BIDMC;
- `bioiot_isolation_forest_esp32.joblib` — modelo experimental adaptado à cadência do ESP32.

O catálogo necessário à demonstração histórica está em `bioiot-ai/resultados/catalogo_interativo.json`. Os modelos são artefatos binários do Python; carregue apenas arquivos provenientes de fontes em que confia.

> Esses arquivos são necessários **para executar os modelos já treinados**. Reproduzir todo o **treinamento** exige obter os registros BIDMC e gerar os conjuntos intermediários; o banco SQLite de pacientes não deve ser publicado.

## 5. Preparar o ESP32

1. Abra a pasta `esp32/` no VS Code com a extensão PlatformIO.
2. Copie `esp32/include/config_local.example.h` para `esp32/include/config_local.h`.
3. No `config_local.h`, configure as credenciais da **sua** rede Wi-Fi (2,4 GHz) e a URL do servidor indicada por `BIOIOT_SERVER_URL`. Use o **IP local do computador** que executa o Docker, e não `localhost`, pois o ESP32 é outro dispositivo.
4. Verifique a ligação do MAX30102 seguindo `esp32/README.md`.
5. Execute **Build** e **Upload** no PlatformIO. Para acompanhar as mensagens da placa, use o **Serial Monitor** na porta serial correspondente.
6. Abra o Dashboard e coloque o dedo no sensor para verificar as leituras.

**Segurança:** `esp32/include/config_local.h` é específico de cada computador/rede e está ignorado pelo Git. **Nunca publique esse arquivo, sua senha de Wi-Fi ou tokens**. O arquivo `config_local.example.h` serve como modelo sem informações pessoais.

## 6. Funcionalidades do painel

- **Dashboard**: visualização das estimativas de BPM/SpO₂ e estado do dispositivo.
- **Gêmeo Digital**: representação visual associada à monitoração.
- **Visitantes/Pacientes**: cadastro e seleção para sessões monitoradas.
- **Alarmes**: regras independentes do serviço de IA, com confirmação, encerramento e histórico.
- **BioIoT AI Experience**: análise estatística experimental de sequências de medições.
- **Análise de Algoritmos**: experimentos acadêmicos de ordenação, complexidade e desempenho.

### Como funciona a IA ao vivo

O ESP32 transmite medições válidas aproximadamente a cada 2,2 segundos. O backend forma uma janela de **28 medições em aproximadamente 60 segundos** e a envia para a API Python. O modelo **Isolation Forest** avalia 12 características estatísticas das sequências de BPM e SpO₂: média, desvio-padrão, mínimo, máximo, amplitude e tendência de cada variável.

A tela informa se a janela foi **estatisticamente sinalizada** ou **não sinalizada**. Esse resultado **não é diagnóstico** nem informa a probabilidade clínica de uma doença. Artefatos e movimentações no sensor podem influenciar as pontuações.

Ao retirar o dedo, a coleta é pausada e o último resultado pode continuar visível. Ao encerrar o monitoramento de um paciente, o estado da IA daquela sessão é limpo. A análise também funciona no modo livre, sem associar a coleta a um paciente.

## 7. Testes

### Testes Node.js

Para executar os testes já configurados no `package.json` do site:

```powershell
docker compose -f compose.yaml -f compose.ai.yaml exec site npm test
docker compose -f compose.yaml -f compose.ai.yaml exec site npm run test:complexidade
```

### Testes da API Python original

```powershell
docker run --rm --network none --entrypoint python bioiot-ia:latest -m unittest -v teste_api_ia
```

### Testes do modelo ESP32

O Dockerfile da IA não inclui este arquivo de testes na imagem; monte-o em modo somente leitura:

```powershell
docker run --rm --network none `
  -v "${PWD}\bioiot-ai\teste_api_esp32.py:/workspace/teste_api_esp32.py:ro" `
  --entrypoint python bioiot-ia:latest -m unittest -v teste_api_esp32
```

### Testes isolados de alarmes

Os testes de alarmes estão em `site/testes-alarmes/`. Para executá-los sem utilizar o SQLite persistente do servidor, use contêineres temporários, sem rede nem volume de dados, seguindo a documentação/testes do projeto. Alguns testes extraem trechos do arquivo `server.js` e exigem executar a versão correspondente do código.

## 8. Resolução de problemas

**Painel não abre:** confira `docker compose -f compose.yaml -f compose.ai.yaml ps` e os logs de `site`.

**IA não responde:** confira se `ia` está `healthy`. Uma falha da IA não deve interromper o fluxo principal do servidor.

**ESP32 não envia dados:** confira rede 2,4 GHz, URL com o IP local do computador, firewall/porta 3000 e monitor serial do PlatformIO.

**Sensor mostra “Sem dedo” ou “A calcular”:** confira posicionamento, conexão elétrica e estabilidade das leituras. O modelo não analisa valores inválidos.

**Modelos não encontrados no build Docker:** confira a existência dos dois arquivos `.joblib` nos caminhos documentados e do `catalogo_interativo.json`.

## 9. Contribuindo com alterações

O repositório oficial é **[Josecleber/BioIoT-Completo](https://github.com/Josecleber/BioIoT-Completo)**.

Para propor uma alteração sem modificar diretamente a versão oficial:

1. Na página do GitHub, clique em **Fork** para criar sua cópia.
2. Faça as alterações em uma branch da sua cópia e registre seus commits.
3. Abra um **Pull Request** para a branch `main` do repositório oficial.
4. Descreva o que mudou, como testar e, se possível, inclua capturas ou logs dos testes.
5. O mantenedor revisará a proposta e decidirá se incorpora as alterações.

Não inclua senhas, informações reais de pacientes, bancos SQLite de produção, arquivos temporários de backup ou dados de terceiros sem autorização.

## 10. Limitações científicas

Os dois modelos foram avaliados de maneira **experimental**, sem validação clínica:

| Indicador | BIDMC original | Adaptado ao ESP32 |
|---|---:|---:|
| Janelas de treino | 326 | 318 |
| Janelas de teste | 88 | 87 |
| Janelas sinalizadas no teste | 4 | 4 |
| Medições por janela | 60 | 28 |

A contagem de janelas sinalizadas **não** é uma métrica de acurácia clínica. As condições do MAX30102 podem diferir das condições de aquisição dos dados BIDMC. O projeto é uma demonstração acadêmica de integração entre IoT, desenvolvimento web, persistência e aprendizado de máquina.
