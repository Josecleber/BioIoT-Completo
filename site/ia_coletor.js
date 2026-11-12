
"use strict";

// Coletor experimental independente do monitoramento.
const TOTAL_AMOSTRAS = 28;
const INTERVALO_MIN_MS = 1700;
const INTERVALO_MAX_MS = 2900;
const DURACAO_MIN_MS = 55000;
const DURACAO_MAX_MS = 65000;

function criarColetorIA(opcoes = {}) {
    const estados = new Map();

    const enviar = opcoes.enviar || (async (amostras) => {
        const resposta = await fetch(
            process.env.BIOIOT_AI_URL ||
            "http://ia:8001/analisar-esp32",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ amostras }),
                signal: AbortSignal.timeout(3000)
            }
        );

        const resultado = await resposta.json();

        if (!resposta.ok) {
            throw new Error(
                resultado.erro || `HTTP ${resposta.status}`
            );
        }

        return resultado;
    });

    function obter(dispositivo) {
        const estado = estados.get(dispositivo);

        if (!estado) {
            return {
                status: "aguardando",
                amostras_coletadas: 0
            };
        }

        return {
            status: estado.status,
            amostras_coletadas: estado.amostras.length,
            total_amostras: TOTAL_AMOSTRAS,
            resultado: estado.resultado,
            resultado_da_janela_anterior:
                estado.resultado !== null &&
                estado.status !== "analisado",
            mensagem: estado.mensagem
        };
    }

    function limpar(dispositivo) {
        estados.delete(dispositivo);
    }

    function pausar(dispositivo) {
        const estado = estados.get(dispositivo);

        if (!estado) return;

        estado.amostras = [];
        estado.pausado = true;
        estado.status = "aguardando";
        estado.mensagem = null;
    }

    function receber({
        dispositivo,
        sessaoId = "",
        bpm,
        spo2,
        instante = Date.now()
    }) {
        if (
            !Number.isFinite(bpm) ||
            !Number.isFinite(spo2) ||
            !Number.isFinite(instante) ||
            bpm < 40 || bpm > 160 ||
            spo2 < 75 || spo2 > 100
        ) {
            limpar(dispositivo);
            return;
        }

        let estado = estados.get(dispositivo);

        if (!estado || estado.sessaoId !== sessaoId) {
            estado = {
                sessaoId,
                amostras: [],
                status: "coletando",
                resultado: null,
                mensagem: null,
                emAnalise: false
            };
            estados.set(dispositivo, estado);
        }

        if (estado.emAnalise) {
            return;
        }

        estado.pausado = false;

        const anterior = estado.amostras.at(-1);

        if (anterior) {
            const intervalo = instante - anterior.instante;

            if (
                intervalo < INTERVALO_MIN_MS ||
                intervalo > INTERVALO_MAX_MS
            ) {
                estado.amostras = [];
                estado.status = "coletando";
                estado.mensagem =
                    "Janela reiniciada: intervalo irregular.";
            }
        }

        if (estado.status !== "coletando") {
            estado.status = "coletando";
            estado.mensagem = null;
        }

        estado.amostras.push({ instante, bpm, spo2 });

        if (estado.amostras.length < TOTAL_AMOSTRAS) {
            return;
        }

        const inicio = estado.amostras[0].instante;
        const fim = estado.amostras.at(-1).instante;
        const duracao = fim - inicio;

        if (
            duracao < DURACAO_MIN_MS ||
            duracao > DURACAO_MAX_MS
        ) {
            estado.amostras = [];
            estado.status = "coletando";
            estado.mensagem =
                "Janela reiniciada: duração incompatível.";
            return;
        }

        const amostras = estado.amostras.map(a => ({
            segundo: Number(
                ((a.instante - inicio) / 1000).toFixed(3)
            ),
            pulse: a.bpm,
            spo2: a.spo2
        }));

        estado.emAnalise = true;
        estado.status = "analisando";
        estado.amostras = [];

        Promise.resolve()
            .then(() => enviar(amostras))
            .then(resultado => {
                if (estados.get(dispositivo) !== estado) return;

                estado.resultado = resultado;
                estado.status = estado.pausado
                    ? "aguardando"
                    : "analisado";
                estado.mensagem = null;
            })
            .catch(erro => {
                if (estados.get(dispositivo) !== estado) return;

                estado.status = "indisponivel";
                estado.mensagem = erro.message;
            })
            .finally(() => {
                estado.emAnalise = false;
            });
    }

    return { receber, obter, limpar, pausar };
}

module.exports = { criarColetorIA };
