// O que todas as telas usam: montar elementos, falar com a API, os textos de estado e os módulos do
// painel. As três funções da casca (atualizar, telaAtual, mostrarEntrada) o app.js liga ao começar.
import { chave, faixa } from "./desenhos.js";

export { vazio } from "./ornamentos.js";

export const NOMES = {
  "servico.reiniciar": "Reiniciar serviço",
  "pc.ligar": "Ligar o PC",
  "pc.desligar": "Desligar o PC",
  "pc.reiniciar": "Reiniciar o PC",
  "pc.cancelar": "Cancelar desligamento do PC",
  "app.reiniciar": "Reiniciar app do lab",
  "app.parar": "Parar app do lab",
  "app.publicar": "Publicar app do lab",
  "app.cancelar": "Cancelar no lab",
  "app.apagar": "Apagar do lab",
  "app.restaurar": "Restaurar da lixeira",
  "app.comando": "Comando no app",
  "claude.tarefa": "Trabalho do Claude Code",
  "claude.cancelar": "Cancelar trabalho do Claude Code",
  "stack.editar": "Gravar arquivo da stack",
  "stack.aplicar": "Aplicar stack",
  "stack.desfazer": "Desfazer edição da stack",
  "aprovacoes.decidir": "Decisão",
};
export const ORDEM_ZONAS = ["core", "ai", "agents", "apps", "lab", "prod"];
export const TERMINADOS = new Set(["concluido", "falhou", "recusado", "expirado", "cancelado"]);
export const TIQUE = 10_000;

export const $ = (seletor) => document.querySelector(seletor);

export function h(tag, atributos, ...filhos) {
  const el = document.createElement(tag);
  for (const [chave, valor] of Object.entries(atributos ?? {})) {
    if (valor === false || valor == null) continue;
    if (chave.startsWith("on")) el.addEventListener(chave.slice(2), valor);
    else if (chave === "class") el.className = valor;
    else el.setAttribute(chave, valor === true ? "" : valor);
  }
  for (const filho of filhos.flat(Infinity)) {
    if (filho == null || filho === false) continue;
    el.append(filho instanceof Node ? filho : String(filho));
  }
  return el;
}

// as três funções da casca: o app.js liga as de verdade ao começar (as telas só chamam)
export let atualizar = async () => {};
export let telaAtual = () => "inicio";
export let mostrarEntrada = () => {};
export function ligarCasca(funcoes) {
  ({ atualizar, telaAtual, mostrarEntrada } = funcoes);
}

// --- API -------------------------------------------------------------------------------------

export async function api(metodo, caminho, corpo) {
  let resposta;
  try {
    resposta = await fetch(caminho, {
      method: metodo,
      credentials: "same-origin",
      headers: corpo ? { "Content-Type": "application/json", "X-Atena": "1" } : {},
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
  } catch {
    return { status: 0, ok: false, erro: "sem conexão com o servidor (o Tailscale está ligado?)" };
  }
  const dados = await resposta.json().catch(() => ({ ok: false, erro: `resposta inválida (${resposta.status})` }));
  if (resposta.status === 401 && caminho !== "/api/entrar") mostrarEntrada();
  return { status: resposta.status, ...dados };
}

// a mesma consulta pedida duas vezes ao mesmo tempo (o Início e os pontos das zonas no topo, por exemplo) vai uma
// vez só ao executor; o que muda algo (as de NOMES) nunca se junta
const emCurso = new Map();
export function consultar(nome, params = {}) {
  if (nome in NOMES) return api("POST", `/api/acao/${nome}`, { params });
  const chave = `${nome} ${JSON.stringify(params)}`;
  if (!emCurso.has(chave)) emCurso.set(chave, api("POST", `/api/acao/${nome}`, { params }).finally(() => emCurso.delete(chave)));
  return emCurso.get(chave);
}

// ações que mudam algo: confirma, pede, acompanha o pedido (202) e avisa o resultado.
// acompanhar = false: só avisa que começou (o trabalho do Claude Code leva de minutos a horas)
export async function mudar(nome, params, pergunta, acompanhar = true) {
  if (pergunta && !confirm(pergunta)) return null;
  const titulo = NOMES[nome] ?? nome;
  avisar(`${titulo}…`);
  let r = await consultar(nome, params);
  if (r.status === 202 && r.pedido && !acompanhar) {
    avisar(`${titulo}: começou (pedido ${r.pedido})`, "ok");
    return r;
  }
  let terminou = r.status !== 202;
  if (r.status === 202 && r.pedido) {
    for (let i = 0; i < 10 && r.ok !== false; i++) {
      const p = await api("GET", `/api/pedido/${r.pedido}?esperar=30`);
      if (p.ok === false) { r = p; terminou = true; break; }
      if (TERMINADOS.has(p.pedido.estado)) {
        r = p.pedido.estado === "concluido" ? { ok: true, resultado: p.pedido.resultado } : { ok: false, erro: p.pedido.erro ?? p.pedido.estado };
        terminou = true;
        break;
      }
    }
  }
  if (r.ok === false) avisar(`${titulo}: ${r.erro}`, "erro");
  else if (!terminou) avisar(`${titulo}: ainda em andamento; o Histórico mostra quando terminar`);
  else avisar(`${titulo}: feito`, "ok");
  return r;
}

// --- utilidades de tela -----------------------------------------------------------------------

export function avisar(texto, tipo = "") {
  const aviso = h("div", { class: `aviso ${tipo}` }, texto);
  // com a janela aberta, o aviso vai dentro dela (a janela fica por cima de tudo)
  ($("#janela").open ? $("#janela-avisos") : $("#avisos")).append(aviso);
  setTimeout(() => aviso.remove(), tipo === "erro" ? 8000 : 4000);
}

// números como se escreve aqui: 15,0 GB, US$ 0,98, 1.304 RPM
export const num = (n, casas = 0) => Number(n).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
export const gb = (mb) => `${num(mb / 1024, 1)}\u00a0GB`;
export const data = (ms) => new Date(ms).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
export const dinheiro = (usd) => `US$\u00a0${num(usd, 2)}`;
export const plural = (n, um, varios) => `${num(n)} ${n === 1 ? um : varios}`;

// o docker stats escreve "54.68MiB", "1.2GiB" e "0.01%": aqui sai "54,7 MB", "1,2 GB" e "0,0%"
const UNIDADES_DOCKER = { B: "B", kB: "KB", KiB: "KB", MB: "MB", MiB: "MB", GB: "GB", GiB: "GB", TB: "TB", TiB: "TB" };
export function tamanhoDocker(texto) {
  const m = String(texto).match(/^([\d.]+)\s*([kKMGT]?i?B)$/);
  if (!m || !UNIDADES_DOCKER[m[2]]) return texto;
  const n = Number(m[1]);
  return `${num(n, n >= 100 || m[2] === "B" ? 0 : 1)}\u00a0${UNIDADES_DOCKER[m[2]]}`;
}
export function porcento(texto) {
  const n = parseFloat(texto);
  return Number.isFinite(n) ? `${num(n, n >= 10 ? 0 : 1)}%` : texto;
}

// a faixa de meandro pintada até a fração; perto do limite fica ocre, passado dele, cinábrio
export function medidor(fracao, alerta = 0.85) {
  const pct = Math.max(0, Math.min(1, fracao || 0));
  const barra = h("span");
  barra.style.width = `${(pct * 100).toFixed(0)}%`; // pelo CSSOM: a CSP barra o atributo style
  return h("div", { class: `medidor${pct >= alerta ? " alto" : pct >= alerta * 0.85 ? " perto" : ""}`, role: "img", "aria-label": `${Math.round(pct * 100)}%` }, barra);
}

// um módulo: a chave do meandro, o título em letra de inscrição e, à direita, o que ele mede (sempre
// dado de verdade)
export function modulo(titulo, codigo, ...conteudo) {
  return h("section", { class: "modulo" },
    h("header", { class: "modulo-topo" }, chave(), h("h2", null, titulo), h("span", { class: "regua" }),
      codigo && h("span", { class: "codigo" }, codigo)), ...conteudo);
}

export function cartao(titulo, ...conteudo) {
  return modulo(titulo, null, ...conteudo);
}

// a tela que ainda não chegou: as placas postas, o pintor fazendo o meandro e, no lugar de cada linha, a
// hachura sendo traçada e apagada, uma linha depois da outra, enquanto o dado chega
export function esqueleto() {
  const marca = (k, curta) => {
    const el = h("span", { class: `marca-vazia${curta ? " curta" : ""}` });
    el.style.setProperty("--k", k);
    return el;
  };
  return [3, 5].map((linhas, i) => h("section", { class: "modulo esqueleto", "aria-hidden": "true" },
    i === 0 ? faixa() : marca(0, true),
    Array.from({ length: linhas }, (_, k) => marca(k + 1, k % 3 === 2))));
}

// o que espera uma resposta curta (abrir um arquivo, procurar, rodar um comando): o texto e a hachura
export const carregando = (texto) => h("p", { class: "fraco carregando" }, texto);

// um número na letra de pedra, com a unidade ao lado (o gasto do mês, a próxima vez da agenda)
export function numeroGrande(texto, unidade) {
  return h("p", { class: "numero-grande" }, texto, unidade && h("small", null, unidade));
}

export function falha(r) {
  return h("p", { class: "erro" }, r.erro ?? "erro");
}

export function linha(rotulo, valor, extra) {
  return h("div", { class: "linha" }, h("span", { class: "rotulo" }, rotulo), h("span", null, valor), extra);
}

// Uma linha de lista, igual em todas as telas: o ponto do estado (o texto dele vem no detalhe), o nome,
// o detalhe embaixo e as teclas à direita (num módulo estreito, várias teclas descem para baixo do
// nome). O extra ocupa a largura toda embaixo: um resumo, um registro, os "detalhes".
export function item({ led, nome, detalhe, acoes, extra, classe }) {
  const teclas = [acoes].flat(Infinity).filter(Boolean);
  const embaixo = [extra].flat(Infinity).filter(Boolean);
  return h("li", { class: ["item", !led && "sem-led", classe].filter(Boolean).join(" "), "data-acoes": teclas.length || null },
    led && h("span", { class: `led ${led}` }),
    h("div", { class: "item-texto" }, h("div", { class: "item-nome" }, nome), detalhe && h("div", { class: "item-detalhe" }, detalhe)),
    teclas.length > 0 && h("div", { class: "item-acoes" }, teclas),
    embaixo.length > 0 && h("div", { class: "item-extra" }, embaixo));
}

// vazio: o texto (ou o vazio() com a vinheta) quando a lista não tem nada
export function itens(lista, vazio, classe) {
  const linhas = [lista].flat(Infinity).filter(Boolean);
  if (!linhas.length) return vazio && (vazio instanceof Node ? vazio : h("p", { class: "fraco" }, vazio));
  return h("ul", { class: `itens${classe ? ` ${classe}` : ""}` }, linhas);
}

// o ponto de cada estado de pedido: malaquita terminou bem, azul em andamento, cinábrio o resto
export const ledEstado = (estado) => (estado === "concluido" ? "ok" : TERMINADOS.has(estado) || estado === "perdida" ? "ruim" : "info");

// um campo de formulário: o rótulo em cima, o controle embaixo (largo: a linha toda)
export function campo(rotulo, controle, largo = false) {
  return h("label", { class: `campo${largo ? " largo" : ""}` }, h("span", { class: "rotulo" }, rotulo), controle);
}

export const containerOk = (c) => c.estado === "running" && !/unhealthy/.test(c.status);

// os estados dos pedidos, como o executor guarda, no português da tela
const ESTADOS = {
  concluido: "concluído", falhou: "falhou", recusado: "recusado", expirado: "expirado", cancelado: "cancelado",
  executando: "rodando", aguardando: "esperando", perguntando: "perguntando", perdida: "perdida", planejando: "planejando",
};
export const estadoTexto = (e) => ESTADOS[e] ?? e;

const ESTADOS_DOCKER = { running: "no ar", exited: "parado", restarting: "reiniciando", paused: "pausado", created: "criado", dead: "morto", removing: "saindo" };
const UNIDADES = { second: ["s", "s"], minute: ["min", "min"], hour: ["h", "h"], day: ["dia", "dias"], week: ["semana", "semanas"], month: ["mês", "meses"], year: ["ano", "anos"] };

// "3 days", "About an hour", "Less than a second" (como o Docker escreve) → "3 dias", "1 h", "agora"
function tempoDocker(texto) {
  if (/^less than a second/i.test(texto)) return null;
  const m = texto.match(/^(\d+|about an?|an?) (second|minute|hour|day|week|month|year)s?$/i);
  if (!m) return texto;
  const n = /^\d+$/.test(m[1]) ? Number(m[1]) : 1;
  const [um, varios] = UNIDADES[m[2].toLowerCase()];
  return `${n} ${n === 1 ? um : varios}`;
}

// "Up 3 days (unhealthy)", "Exited (137) 5 hours ago" → "no ar há 3 dias · saúde falhando", "parado há 5 h (erro 137)";
// semEstado: só "há 3 dias · …" (para o lado de um ponto que já diz o estado)
export function statusDocker(status, semEstado = false) {
  let m = status.match(/^Up (.+?)(?: \((healthy|unhealthy|health: starting)\))?$/);
  if (m) {
    const ha = tempoDocker(m[1]);
    const saude = { healthy: " · saudável", unhealthy: " · verificação de saúde falhando", "health: starting": " · verificação começando" }[m[2]] ?? "";
    return `${semEstado ? "" : "no ar "}${ha ? `há ${ha}` : "agora"}${saude}`;
  }
  m = status.match(/^(Exited|Restarting) \((-?\d+)\) (.+) ago$/);
  if (m) {
    const ha = tempoDocker(m[3]);
    const codigo = m[2] === "0" ? "" : ` (erro ${m[2]})`;
    return `${semEstado ? "" : `${m[1] === "Exited" ? "parado" : "reiniciando"} `}${ha ? `há ${ha}` : "agora"}${codigo}`;
  }
  return semEstado ? "" : ESTADOS_DOCKER[status.toLowerCase()] ?? status;
}

// --- central de aprovações e atividade do executor (os tempos do executor vêm em segundos) ---------

export const hora = (s) => new Date(s * 1000).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });

// executor antigo ou token do painel sem as ações da central
export function semCentral(r) {
  if (r.status !== 403 && r.status !== 404) return null;
  return h("p", { class: "fraco" }, "A central precisa do executor novo e das ações aprovacoes.lista, aprovacoes.decidir e atividade.lista no token do painel (rode o instalador com --painel).");
}

// --- sistema: sensores, processos, rede e o registro do systemd ---------------------------------
// Cada cartão se refaz sozinho (botão Atualizar, filtros), sem recarregar a tela toda.

// token do painel sem a ação (instalado antes desta versão)
export function semAcao(r, nome) {
  if (r.status !== 403) return null;
  return h("p", { class: "fraco" }, `O token do painel ainda não tem ${nome} (rode o instalador com --painel).`);
}

export function botaoAtualizar(refazer) {
  return h("div", { class: "botoes" }, h("button", { type: "button", class: "discreto", onclick: (evento) => {
    evento.currentTarget.disabled = true;
    refazer();
  } }, "Atualizar"));
}

export function abrirJanela(titulo, ...conteudo) {
  $("#janela-titulo").textContent = titulo;
  $("#janela-corpo").replaceChildren(...conteudo.flat(Infinity).filter(Boolean));
  if (!$("#janela").open) $("#janela").showModal();
}
