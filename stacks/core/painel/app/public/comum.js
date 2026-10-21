// O que todas as telas usam: montar elementos, falar com a API, os textos de estado e os módulos do
// aparelho. As três funções da casca (atualizar, telaAtual, mostrarEntrada) o app.js liga ao começar.
import { seteSegmentos } from "./visor.js";

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

export const consultar = (nome, params = {}) => api("POST", `/api/acao/${nome}`, { params });

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

export const gb = (mb) => `${(mb / 1024).toFixed(1)} GB`;
export const data = (ms) => new Date(ms).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
export const dinheiro = (usd) => `US$ ${Number(usd).toFixed(2)}`;

export function medidor(fracao, alerta = 0.85) {
  const pct = Math.max(0, Math.min(1, fracao || 0));
  const barra = h("span");
  barra.style.width = `${(pct * 100).toFixed(0)}%`; // pelo CSSOM: a CSP barra o atributo style
  return h("div", { class: `medidor${pct >= alerta ? " alto" : ""}` }, barra);
}

// um módulo do aparelho: o título e, à direita, a etiqueta com o que ele mede (sempre dado de verdade)
export function modulo(titulo, codigo, ...conteudo) {
  return h("section", { class: "modulo" },
    h("header", { class: "modulo-topo" }, h("h2", null, titulo),
      h("span", { class: "etiqueta" }, codigo && h("span", { class: "codigo" }, codigo))), ...conteudo);
}

// o código de peça de cada módulo: a tela e a posição dele no painel (IN-01 é o primeiro do Início),
// refeito sempre que um módulo entra, sai ou se refaz sozinho
const PREFIXOS = {
  inicio: "IN", aprovacoes: "AP", agenda: "AG", servicos: "SV", sistema: "SY", arquivos: "AR",
  pc: "PC", lab: "LB", atividade: "AT", historico: "HI", ajustes: "AJ",
};

function numerarModulos() {
  const prefixo = PREFIXOS[$("#tela").dataset.tela] ?? "AT";
  [...document.querySelectorAll("#tela > .modulo")].forEach((m, i) => {
    const etiqueta = m.querySelector(".modulo-topo .etiqueta");
    if (!etiqueta) return;
    const codigo = `${prefixo}-${String(i + 1).padStart(2, "0")}`;
    const peca = etiqueta.querySelector(".peca") ?? etiqueta.appendChild(h("span", { class: "peca" }));
    if (peca.textContent !== codigo) peca.textContent = codigo;
  });
}
new MutationObserver(numerarModulos).observe($("#tela"), { childList: true });

export function cartao(titulo, ...conteudo) {
  return modulo(titulo, null, ...conteudo);
}

// um número em 7 segmentos num visorzinho dentro do módulo
export function mostrador(texto, unidade) {
  return h("div", { class: "mostrador-numero" }, seteSegmentos(texto), unidade && h("span", { class: "celula-unidade" }, unidade));
}

export function falha(r) {
  return h("p", { class: "erro" }, r.erro ?? "erro");
}

export function linha(rotulo, valor, extra) {
  return h("div", { class: "linha" }, h("span", { class: "rotulo" }, rotulo), h("span", null, valor), extra);
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
// semEstado: só "há 3 dias · …" (para o lado de um LED que já diz o estado)
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

export function estadoContainer(c) {
  const ok = containerOk(c);
  return h("span", { class: `selo ${ok ? "ok" : "ruim"}` }, ok ? "no ar" : c.estado === "running" ? "com problema" : ESTADOS_DOCKER[c.estado] ?? c.estado);
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
