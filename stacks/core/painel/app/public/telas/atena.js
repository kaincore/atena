// Atena: o chat com ela, do jeito dos apps de conversa com IA. À esquerda (no celular, numa gaveta), a lista
// das conversas dela (Telegram, painel, agenda) e dos trabalhos do Claude Code que ela comanda, agrupada por
// dia e com a busca; à direita, a conversa: as suas falas em balões, as dela soltas na coluna, e o campo de
// escrever preso embaixo, com a tecla redonda que envia e, enquanto ela responde, para. A conversa nova
// abre no meio da tela, com sugestões. A resposta chega aos pedaços pelo pedido de atena.falar (GET
// /api/pedido com versao), com os passos que ela dá e o pedido de aprovação de um comando perigoso; o que
// chega aos pedaços redesenha só a resposta, nunca a tela inteira. As do Telegram e da agenda ficam só
// para ler.
import { api, atualizar, avisar, consultar, dinheiro, estadoTexto, falha, h, item, itens, ledEstado, num,
  plural, telaAtual, vazio } from "../comum.js";
import { picto } from "../pictos.js";

const ORIGENS = { painel: "painel", telegram: "Telegram", agenda: "agenda", terminal: "terminal", whatsapp: "WhatsApp" };
const FILTROS = [["todas", "Todas"], ["painel", "Painel"], ["telegram", "Telegram"], ["agenda", "Agenda"], ["claude", "Claude Code"]];
const ESCOLHAS = { once: "Só desta vez", session: "Nesta conversa", always: "Sempre", deny: "Não" };
const FASES = { plano: "O plano", executar: "O trabalho" };
const SUGESTOES = ["Como está o servidor agora?", "O que a ronda viu hoje?", "Quanto gastei de IA este mês?",
  "Que receitas de estilo eu tenho?"];
// uma conversa custa menos de um centavo: aí, quatro casas
const custo = (usd) => (usd < 0.01 ? `US$ ${num(usd, 4)}` : dinheiro(usd));
// no celular e no tablet, Enter quebra a linha (o teclado não tem Shift à mão); no PC, Enter envia
const toque = () => matchMedia("(pointer: coarse)").matches;
const largo = () => matchMedia("(min-width: 60rem)").matches;

// o que a tela lembra entre uma leitura e outra: o filtro, a busca, o que está aberto, o rascunho e a resposta
// que está chegando (envio: o pedido de atena.falar, com o texto, os passos, a aprovação e a versão)
const estado = { filtro: "todas", busca: "", aberta: null, rascunho: "", envio: null, ultimoErro: null, registroAte: 300 };

// hoje às 14:05, ontem às 9:10, 28/10 às 9:10
function diasAtras(segundos) {
  return Math.round((new Date().setHours(0, 0, 0, 0) - new Date(segundos * 1000).setHours(0, 0, 0, 0)) / 86_400_000);
}
function quandoFoi(segundos) {
  if (!segundos) return "";
  const d = new Date(segundos * 1000);
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const dias = diasAtras(segundos);
  if (dias === 0) return `hoje às ${hora}`;
  if (dias === 1) return `ontem às ${hora}`;
  return `${d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} às ${hora}`;
}
const GRUPOS = [[0, "Hoje"], [1, "Ontem"], [7, "Últimos 7 dias"], [30, "Últimos 30 dias"], [Infinity, "Antes"]];
const grupoDe = (segundos) => (segundos ? GRUPOS.find(([ate]) => diasAtras(segundos) <= ate)[1] : "Antes");

// --- o texto dela: parágrafos, títulos, listas, **negrito**, `código` e blocos de código, sem innerHTML ----
function emLinha(texto) {
  return texto.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`)/).filter(Boolean).map((s) =>
    s.startsWith("**") && s.endsWith("**") && s.length > 4 ? h("strong", null, s.slice(2, -2))
      : s.startsWith("`") && s.endsWith("`") && s.length > 2 ? h("code", null, s.slice(1, -1)) : s);
}

const ITEM = /^\s*([-*•]|\d+[.)])\s+/;

// copiar para a área de transferência só existe em HTTPS (o Tailscale); na rede de casa, em HTTP, a tecla some
const podeCopiar = () => Boolean(navigator.clipboard && window.isSecureContext);
function teclaCopiar(texto, rotulo = "Copiar") {
  if (!podeCopiar()) return null;
  return h("button", { type: "button", class: "acao-fala", "aria-label": rotulo, title: rotulo, onclick: async (e) => {
    const b = e.currentTarget;
    try {
      await navigator.clipboard.writeText(texto);
      b.classList.add("copiado");
      b.lastChild.textContent = "Copiado";
      setTimeout(() => { b.classList.remove("copiado"); b.lastChild.textContent = rotulo; }, 1600);
    } catch { avisar("Não consegui copiar", "erro"); }
  } }, picto("copiar"), h("span", null, rotulo));
}

function blocoCodigo(linhas, lingua) {
  const codigo = linhas.join("\n");
  return h("div", { class: "codigo-fala" },
    h("div", { class: "codigo-topo" }, h("span", null, lingua || "código"), teclaCopiar(codigo)),
    h("pre", null, h("code", null, codigo)));
}

// cada bloco (separado por linha em branco) vira parágrafos e listas: as linhas seguidas que começam com
// "- " ou "1." são uma lista; as outras, um parágrafo com as quebras de linha dela. Entre ``` é código.
function textoDela(texto) {
  const blocos = [];
  const partes = String(texto ?? "").trim().split(/^```([\w+-]*)[^\n]*\n([\s\S]*?)(?:^```\s*$|(?![\s\S]))/m);
  for (let i = 0; i < partes.length; i += 3) {
    for (const bloco of partes[i].trim().split(/\n{2,}/)) {
      if (!bloco.trim()) continue;
      let solto = [], lista = [];
      const fecharSolto = () => {
        if (!solto.length) return;
        const titulo = solto.length === 1 && /^#{1,4}\s/.test(solto[0]);
        blocos.push(titulo ? h("h4", null, emLinha(solto[0].replace(/^#+\s*/, "")))
          : h("p", null, solto.map((l, j) => [j ? h("br") : null, emLinha(l.replace(/^#+\s*/, ""))])));
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
    if (i + 2 < partes.length) blocos.push(blocoCodigo(partes[i + 2].replace(/\n$/, "").split("\n"), partes[i + 1]));
  }
  return h("div", { class: "texto" }, blocos);
}

// --- abrir, rolar ---------------------------------------------------------------------------------------
const fim = () => scrollTo({ top: document.documentElement.scrollHeight });
const noFim = () => innerHeight + scrollY >= document.documentElement.scrollHeight - 140;

async function abrir(aberta) {
  estado.aberta = aberta;
  estado.registroAte = 300;
  document.querySelector("#gaveta-conversas")?.close();
  await atualizar();
  // uma conversa abre no fim, como num app de conversa; a nova e a lista, no alto
  if (aberta && aberta.tipo !== "nova") fim();
  else scrollTo({ top: 0 });
  if (!aberta || aberta.tipo === "nova") document.querySelector('#tela [data-chave="compor"]')?.focus({ preventScroll: true });
}

const ativa = (tipo, id) => estado.aberta?.tipo === tipo && estado.aberta.id === id;

// a tecla redonda que leva ao fim da conversa, quando você subiu para ler
addEventListener("scroll", () => {
  const descer = document.querySelector("#tela .descer");
  if (descer) descer.hidden = noFim();
}, { passive: true });

// --- a lista: as conversas ou os trabalhos do Claude Code, por dia ---------------------------------------
function itemLista(tipo, id, titulo, origem, quando) {
  return h("li", { class: `item-conversa${ativa(tipo, id) ? " ativa" : ""}`, "data-busca": `${titulo} ${origem ?? ""}`.toLowerCase() },
    h("a", { href: "#atena", "data-chave": `${tipo}:${id}`, "aria-current": ativa(tipo, id) ? "page" : null, title: quando,
      onclick: (e) => { e.preventDefault(); abrir({ tipo, id }); } },
    h("span", { class: "titulo-conversa" }, titulo),
    origem && h("span", { class: "origem-conversa" }, origem)));
}

function listaPorDia(linhas) {
  const grupos = new Map();
  for (const [quando, li] of linhas) {
    const g = grupoDe(quando);
    if (!grupos.has(g)) grupos.set(g, []);
    grupos.get(g).push(li);
  }
  return GRUPOS.filter(([, g]) => grupos.has(g)).map(([, g]) => h("section", { class: "grupo-conversas" },
    h("h3", null, g), h("ul", null, grupos.get(g))));
}

// a busca filtra a lista que já está na tela, sem ler de novo (o foco fica no campo)
function filtrar(lado, texto) {
  estado.busca = texto;
  const t = texto.trim().toLowerCase();
  for (const li of lado.querySelectorAll(".item-conversa")) li.hidden = Boolean(t) && !li.dataset.busca.includes(t);
  for (const g of lado.querySelectorAll(".grupo-conversas")) g.hidden = !g.querySelector(".item-conversa:not([hidden])");
  const nada = lado.querySelector(".nada-achado");
  if (nada) nada.hidden = !t || Boolean(lado.querySelector(".item-conversa:not([hidden])"));
}

function ladoConversas(lista) {
  const lado = h("div", { class: "lado-conversas" });
  const nova = h("button", { type: "button", class: "nova-conversa", onclick: () => abrir({ tipo: "nova" }) },
    picto("escrever"), h("span", null, "Nova conversa"));
  const busca = h("input", { type: "search", class: "busca-conversas", value: estado.busca, placeholder: "Buscar conversas",
    "aria-label": "Buscar nas conversas", autocomplete: "off", "data-chave": "busca-conversas",
    oninput: (e) => filtrar(lado, e.currentTarget.value) });
  const filtros = h("div", { class: "travas filtros-conversas", role: "radiogroup", "aria-label": "Mostrar" },
    FILTROS.map(([v, t]) => h("label", { class: "trava" },
      h("input", { type: "radio", name: "filtro", value: v, checked: estado.filtro === v,
        onchange: () => { estado.filtro = v; atualizar(); } }), h("span", null, t))));
  let corpo;
  if (lista.ok === false) corpo = falha(lista);
  else if (estado.filtro === "claude") {
    const t = lista.resultado.trabalhos;
    corpo = t.length ? listaPorDia(t.map((x) => [x.criado, itemLista("claude", x.id, x.pedido, x.projeto, quandoFoi(x.criado))]))
      : vazio("O Claude Code ainda não trabalhou aqui.", "coruja");
  } else {
    const c = lista.resultado.conversas;
    corpo = c.length ? listaPorDia(c.map((x) => [x.ultima, itemLista("conversa", x.id, x.titulo || x.previa || "(sem título)",
      x.origem === "painel" ? null : ORIGENS[x.origem] ?? x.origem, quandoFoi(x.ultima))]))
      : vazio("Nenhuma conversa ainda.", "coruja");
  }
  lado.append(nova, busca, filtros, h("nav", { class: "conversas", "aria-label": "Conversas" }, corpo,
    h("p", { class: "fraco nada-achado", hidden: true }, "Nenhuma conversa com isso.")));
  if (estado.busca) filtrar(lado, estado.busca);
  return lado;
}

// no celular, a lista fica numa gaveta que sai da esquerda (uma janela, com o fundo escurecido)
function abrirGaveta(lista) {
  const gaveta = document.querySelector("#gaveta-conversas");
  gaveta.replaceChildren(h("div", { class: "gaveta-topo" }, h("strong", null, "Conversas"),
    h("button", { type: "button", class: "discreto", onclick: () => gaveta.close() }, "Fechar")), ladoConversas(lista));
  gaveta.showModal();
}

// --- uma conversa ----------------------------------------------------------------------------------------
function cartaoTrabalho(id, trabalhos) {
  const t = trabalhos.get(id);
  return h("a", { class: "trabalho-claude", href: "#atena", "data-chave": `trabalho:${id}`,
    onclick: (e) => { e.preventDefault(); abrir({ tipo: "claude", id }); } },
  h("span", { class: `led ${t ? ledEstado(t.estado) : "info"}` }),
  h("span", null, h("strong", null, `Claude Code${t?.projeto ? ` · ${t.projeto}` : ""}`),
    h("span", { class: "fraco" }, t ? [estadoTexto(t.estado), t.commits ? plural(t.commits, "commit", "commits") : null].filter(Boolean).join(" · ")
      : `trabalho ${id}`)),
  picto("seguir"));
}

// os passos dela, numa linha que abre (como o "pesquisou na web" dos apps de conversa)
function listaPassos(passos, trabalhos, aberto = false) {
  if (!passos?.length) return null;
  const rodando = passos.some((p) => p.estado === "rodando");
  const cartoes = passos.flatMap((p) => p.trabalhos ?? []).map((id) => cartaoTrabalho(id, trabalhos));
  return [
    h("details", { class: `passos${rodando ? " rodando" : ""}`, open: aberto && rodando },
      h("summary", null, rodando ? `Trabalhando · ${plural(passos.length, "passo", "passos")}` : plural(passos.length, "passo", "passos")),
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
    return h("div", { class: "fala voce", title: quandoFoi(m.quando) || null }, textoDela(m.texto));
  const corpo = [
    m.papel === "agenda" && h("span", { class: "quem" }, picto("agenda"), `Agenda · ${m.nome}`),
    m.papel !== "agenda" && listaPassos(m.passos, trabalhos),
    m.texto?.trim() && textoDela(m.texto),
  ];
  return h("div", { class: `fala ${m.papel === "agenda" ? "agenda" : "atena"}` }, corpo,
    m.texto?.trim() && h("div", { class: "acoes-fala" }, teclaCopiar(m.texto),
      m.quando && h("span", { class: "quando-fala" }, quandoFoi(m.quando))));
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

// a resposta que está chegando: o que você mandou, o que ela já escreveu (com o cursor piscando), os passos
// e a aprovação. O Parar fica na tecla redonda do campo de escrever
function resposta(env, trabalhos) {
  const aprovar = (escolha) => async () => {
    const r = await api("POST", "/api/acao/atena.aprovar", { params: { pedido: env.pedido, escolha } });
    if (r.ok === false) avisar(r.erro, "erro");
  };
  const escrevendo = env.estado === "executando";
  return h("div", { class: "resposta-viva", "data-chave": "resposta", "aria-live": "polite", "aria-busy": String(escrevendo) },
    fala({ papel: "voce", texto: env.pergunta }),
    h("div", { class: `fala atena${escrevendo ? " escrevendo" : ""}` },
      listaPassos(env.passos, trabalhos, true),
      env.aprovacao && h("div", { class: "aprovacao-chat" },
        h("p", null, h("strong", null, "Ela quer rodar um comando que pede o seu ok"), env.aprovacao.descricao ? `: ${env.aprovacao.descricao}` : ""),
        env.aprovacao.comando && h("pre", { class: "registro" }, env.aprovacao.comando),
        h("div", { class: "botoes" }, env.aprovacao.escolhas.map((e) => h("button", {
          type: "button", class: e === "once" ? "principal" : e === "deny" ? "discreto perigo" : "discreto", onclick: aprovar(e),
        }, ESCOLHAS[e] ?? e)))),
      env.texto?.trim() ? textoDela(env.texto) : escrevendo && !env.aprovacao && h("p", { class: "pensando" }, "Pensando…"),
      env.erro && h("p", { class: "erro" }, env.erro)));
}

function redesenharResposta(trabalhos) {
  const atual = document.querySelector('#tela [data-chave="resposta"]');
  if (!atual || !estado.envio) return;
  const descer = noFim();
  atual.replaceWith(resposta(estado.envio, trabalhos));
  if (descer) fim(); // quem está lendo o fim acompanha o texto chegando; quem subiu para ler fica onde está
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
  if (telaAtual() === "atena") {
    const descer = noFim();
    await atualizar();
    if (descer) fim();
  }
}

async function enviar(texto, trabalhos) {
  const conversa = estado.aberta?.tipo === "conversa" ? estado.aberta.id : null;
  const r = await api("POST", "/api/acao/atena.falar", { params: { texto, ...(conversa ? { conversa } : {}) } });
  if (r.ok === false) return avisar(r.erro, "erro");
  estado.rascunho = "";
  estado.ultimoErro = null;
  estado.envio = { pedido: r.pedido, pergunta: texto, texto: "", passos: [], aprovacao: null, estado: "executando", versao: 0, conversa };
  if (!estado.aberta) estado.aberta = { tipo: "nova" };
  await atualizar();
  fim();
  document.querySelector('#tela [data-chave="compor"]')?.focus({ preventScroll: true });
  acompanhar(estado.envio, trabalhos);
}

async function parar() {
  const r = await api("POST", "/api/acao/atena.parar", { params: { pedido: estado.envio?.pedido } });
  if (r.ok === false) avisar(r.erro, "erro");
}

// o campo cresce com o texto, até umas 10 linhas; depois rola por dentro
function crescer(campo) {
  campo.style.setProperty("height", "auto");
  campo.style.setProperty("height", `${Math.min(campo.scrollHeight, 240)}px`);
}

function compor(trabalhos) {
  const ocupado = Boolean(estado.envio);
  const mandar = (form) => {
    const texto = form.texto.value.trim();
    if (texto && !estado.envio) enviar(texto, trabalhos);
  };
  const campo = h("textarea", { name: "texto", rows: "1", maxlength: "8000", placeholder: "Escreva para a Atena…",
    "aria-label": "Mensagem para a Atena", "data-chave": "compor", enterkeyhint: toque() ? "enter" : "send",
    oninput: (e) => {
      estado.rascunho = e.currentTarget.value;
      crescer(e.currentTarget);
      e.currentTarget.form.querySelector(".enviar").disabled = !estado.envio && !e.currentTarget.value.trim();
    },
    onkeydown: (e) => {
      const enviaComEnter = e.key === "Enter" && !e.shiftKey && !e.isComposing && !toque();
      if (enviaComEnter || (e.key === "Enter" && (e.ctrlKey || e.metaKey))) { e.preventDefault(); mandar(e.currentTarget.form); }
    } }, estado.rascunho);
  requestAnimationFrame(() => crescer(campo));
  // a tecla redonda: envia; com a resposta chegando, para
  const tecla = ocupado
    ? h("button", { type: "button", class: "enviar parar", "aria-label": "Parar a resposta", title: "Parar", onclick: parar }, picto("parar"))
    : h("button", { type: "submit", class: "enviar", "aria-label": "Enviar", title: "Enviar", disabled: !estado.rascunho.trim() }, picto("enviar"));
  return h("form", { class: "compor-chat", onsubmit: (e) => { e.preventDefault(); mandar(e.currentTarget); } }, campo, tecla);
}

function pe(trabalhos, extra) {
  return h("div", { class: "chat-pe" },
    h("button", { type: "button", class: "descer", hidden: true, "aria-label": "Ir para o fim da conversa", onclick: () =>
      scrollTo({ top: document.documentElement.scrollHeight, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }) },
    picto("descer")),
    extra, compor(trabalhos),
    h("p", { class: "chat-aviso" }, "A Atena pode errar. O que mexe no servidor de verdade pede o seu ok."));
}

function erroAnterior() {
  const e = estado.ultimoErro;
  return e && h("p", { class: "erro" }, `A última mensagem não teve resposta: ${e.erro}. `,
    h("a", { href: "#atena", onclick: (ev) => { ev.preventDefault(); estado.rascunho = e.pergunta; estado.ultimoErro = null; atualizar(); } },
      "Escrever de novo"));
}

function topo(titulo, meta, lista) {
  return h("header", { class: "chat-topo" },
    h("button", { type: "button", class: "abrir-gaveta", "aria-label": "Conversas", title: "Conversas", onclick: () => abrirGaveta(lista) },
      picto("lado")),
    h("div", { class: "chat-titulo" }, h("h2", null, titulo), meta && h("span", { class: "fraco" }, meta)),
    h("button", { type: "button", class: "abrir-gaveta nova-pequena", "aria-label": "Nova conversa", title: "Nova conversa",
      onclick: () => abrir({ tipo: "nova" }) }, picto("escrever")));
}

// a conversa nova: o convite no meio da tela, o campo de escrever e as sugestões
function boasVindas(trabalhos, lista) {
  const env = estado.envio;
  if (env) return [topo("Nova conversa", null, lista), h("div", { class: "chat-fio" }, h("div", { class: "falas" }, resposta(env, trabalhos))),
    pe(trabalhos, erroAnterior())];
  return [topo("Nova conversa", null, lista), h("div", { class: "chat-vazio" },
    h("h2", { class: "convite" }, "Em que posso ajudar?"),
    compor(trabalhos),
    h("div", { class: "sugestoes" }, SUGESTOES.map((s) => h("button", { type: "button", class: "sugestao", onclick: () => enviar(s, trabalhos) }, s))),
    erroAnterior(),
    h("p", { class: "chat-aviso" }, "Uma conversa nova no painel. A memória dela é uma só: o que ela sabe pelo Telegram vale aqui também."))];
}

async function conversaAberta(trabalhos, lista) {
  const env = estado.envio;
  const r = await consultar("atena.conversa", { conversa: estado.aberta.id, quantas: 200 });
  if (r.ok === false) return [topo("Conversa", null, lista), h("div", { class: "chat-fio" }, falha(r))];
  const { conversa: c } = r.resultado;
  const viva = env && env.conversa === c.id;
  // a Atena guarda a sua mensagem assim que a recebe: com a resposta chegando, ela sai daqui e fica na resposta
  let mensagens = r.resultado.mensagens;
  const sua = viva ? mensagens.findLastIndex((m) => m.papel === "voce" && m.texto.trim() === env.pergunta.trim()) : -1;
  if (sua >= 0) mensagens = mensagens.slice(0, sua);
  const meta = [ORIGENS[c.origem] ?? c.origem, c.custo ? custo(c.custo) : null].filter(Boolean).join(" · ");
  return [topo(c.titulo || "Conversa", meta, lista),
    h("div", { class: "chat-fio" },
      !r.resultado.completa && h("p", { class: "fraco aviso-antigas" }, "As mensagens mais antigas desta conversa ficaram de fora (são as 200 últimas)."),
      h("div", { class: "falas" }, juntarPassos(mensagens).map((m) => fala(m, trabalhos)), viva && resposta(env, trabalhos))),
    c.pode_responder ? pe(trabalhos, erroAnterior())
      : h("div", { class: "chat-pe so-ler" }, h("p", null, c.origem === "telegram"
        ? "Conversa do Telegram: aqui ela fica só para ler. Continue por lá, ou comece uma nova no painel."
        : "Esta conversa fica só para ler."),
      h("button", { type: "button", class: "discreto", onclick: () => abrir({ tipo: "nova" }) }, "Nova conversa"))];
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

async function trabalhoAberto(trabalhos, lista) {
  const id = estado.aberta.id;
  const t = trabalhos.get(id);
  const r = await consultar("claude.registro", { trabalho: id, quantos: estado.registroAte });
  const meta = t && [estadoTexto(t.estado), t.projeto && `projeto ${t.projeto}`, t.conta && `conta ${t.conta}`, t.modelo,
    t.cliente === "hermes" ? "mandado pela Atena" : t.cliente === "painel" ? "mandado pelo painel" : null, quandoFoi(t.criado),
    t.commits ? plural(t.commits, "commit", "commits") : null].filter(Boolean).join(" · ");
  const cabeca = t && [
    h("div", { class: "fala voce" }, textoDela(t.pedido)),
    t.resumo && h("details", { class: "resumo-trabalho" }, h("summary", null, "Resumo"), textoDela(t.resumo)),
  ];
  const corpo = r.ok === false ? [cabeca, r.status === 404 ? h("p", { class: "fraco" }, r.erro) : falha(r)] : (() => {
    const { itens: registro, total } = r.resultado;
    return [cabeca, h("div", { class: "falas registro-claude" }, registroLido(registro)),
      total > registro.length && h("div", { class: "botoes" }, h("button", { type: "button", class: "discreto", onclick: () => {
        estado.registroAte = Math.min(estado.registroAte + 300, 500);
        atualizar();
      } }, total > 500 ? `Mostrar mais (${num(Math.min(total, 500))} de ${num(total)})` : `Mostrar tudo (${num(total)})`))];
  })();
  return [topo(`Claude Code${t?.projeto ? ` · ${t.projeto}` : ""}`, meta ?? `trabalho ${id}`, lista),
    h("div", { class: "chat-fio" }, corpo),
    h("div", { class: "chat-pe so-ler" }, h("p", null, "Trabalho do Claude Code: a conversa inteira dele, para ler."))];
}

// --- a tela ----------------------------------------------------------------------------------------------
export async function telaAtena() {
  const claude = estado.filtro === "claude";
  const aberta = estado.aberta ?? (largo() ? { tipo: "nova" } : null);
  const [lista, historico] = await Promise.all([
    claude ? consultar("claude.historico", { quantos: 50 })
      : consultar("atena.conversas", { quantas: 50, ...(estado.filtro === "todas" ? {} : { origem: estado.filtro }) }),
    // os trabalhos do Claude Code, para os cartões dentro das conversas e o cabeçalho do registro
    aberta && !claude ? consultar("claude.historico", { quantos: 50 }) : null,
  ]);
  const fonte = claude ? lista : historico;
  const trabalhos = new Map(fonte && fonte.ok !== false ? fonte.resultado.trabalhos.map((t) => [t.id, t]) : []);
  if (lista.ok === false && (lista.status === 403 || lista.status === 404))
    return [h("section", { class: "modulo largo" }, h("p", { class: "fraco" },
      "O token do painel ainda não tem as ações da Atena: rode sudo ./aplicar no servidor."))];
  // no celular, sem nada aberto, a tela é a conversa nova (a lista fica na gaveta, como num app de conversa)
  const principal = !aberta || aberta.tipo === "nova" ? boasVindas(trabalhos, lista)
    : aberta.tipo === "claude" ? await trabalhoAberto(trabalhos, lista) : await conversaAberta(trabalhos, lista);
  return [h("section", { class: `largo chat${!aberta || aberta.tipo === "nova" ? " chat-nova" : ""}` },
    h("aside", { class: "chat-lado" }, ladoConversas(lista)),
    h("div", { class: "chat-principal" }, principal),
    h("dialog", { id: "gaveta-conversas", class: "gaveta", "aria-label": "Conversas",
      onclick: (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); } }))];
}
