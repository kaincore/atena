// Atena: as conversas dela (Telegram, painel, agenda) e os trabalhos do Claude Code que ela comanda, numa
// lista à esquerda, e a conversa aberta à direita (no celular, uma de cada vez). Nas conversas do painel,
// você conversa com ela: a resposta chega aos pedaços pelo pedido de atena.falar (GET /api/pedido com
// versao), com os passos que ela dá e o pedido de aprovação de um comando perigoso. As do Telegram e da
// agenda ficam só para ler. O que chega aos pedaços redesenha só a resposta, nunca a tela inteira.
import { api, atualizar, avisar, cartao, consultar, dinheiro, estadoTexto, falha, h, item, itens, ledEstado, modulo, num,
  plural, telaAtual, vazio } from "../comum.js";

const ORIGENS = { painel: "painel", telegram: "Telegram", agenda: "agenda", terminal: "terminal", whatsapp: "WhatsApp" };
const FILTROS = [["todas", "Todas"], ["painel", "Painel"], ["telegram", "Telegram"], ["agenda", "Agenda"], ["claude", "Claude Code"]];
const ESCOLHAS = { once: "Só desta vez", session: "Nesta conversa", always: "Sempre", deny: "Não" };
const FASES = { plano: "O plano", executar: "O trabalho" };
// uma conversa custa menos de um centavo: aí, quatro casas
const custo = (usd) => (usd < 0.01 ? `US$\u00a0${num(usd, 4)}` : dinheiro(usd));

// o que a tela lembra entre uma leitura e outra: o filtro, o que está aberto, o rascunho e a resposta que
// está chegando (envio: o pedido de atena.falar, com o texto, os passos, a aprovação e a versão)
const estado = { filtro: "todas", aberta: null, rascunho: "", envio: null, ultimoErro: null, registroAte: 300 };

// hoje às 14:05, ontem às 9:10, 28/10 às 9:10
function quandoFoi(segundos) {
  if (!segundos) return "";
  const d = new Date(segundos * 1000);
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const dias = Math.round((new Date().setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 86_400_000);
  if (dias === 0) return `hoje às ${hora}`;
  if (dias === 1) return `ontem às ${hora}`;
  return `${d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} às ${hora}`;
}

// --- o texto dela: parágrafos, listas, **negrito** e `código`, sem innerHTML ---------------------------
function emLinha(texto) {
  return texto.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`)/).filter(Boolean).map((s) =>
    s.startsWith("**") && s.endsWith("**") && s.length > 4 ? h("strong", null, s.slice(2, -2))
      : s.startsWith("`") && s.endsWith("`") && s.length > 2 ? h("code", null, s.slice(1, -1)) : s);
}

const ITEM = /^\s*([-*•]|\d+[.)])\s+/;

// cada bloco (separado por linha em branco) vira parágrafos e listas: as linhas seguidas que começam com
// "- " ou "1." são uma lista; as outras, um parágrafo com as quebras de linha dela
function textoDela(texto) {
  const blocos = [];
  for (const bloco of String(texto ?? "").trim().split(/\n{2,}/)) {
    let solto = [], lista = [];
    const fecharSolto = () => {
      if (!solto.length) return;
      const titulo = solto.length === 1 && /^#{1,4}\s/.test(solto[0]);
      blocos.push(h("p", null, titulo ? h("strong", null, emLinha(solto[0].replace(/^#+\s*/, "")))
        : solto.map((l, i) => [i ? h("br") : null, emLinha(l.replace(/^#+\s*/, ""))])));
      solto = [];
    };
    const fecharLista = () => {
      if (!lista.length) return;
      blocos.push(h(/^\s*\d/.test(lista[0]) ? "ol" : "ul", null, lista.map((l) => h("li", null, emLinha(l.replace(ITEM, ""))))));
      lista = [];
    };
    for (const linha of bloco.split("\n")) {
      if (ITEM.test(linha)) { fecharSolto(); lista.push(linha); }
      else { fecharLista(); solto.push(linha); }
    }
    fecharSolto();
    fecharLista();
  }
  return h("div", { class: "texto" }, blocos);
}

// --- a lista: as conversas ou os trabalhos do Claude Code ----------------------------------------------
function abrir(aberta) {
  estado.aberta = aberta;
  estado.registroAte = 300;
  atualizar();
  scrollTo({ top: 0 });
}

const ativa = (tipo, id) => estado.aberta?.tipo === tipo && estado.aberta.id === id;

function linhaConversa(c) {
  return item({
    classe: `conversa${ativa("conversa", c.id) ? " marcada" : ""}`, chave: `conversa:${c.id}`,
    nome: h("a", { href: "#atena", onclick: (e) => { e.preventDefault(); abrir({ tipo: "conversa", id: c.id }); } },
      c.titulo || c.previa || "(sem título)"),
    detalhe: [h("span", { class: `selo${c.origem === "painel" ? " neutro" : ""}` }, ORIGENS[c.origem] ?? c.origem),
      [quandoFoi(c.ultima), plural(c.mensagens, "mensagem", "mensagens")].filter(Boolean).join(" · ")],
  });
}

function linhaTrabalho(t) {
  return item({
    led: ledEstado(t.estado), classe: `conversa${ativa("claude", t.id) ? " marcada" : ""}`, chave: `claude:${t.id}`,
    nome: h("a", { href: "#atena", onclick: (e) => { e.preventDefault(); abrir({ tipo: "claude", id: t.id }); } }, t.pedido),
    detalhe: [estadoTexto(t.estado), t.projeto, t.cliente === "hermes" ? "pela Atena" : t.cliente === "painel" ? "pelo painel" : t.cliente,
      quandoFoi(t.criado)].filter(Boolean).join(" · "),
  });
}

async function moduloLista(lista) {
  const filtros = h("div", { class: "travas filtros", role: "radiogroup", "aria-label": "Mostrar" },
    FILTROS.map(([v, t]) => h("label", { class: "trava" },
      h("input", { type: "radio", name: "filtro", value: v, checked: estado.filtro === v,
        onchange: () => { estado.filtro = v; atualizar(); } }), h("span", null, t))));
  const nova = h("button", { type: "button", class: "principal", onclick: () => abrir({ tipo: "nova" }) }, "Nova conversa");
  let corpo;
  if (lista.ok === false) corpo = falha(lista);
  else if (estado.filtro === "claude")
    corpo = itens(lista.resultado.trabalhos.map(linhaTrabalho), vazio("O Claude Code ainda não trabalhou aqui.", "coruja"), "conversas");
  else corpo = itens(lista.resultado.conversas.map(linhaConversa), vazio("Nenhuma conversa ainda.", "coruja"), "conversas");
  return modulo("Conversas", null, h("div", { class: "botoes" }, nova), filtros, corpo);
}

// --- uma conversa ----------------------------------------------------------------------------------------
function cartaoTrabalho(id, trabalhos) {
  const t = trabalhos.get(id);
  return h("div", { class: "trabalho-claude" },
    item({
      led: t ? ledEstado(t.estado) : "info", chave: `trabalho:${id}`,
      nome: h("a", { href: "#atena", onclick: (e) => { e.preventDefault(); abrir({ tipo: "claude", id }); } },
        `Claude Code${t?.projeto ? ` · ${t.projeto}` : ""}`),
      detalhe: t ? [estadoTexto(t.estado), t.commits ? plural(t.commits, "commit", "commits") : null, `trabalho ${id}`].filter(Boolean).join(" · ")
        : `trabalho ${id}`,
    }));
}

function listaPassos(passos, trabalhos, aberto = false) {
  if (!passos?.length) return null;
  const rodando = passos.some((p) => p.estado === "rodando");
  const cartoes = passos.flatMap((p) => p.trabalhos ?? []).map((id) => cartaoTrabalho(id, trabalhos));
  return [
    h("details", { class: "passos", open: aberto || rodando },
      h("summary", null, `${plural(passos.length, "passo", "passos")}${rodando ? " · trabalhando" : ""}`),
      itens(passos.map((p) => item({
        led: p.estado === "rodando" ? "info" : p.estado === "falhou" ? "ruim" : null,
        nome: h("span", { class: "ferramenta" }, p.ferramenta), detalhe: p.detalhe,
        extra: p.resultado && h("details", null, h("summary", null, "Resultado"), h("pre", { class: "registro" }, p.resultado)),
      })), null, "sub")),
    cartoes,
  ];
}

function fala(m, trabalhos) {
  if (m.papel === "voce")
    return h("div", { class: "fala voce" }, h("span", { class: "quem" }, `Você${m.quando ? ` · ${quandoFoi(m.quando)}` : ""}`), textoDela(m.texto));
  if (m.papel === "agenda")
    return h("div", { class: "fala agenda" }, h("span", { class: "quem" }, `Agenda · ${m.nome}`), textoDela(m.texto));
  return h("div", { class: "fala atena" }, h("span", { class: "quem" }, `Atena${m.quando ? ` · ${quandoFoi(m.quando)}` : ""}`),
    listaPassos(m.passos, trabalhos), m.texto?.trim() && textoDela(m.texto));
}

// as mensagens dela que só chamam ferramentas entram na próxima que tem texto: uma fala com todos os passos
function juntarPassos(mensagens) {
  const saida = [];
  let passos = [];
  for (const m of mensagens) {
    if (m.papel === "atena" && !m.texto?.trim()) { passos.push(...m.passos); continue; }
    if (passos.length) {
      if (m.papel === "atena") { saida.push({ ...m, passos: [...passos, ...m.passos] }); passos = []; continue; }
      saida.push({ papel: "atena", texto: "", passos, quando: null });
      passos = [];
    }
    saida.push(m);
  }
  if (passos.length) saida.push({ papel: "atena", texto: "", passos, quando: null });
  return saida;
}

// a resposta que está chegando: o que você mandou, o que ela já escreveu, os passos, a aprovação e o Parar
function resposta(env, trabalhos) {
  const aprovar = (escolha) => async () => {
    const r = await api("POST", "/api/acao/atena.aprovar", { params: { pedido: env.pedido, escolha } });
    if (r.ok === false) avisar(r.erro, "erro");
  };
  const parar = async () => {
    const r = await api("POST", "/api/acao/atena.parar", { params: { pedido: env.pedido } });
    if (r.ok === false) avisar(r.erro, "erro");
  };
  return h("div", { class: "resposta-viva", "data-chave": "resposta", "aria-live": "polite" },
    fala({ papel: "voce", texto: env.pergunta }),
    h("div", { class: `fala atena${env.estado === "executando" ? " escrevendo" : ""}` },
      h("span", { class: "quem" }, env.estado === "executando" ? "Atena · escrevendo" : "Atena"),
      listaPassos(env.passos, trabalhos, true),
      env.aprovacao && h("div", { class: "aprovacao-chat" },
        h("p", null, h("strong", null, "Ela quer rodar um comando que pede o seu ok"), env.aprovacao.descricao ? `: ${env.aprovacao.descricao}` : ""),
        env.aprovacao.comando && h("pre", { class: "registro" }, env.aprovacao.comando),
        h("div", { class: "botoes" }, env.aprovacao.escolhas.map((e) => h("button", {
          type: "button", class: e === "once" ? "principal" : e === "deny" ? "discreto perigo" : "discreto", onclick: aprovar(e),
        }, ESCOLHAS[e] ?? e)))),
      env.texto?.trim() ? textoDela(env.texto) : env.estado === "executando" && h("p", { class: "fraco" }, "Pensando…"),
      env.erro && h("p", { class: "erro" }, env.erro),
      env.estado === "executando" && h("div", { class: "botoes" }, h("button", { type: "button", class: "discreto", onclick: parar }, "Parar"))));
}

function redesenharResposta(trabalhos) {
  const atual = document.querySelector('#tela [data-chave="resposta"]');
  if (atual && estado.envio) atual.replaceWith(resposta(estado.envio, trabalhos));
}

// acompanha o pedido até o fim: a cada mudança, só a resposta se redesenha; no fim, a conversa se lê de novo
// da Atena (que guarda a versão de verdade) e a resposta viva sai
async function acompanhar(env, trabalhos) {
  while (env.estado === "executando" && estado.envio === env) {
    const r = await api("GET", `/api/pedido/${env.pedido}?esperar=25&versao=${env.versao}`);
    if (r.ok === false) {
      if (r.status === 0 || r.status >= 502) { await new Promise((ok) => setTimeout(ok, 2000)); continue; }
      Object.assign(env, { estado: "falhou", erro: r.erro });
      break;
    }
    const p = r.pedido;
    Object.assign(env, { versao: p.versao ?? env.versao, estado: p.estado, texto: p.texto ?? env.texto, passos: p.passos ?? env.passos,
      aprovacao: p.aprovacao ?? null, erro: p.erro ?? null });
    if (p.conversa && !env.conversa) {
      env.conversa = p.conversa;
      if (estado.aberta?.tipo === "nova") estado.aberta = { tipo: "conversa", id: p.conversa };
    }
    if (telaAtual() === "atena") redesenharResposta(trabalhos);
  }
  if (estado.envio !== env) return;
  if (env.estado !== "concluido") estado.ultimoErro = { pergunta: env.pergunta, erro: env.erro ?? estadoTexto(env.estado) };
  estado.envio = null;
  if (telaAtual() === "atena") atualizar();
}

async function enviar(texto, trabalhos) {
  const conversa = estado.aberta?.tipo === "conversa" ? estado.aberta.id : null;
  const r = await api("POST", "/api/acao/atena.falar", { params: { texto, ...(conversa ? { conversa } : {}) } });
  if (r.ok === false) return avisar(r.erro, "erro");
  estado.rascunho = "";
  estado.ultimoErro = null;
  estado.envio = { pedido: r.pedido, pergunta: texto, texto: "", passos: [], aprovacao: null, estado: "executando", versao: 0, conversa };
  await atualizar();
  acompanhar(estado.envio, trabalhos);
}

function compor(trabalhos) {
  const ocupado = Boolean(estado.envio);
  const mandar = (form) => {
    const texto = form.texto.value.trim();
    if (texto && !estado.envio) enviar(texto, trabalhos);
  };
  return h("form", { class: "compor", onsubmit: (e) => { e.preventDefault(); mandar(e.currentTarget); } },
    h("textarea", { name: "texto", rows: "2", maxlength: "8000", placeholder: "Escreva para a Atena…", "aria-label": "Mensagem para a Atena",
      oninput: (e) => { estado.rascunho = e.currentTarget.value; },
      onkeydown: (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); mandar(e.currentTarget.form); } } },
    estado.rascunho),
    // com a resposta chegando, a tecla principal do módulo é a da aprovação (ou nenhuma)
    h("button", { type: "submit", class: ocupado ? "discreto" : "principal", disabled: ocupado }, ocupado ? "Respondendo…" : "Enviar"));
}

async function moduloConversa(trabalhos) {
  const voltar = h("button", { type: "button", class: "discreto voltar", onclick: () => abrir(null) }, "Conversas");
  const env = estado.envio;
  if (estado.aberta.tipo === "nova") {
    return modulo("Nova conversa", null, voltar,
      env ? h("div", { class: "falas" }, resposta(env, trabalhos))
        : h("p", { class: "fraco" }, "Uma conversa nova no painel. A memória dela é uma só: o que ela sabe pelo Telegram vale aqui também."),
      erroAnterior(), compor(trabalhos));
  }
  const r = await consultar("atena.conversa", { conversa: estado.aberta.id, quantas: 200 });
  if (r.ok === false) return modulo("Conversa", null, voltar, falha(r));
  const { conversa: c } = r.resultado;
  const viva = env && env.conversa === c.id;
  // a Atena guarda a sua mensagem assim que a recebe: com a resposta chegando, ela sai daqui e fica na resposta
  let mensagens = r.resultado.mensagens;
  const sua = viva ? mensagens.findLastIndex((m) => m.papel === "voce" && m.texto.trim() === env.pergunta.trim()) : -1;
  if (sua >= 0) mensagens = mensagens.slice(0, sua);
  return modulo(c.titulo || "Conversa", [ORIGENS[c.origem] ?? c.origem, c.custo ? custo(c.custo) : null].filter(Boolean).join(" · "), voltar,
    !r.resultado.completa && h("p", { class: "fraco" }, "As mensagens mais antigas desta conversa ficaram de fora (são as 200 últimas)."),
    h("div", { class: "falas" }, juntarPassos(mensagens).map((m) => fala(m, trabalhos)), viva && resposta(env, trabalhos)),
    c.pode_responder ? [erroAnterior(), compor(trabalhos)]
      : h("p", { class: "fraco so-ler" }, c.origem === "telegram"
        ? "Conversa do Telegram: aqui ela fica só para ler. Continue por lá, ou comece uma nova no painel."
        : "Esta conversa fica só para ler."));
}

function erroAnterior() {
  const e = estado.ultimoErro;
  return e && h("p", { class: "erro" }, `A última mensagem não teve resposta: ${e.erro}. `,
    h("a", { href: "#atena", onclick: (ev) => { ev.preventDefault(); estado.rascunho = e.pergunta; estado.ultimoErro = null; atualizar(); } },
      "Escrever de novo"));
}

// --- um trabalho do Claude Code: o pedido e a conversa inteira dele ----------------------------------------
function itemRegistro(i) {
  if (i.tipo === "fase") return h("h3", { class: "fase" }, FASES[i.fase] ?? i.fase);
  if (i.tipo === "inicio") return h("p", { class: "fraco" }, `Começou${i.modelo ? ` com ${i.modelo}` : ""}.`);
  if (i.tipo === "texto") return h("div", { class: `fala atena${i.sub ? " sub" : ""}` }, textoDela(i.texto));
  if (i.tipo === "nota") return h("p", { class: "fraco" }, i.texto);
  if (i.tipo === "fim")
    return h("div", { class: "fala fim" }, h("span", { class: "quem" },
      [i.ok ? "Terminou" : "Parou com erro", i.segundos ? `${num(i.segundos)} s` : null, i.turnos ? plural(i.turnos, "volta", "voltas") : null,
        i.custo ? custo(i.custo) : null].filter(Boolean).join(" · ")), i.texto && textoDela(i.texto));
  return item({
    led: i.erro ? "ruim" : null, classe: i.sub ? "dentro" : null, nome: h("span", { class: "ferramenta" }, i.nome), detalhe: i.detalhe,
    extra: i.resultado && h("details", null, h("summary", null, "Resultado"), h("pre", { class: "registro" }, i.resultado)),
  });
}

// as ferramentas seguidas ficam numa lista só, presa pelo fio; o resto, uma coisa de cada vez
function registroLido(lista) {
  const saida = [];
  let seguidas = [];
  const fechar = () => { if (seguidas.length) saida.push(h("ul", { class: "itens sub" }, seguidas)); seguidas = []; };
  for (const i of lista) {
    if (i.tipo === "ferramenta") seguidas.push(itemRegistro(i));
    else { fechar(); saida.push(itemRegistro(i)); }
  }
  fechar();
  return saida;
}

async function moduloTrabalho(trabalhos) {
  const voltar = h("button", { type: "button", class: "discreto voltar", onclick: () => abrir(null) }, "Conversas");
  const id = estado.aberta.id;
  const t = trabalhos.get(id);
  const r = await consultar("claude.registro", { trabalho: id, quantos: estado.registroAte });
  const cabeca = t && [
    h("pre", { class: "texto-pedido" }, t.pedido),
    h("p", { class: "fraco" }, [estadoTexto(t.estado), t.projeto && `projeto ${t.projeto}`, t.conta && `conta ${t.conta}`, t.modelo,
      t.cliente === "hermes" ? "mandado pela Atena" : t.cliente === "painel" ? "mandado pelo painel" : null, quandoFoi(t.criado),
      t.commits ? plural(t.commits, "commit", "commits") : null].filter(Boolean).join(" · ")),
    t.resumo && h("details", null, h("summary", null, "Resumo"), h("pre", { class: "texto-pedido" }, t.resumo)),
  ];
  if (r.ok === false)
    return modulo("Trabalho do Claude Code", id, voltar, cabeca, r.status === 404 ? h("p", { class: "fraco" }, r.erro) : falha(r));
  const { itens: lista, total } = r.resultado;
  return modulo("Trabalho do Claude Code", id, voltar, cabeca,
    h("div", { class: "falas registro-claude" }, registroLido(lista)),
    total > lista.length && h("div", { class: "botoes" }, h("button", { type: "button", class: "discreto", onclick: () => {
      estado.registroAte = Math.min(estado.registroAte + 300, 500);
      atualizar();
    } }, total > 500 ? `Mostrar mais (${num(Math.min(total, 500))} de ${num(total)})` : `Mostrar tudo (${num(total)})`)));
}

// --- a tela ----------------------------------------------------------------------------------------------
export async function telaAtena() {
  const claude = estado.filtro === "claude";
  const [lista, historico] = await Promise.all([
    claude ? consultar("claude.historico", { quantos: 50 })
      : consultar("atena.conversas", { quantas: 50, ...(estado.filtro === "todas" ? {} : { origem: estado.filtro }) }),
    // os trabalhos do Claude Code, para os cartões dentro das conversas e o cabeçalho do registro
    estado.aberta && !claude ? consultar("claude.historico", { quantos: 50 }) : null,
  ]);
  const fonte = claude ? lista : historico;
  const trabalhos = new Map(fonte && fonte.ok !== false ? fonte.resultado.trabalhos.map((t) => [t.id, t]) : []);
  if (lista.ok === false && (lista.status === 403 || lista.status === 404))
    return [cartao("Atena", h("p", { class: "fraco" }, "O token do painel ainda não tem as ações da Atena: rode sudo ./aplicar no servidor."))];
  const aberta = !estado.aberta ? null : estado.aberta.tipo === "claude" ? await moduloTrabalho(trabalhos) : await moduloConversa(trabalhos);
  return [h("section", { class: `largo tela-atena${aberta ? " lendo" : ""}` },
    h("div", { class: "lista-conversas" }, await moduloLista(lista)),
    h("div", { class: "conversa-aberta" }, aberta ?? modulo("Atena", null,
      h("p", { class: "fraco" }, "Escolha uma conversa ao lado, ou comece uma nova. As do Telegram e da agenda ficam aqui para ler; os trabalhos do Claude Code que ela mandou aparecem dentro delas."))))];
}
