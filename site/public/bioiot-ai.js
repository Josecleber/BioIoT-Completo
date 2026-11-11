
/*
 * BIOIOT AI EXPERIENCE
 * Demonstração científica com dados históricos.
 * Independente do monitoramento em tempo real.
 */

(() => {
    "use strict";

    const URL_CATALOGO =
        "/bioiot-ai/catalogo_interativo.json";

    const NS = "http://www.w3.org/2000/svg";

    const nomesCaracteristicas = {
        pulse_media: "Pulso médio",
        pulse_desvio: "Desvio do pulso",
        pulse_minimo: "Pulso mínimo",
        pulse_maximo: "Pulso máximo",
        pulse_amplitude: "Amplitude do pulso",
        pulse_tendencia: "Tendência do pulso",
        spo2_media: "SpO₂ média",
        spo2_desvio: "Desvio da SpO₂",
        spo2_minimo: "SpO₂ mínima",
        spo2_maximo: "SpO₂ máxima",
        spo2_amplitude: "Amplitude da SpO₂",
        spo2_tendencia: "Tendência da SpO₂"
    };

    let catalogo = null;

    function elemento(id) {
        return document.getElementById(id);
    }

    function texto(id, valor) {
        const alvo = elemento(id);

        if (alvo) {
            alvo.textContent = String(valor);
        }
    }

    function numero(valor, casas = 2) {
        return Number(valor).toLocaleString("pt-BR", {
            minimumFractionDigits: casas,
            maximumFractionDigits: casas
        });
    }

    function criarSvg(tag, atributos = {}, conteudo = "") {
        const el = document.createElementNS(NS, tag);

        for (const [chave, valor] of Object.entries(atributos)) {
            el.setAttribute(chave, String(valor));
        }

        if (conteudo) {
            el.textContent = conteudo;
        }

        return el;
    }

    function desenharGrafico(id, serie, campo, cor) {
        const svg = elemento(id);

        if (!svg) return;

        svg.replaceChildren();

        const valores = serie.map(ponto => Number(ponto[campo]));

        if (
            valores.length !== 60 ||
            !valores.every(Number.isFinite)
        ) {
            svg.appendChild(
                criarSvg("text", {
                    x: 24,
                    y: 90,
                    fill: "#cbd5e1",
                    "font-size": 17
                }, "Dados insuficientes para o gráfico")
            );
            return;
        }

        const largura = 700;
        const altura = 180;

        const esquerda = 48;
        const direita = largura - 15;
        const topo = 15;
        const fundo = altura - 30;

        const minimoReal = Math.min(...valores);
        const maximoReal = Math.max(...valores);

        const margem = Math.max(
            (maximoReal - minimoReal) * 0.15,
            campo === "pulse" ? 2 : 0.5
        );

        const minimo = minimoReal - margem;
        const maximo = maximoReal + margem;

        const x = indice =>
            esquerda + (indice / 59) * (direita - esquerda);

        const y = valor =>
            fundo - ((valor - minimo) / (maximo - minimo))
            * (fundo - topo);

        for (let i = 0; i <= 3; i++) {
            const posY = topo + i * (fundo - topo) / 3;

            svg.appendChild(
                criarSvg("line", {
                    x1: esquerda,
                    y1: posY,
                    x2: direita,
                    y2: posY,
                    stroke: "#334155",
                    "stroke-width": 1
                })
            );

            const valorEixo =
                maximo - i * (maximo - minimo) / 3;

            svg.appendChild(
                criarSvg("text", {
                    x: esquerda - 8,
                    y: posY + 4,
                    fill: "#94a3b8",
                    "font-size": 12,
                    "text-anchor": "end"
                }, numero(valorEixo, 0))
            );
        }

        const pontos = valores.map((valor, indice) =>
            `${indice === 0 ? "M" : "L"} ` +
            `${x(indice).toFixed(2)} ${y(valor).toFixed(2)}`
        ).join(" ");

        svg.appendChild(
            criarSvg("path", {
                d: pontos,
                stroke: cor,
                "stroke-width": 3,
                fill: "none",
                "stroke-linejoin": "round",
                "stroke-linecap": "round"
            })
        );

        for (const segundo of [0, 15, 30, 45, 59]) {
            svg.appendChild(
                criarSvg("text", {
                    x: x(segundo),
                    y: altura - 8,
                    fill: "#94a3b8",
                    "font-size": 12,
                    "text-anchor": "middle"
                }, `${segundo}s`)
            );
        }
    }

    function exibirExplicacoes(caso) {
        const container = elemento("ai-explanation-list");

        if (!container) return;

        container.replaceChildren();

        const itens = (caso.sensibilidade || [])
            .filter(item =>
                Number.isFinite(Number(item.mudanca_score))
            );

        if (itens.length === 0) {
            const p = document.createElement("p");
            p.className = "ai-secondary-text";
            p.textContent =
                "Esta janela não foi sinalizada. " +
                "Nenhuma análise individual de sensibilidade " +
                "foi calculada para este caso.";

            container.appendChild(p);
            return;
        }

        const maior = Math.max(
            ...itens.map(item =>
                Math.abs(Number(item.mudanca_score))
            ),
            0.000001
        );

        for (const item of itens) {
            const mudanca = Number(item.mudanca_score);

            const linha = document.createElement("div");
            linha.className = "ai-feature-row";

            const nome = document.createElement("span");
            nome.textContent =
                nomesCaracteristicas[item.caracteristica] ||
                item.caracteristica;

            const trilha = document.createElement("div");
            trilha.className = "ai-feature-track";

            const preenchimento = document.createElement("div");
            preenchimento.className = "ai-feature-fill";

            preenchimento.style.width =
                `${Math.abs(mudanca) / maior * 100}%`;

            trilha.appendChild(preenchimento);

            const valor = document.createElement("strong");
            valor.textContent =
                `${mudanca >= 0 ? "+" : ""}` +
                numero(mudanca, 5);

            linha.append(nome, trilha, valor);
            container.appendChild(linha);
        }
    }

    function selecionarCaso(indice) {
        if (!catalogo) return;

        const caso = catalogo.casos[indice];
        if (!caso) return;

        const atipico = caso.tipo === "padrao_atipico";

        const tituloExplicacao = document.querySelector(
            ".ai-explanation-panel h2"
        );

        if (tituloExplicacao) {
            tituloExplicacao.textContent = atipico
                ? "Por que o modelo sinalizou?"
                : "Por que este caso não foi sinalizado?";
        }

        const identificador =
            caso.arquivo.match(/bidmc_(\d+)_/i);

        const nome = identificador
            ? `BIDMC ${identificador[1]}`
            : caso.arquivo;

        texto("ai-case-title", nome);

        const inicio = Math.round(caso.inicio_segundo);

        texto(
            "ai-case-period",
            `Registro histórico • Segundos ${inicio} a ${inicio + 59}`
        );

        texto(
            "ai-pulse-average",
            `${numero(caso.pulse_media)} BPM`
        );

        texto(
            "ai-spo2-average",
            `${numero(caso.spo2_media)}%`
        );

        texto("ai-score-value", numero(caso.score, 5));

        texto(
            "ai-score-threshold",
            `Limiar experimental: ${numero(caso.limiar, 5)}`
        );

        const status = elemento("ai-case-status");

        if (status) {
            status.classList.toggle("atipico", atipico);
            status.textContent = atipico
                ? "Padrão atípico"
                : "Não sinalizado";
        }

        texto(
            "ai-interpretation-text",
            atipico
                ? "O modelo identificou uma sequência " +
                "estatisticamente incomum em relação " +
                "às características aprendidas. " +
                "Isso não indica uma doença nem " +
                "determina a condição de saúde da pessoa."
                : "Esta janela não ultrapassou o limiar " +
                "experimental de sinalização do modelo. " +
                "Isso não significa que seja um " +
                "registro clinicamente normal."
        );

        desenharGrafico(
            "ai-pulse-chart",
            caso.serie_temporal,
            "pulse",
            "#fb7185"
        );

        desenharGrafico(
            "ai-spo2-chart",
            caso.serie_temporal,
            "spo2",
            "#38bdf8"
        );

        exibirExplicacoes(caso);

        const botoes = elemento("ai-case-list")
            ?.querySelectorAll(".ai-case-button") || [];

        botoes.forEach((botao, posicao) => {
            const ativo = posicao === indice;
            botao.classList.toggle("active", ativo);
            botao.setAttribute(
                "aria-pressed",
                String(ativo)
            );
        });
    }

    function criarSeletores() {
        const container = elemento("ai-case-list");

        if (!container) return;

        container.replaceChildren();

        catalogo.casos.forEach((caso, indice) => {
            const botao = document.createElement("button");
            botao.type = "button";
            botao.className = "ai-case-button";

            const identificador =
                caso.arquivo.match(/bidmc_(\d+)_/i);

            const titulo = document.createElement("span");
            titulo.textContent = identificador
                ? `BIDMC ${identificador[1]}`
                : caso.arquivo;

            const subtitulo = document.createElement("small");
            subtitulo.textContent =
                caso.tipo === "padrao_atipico"
                    ? "Sinalizado pela IA"
                    : "Não sinalizado";

            botao.append(titulo, subtitulo);

            botao.addEventListener(
                "click",
                () => selecionarCaso(indice)
            );

            container.appendChild(botao);
        });
    }

    async function inicializarBioIoTAI() {
        const carregamento = elemento("ai-loading");
        const conteudo = elemento("ai-content");

        if (!carregamento || !conteudo) return;

        try {
            const resposta = await fetch(URL_CATALOGO, {
                cache: "no-store"
            });

            if (!resposta.ok) {
                throw new Error(`HTTP ${resposta.status}`);
            }

            const dados = await resposta.json();

            if (
                !Array.isArray(dados.casos) ||
                dados.casos.length !== 6 ||
                !dados.casos.every(caso =>
                    Array.isArray(caso.serie_temporal) &&
                    caso.serie_temporal.length === 60
                )
            ) {
                throw new Error(
                    "Catálogo científico incompleto."
                );
            }

            catalogo = dados;

            texto(
                "ai-training-count",
                dados.janelas_treinamento
            );

            texto(
                "ai-test-count",
                dados.janelas_teste
            );

            texto(
                "ai-flagged-count",
                dados.total_sinalizadas_teste
            );

            criarSeletores();
            selecionarCaso(0);

            conteudo.hidden = false;
            carregamento.hidden = true;

        } catch (erro) {
            console.error(
                "[BioIoT AI] Falha ao carregar:",
                erro
            );

            carregamento.textContent =
                "Não foi possível carregar os dados científicos. " +
                "Verifique o catálogo e tente atualizar a página.";
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            inicializarBioIoTAI,
            { once: true }
        );
    } else {
        inicializarBioIoTAI();
    }
})();
