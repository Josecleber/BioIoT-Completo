
(() => {
    "use strict";

    const DISPOSITIVO = "ESP32-BANCADA-01";
    const URL = `/api/ia/estado/${encodeURIComponent(DISPOSITIVO)}`;

    let ultimaAnalise = null;

    function elemento(id) {
        return document.getElementById(id);
    }

    function escrever(id, valor) {
        const destino = elemento(id);
        if (destino) destino.textContent = String(valor);
    }

    function formatar(valor, casas = 2) {
        const numero = Number(valor);
        return Number.isFinite(numero)
            ? numero.toLocaleString("pt-BR", {
                minimumFractionDigits: casas,
                maximumFractionDigits: casas
            })
            : "—";
    }

    function montarPainel() {
        const area = document.querySelector(
            "#bioiot-ai .ai-experience"
        );

        if (!area || elemento("ai-live-panel")) return;

        const painel = document.createElement("section");
        painel.id = "ai-live-panel";
        painel.className = "ai-live-panel";

        // Estrutura fixa: nenhum dado externo entra no HTML.
        painel.innerHTML = `
            <div class="ai-live-header">
                <div>
                    <span class="ai-live-eyebrow">
                        MODELO EXPERIMENTAL • MAX30102
                    </span>
                    <h2>Inteligência artificial ao vivo</h2>
                    <p>
                        Análise automática de janelas de medições
                        recebidas do ESP32.
                    </p>
                </div>
                <span id="ai-live-status" class="ai-live-status">
                    Conectando
                </span>
            </div>

            <div class="ai-live-progress-info">
                <span id="ai-live-etapa">Aguardando sensor</span>
                <strong id="ai-live-count">0 / 28</strong>
            </div>

            <div class="ai-live-track"
                 role="progressbar"
                 aria-label="Progresso da coleta"
                 aria-valuemin="0"
                 aria-valuemax="28"
                 aria-valuenow="0"
                 id="ai-live-progress">
                <div id="ai-live-fill"></div>
            </div>

            <div class="ai-live-results">
                <div class="ai-live-metric">
                    <span>Pontuação da IA</span>
                    <strong id="ai-live-score">—</strong>
                </div>
                <div class="ai-live-metric">
                    <span>Limiar experimental</span>
                    <strong id="ai-live-limiar">—</strong>
                </div>
                <div class="ai-live-metric">
                    <span>Pulso médio da janela</span>
                    <strong id="ai-live-bpm">—</strong>
                </div>
                <div class="ai-live-metric">
                    <span>SpO₂ média da janela</span>
                    <strong id="ai-live-spo2">—</strong>
                </div>
            </div>

            <div class="ai-live-conclusion">
                <strong id="ai-live-classificacao">
                    Nenhuma janela analisada nesta sessão.
                </strong>
                <p id="ai-live-details">
                    A análise começa após 28 medições válidas.
                </p>
            </div>

            <p class="ai-live-disclaimer">
                Resultado estatístico experimental, sem finalidade
                diagnóstica. O modelo foi treinado com dados BIDMC
                adaptados à cadência do ESP32; sua precisão clínica
                com o MAX30102 não foi estabelecida.
            </p>
        `;

        const cabecalho = area.querySelector(".ai-header");

        if (cabecalho) {
            cabecalho.insertAdjacentElement("afterend", painel);
        } else {
            area.prepend(painel);
        }
    }

    function atualizarProgresso(quantidade, total) {
        const maximo = 28;
        const atual = Math.max(
            0,
            Math.min(maximo, Number(quantidade) || 0)
        );

        escrever("ai-live-count", `${atual} / ${maximo}`);

        const barra = elemento("ai-live-fill");
        if (barra) {
            barra.style.width = `${atual / maximo * 100}%`;
        }

        const progresso = elemento("ai-live-progress");

        if (progresso) {
            progresso.setAttribute("aria-valuenow", String(atual));
        }
    }

    function mostrarResultado(resultado, anterior) {
        if (!resultado) {
            ultimaAnalise = null;
            escrever("ai-live-score", "—");
            escrever("ai-live-limiar", "—");
            escrever("ai-live-bpm", "—");
            escrever("ai-live-spo2", "—");
            escrever(
                "ai-live-classificacao",
                "Nenhuma janela analisada nesta sessão."
            );
            escrever(
                "ai-live-details",
                "Aguardando medições válidas."
            );
            return;
        }

        ultimaAnalise = resultado;

        const caracteristicas = resultado.caracteristicas || {};

        escrever("ai-live-score", formatar(resultado.score, 4));
        escrever("ai-live-limiar", formatar(resultado.limiar, 4));

        escrever(
            "ai-live-bpm",
            `${formatar(caracteristicas.pulse_media, 1)} BPM`
        );

        escrever(
            "ai-live-spo2",
            `${formatar(caracteristicas.spo2_media, 1)}%`
        );

        escrever(
            "ai-live-classificacao",
            resultado.padrao_atipico
                ? "Padrão estatístico sinalizado"
                : "Padrão não sinalizado pelo modelo"
        );

        escrever(
            "ai-live-details",
            `${anterior ? "Resultado da janela anterior. " : ""}` +
            `${resultado.amostras} medições em ` +
            `${formatar(resultado.duracao_real_segundos, 1)} segundos.`
        );
    }

    function atualizarEstado(dados) {
        const status = dados.status || "aguardando";
        const coletadas = dados.amostras_coletadas || 0;

        const nomes = {
            aguardando: "Aguardando",
            coletando: "Coletando",
            analisando: "Analisando",
            analisado: "Concluído",
            indisponivel: "IA indisponível"
        };

        escrever("ai-live-status", nomes[status] || status);

        const etiqueta = elemento("ai-live-status");
        if (etiqueta) etiqueta.dataset.status = status;

        atualizarProgresso(coletadas, 28);

        const mensagens = {
            aguardando: "Aguardando medição válida do ESP32",
            coletando: "Coletando medições reais",
            analisando: "Processando janela no Isolation Forest",
            analisado: "Última análise concluída",
            indisponivel: "Não foi possível concluir a análise"
        };

        escrever("ai-live-etapa", mensagens[status] || status);

        const anterior = Boolean(
            dados.resultado_da_janela_anterior
        );

        if (dados.resultado) {
            mostrarResultado(dados.resultado, anterior);
        } else if (ultimaAnalise !== null) {
            mostrarResultado(null, false);
        }

        if (status === "indisponivel" && dados.mensagem) {
            escrever(
                "ai-live-etapa",
                "Serviço experimental indisponível"
            );
        }
    }

    async function consultar() {
        try {
            const resposta = await fetch(URL, {
                cache: "no-store"
            });

            if (!resposta.ok) {
                throw new Error(`HTTP ${resposta.status}`);
            }

            const dados = await resposta.json();
            atualizarEstado(dados);
        } catch (erro) {
            escrever("ai-live-status", "Sem conexão");
            escrever(
                "ai-live-etapa",
                "Não foi possível consultar o servidor"
            );

            const etiqueta = elemento("ai-live-status");

            if (etiqueta) {
                etiqueta.dataset.status = "indisponivel";
            }

            console.warn("[BioIoT AI Live]", erro.message);
        }
    }

    function iniciar() {
        montarPainel();
        consultar();

        // Apenas consulta a API. Não interfere no sensor.
        setInterval(consultar, 2500);
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            iniciar,
            { once: true }
        );
    } else {
        iniciar();
    }
})();
