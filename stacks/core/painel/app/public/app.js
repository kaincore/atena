// Interface do painel: telas montadas com elementos (nunca innerHTML com dados do servidor).

const NOMES = {
  "servico.reiniciar": "Reiniciar serviço",
  "pc.ligar": "Ligar o PC",
  "pc.desligar": "Desligar o PC",
  "pc.reiniciar": "Reiniciar o PC",
  "pc.cancelar": "Cancelar desligamento do PC",
  "app.reiniciar": "Reiniciar app do lab",
  "app.parar": "Parar app do lab",
};
const ORDEM_ZONAS = ["core", "ai", "agents", "apps", "lab", "prod"];
const TERMINADOS = new Set(["concluido", "falhou", "recusado", "expirado", "cancelado"]);
const INTERVALO = 30_000;

const $ = (seletor) => document.querySelector(seletor);

function h(tag, atributos, ...filhos) {
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

// --- API -------------------------------------------------------------------------------------

async function api(metodo, caminho, corpo) {
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

const consultar = (nome, params = {}) => api("POST", `/api/acao/${nome}`, { params });

// ações que mudam algo: confirma, pede, acompanha o pedido (202) e avisa o resultado
async function mudar(nome, params, pergunta) {
  if (pergunta && !confirm(pergunta)) return null;
  avisar(`${NOMES[nome] ?? nome}…`);
  let r = await consultar(nome, params);
  if (r.status === 202 && r.pedido) {
    for (let i = 0; i < 10 && r.ok !== false; i++) {
      const p = await api("GET", `/api/pedido/${r.pedido}?esperar=30`);
      if (p.ok === false) { r = p; break; }
      if (TERMINADOS.has(p.pedido.estado)) {
        r = p.pedido.estado === "concluido" ? { ok: true, resultado: p.pedido.resultado } : { ok: false, erro: p.pedido.erro ?? p.pedido.estado };
        break;
      }
    }
  }
  if (r.ok === false) avisar(`${NOMES[nome] ?? nome}: ${r.erro}`, "erro");
  else avisar(`${NOMES[nome] ?? nome}: feito`, "ok");
  return r;
}

// --- utilidades de tela -----------------------------------------------------------------------

function avisar(texto, tipo = "") {
  const aviso = h("div", { class: `aviso ${tipo}` }, texto);
  $("#avisos").append(aviso);
  setTimeout(() => aviso.remove(), tipo === "erro" ? 8000 : 4000);
}

const gb = (mb) => `${(mb / 1024).toFixed(1)} GB`;
const data = (ms) => new Date(ms).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
const dinheiro = (usd) => `US$ ${Number(usd).toFixed(2)}`;

function medidor(fracao, alerta = 0.85) {
  const pct = Math.max(0, Math.min(1, fracao || 0));
  const barra = h("span");
  barra.style.width = `${(pct * 100).toFixed(0)}%`; // pelo CSSOM: a CSP barra o atributo style
  return h("div", { class: `medidor${pct >= alerta ? " alto" : ""}` }, barra);
}

function cartao(titulo, ...conteudo) {
  return h("section", { class: "cartao" }, h("h2", null, titulo), ...conteudo);
}

function falha(r) {
  return h("p", { class: "erro" }, r.erro ?? "erro");
}

function linha(rotulo, valor, extra) {
  return h("div", { class: "linha" }, h("span", { class: "rotulo" }, rotulo), h("span", null, valor), extra);
}

function estadoContainer(c) {
  const ok = c.estado === "running" && !/unhealthy/.test(c.status);
  return h("span", { class: `selo ${ok ? "ok" : "ruim"}` }, ok ? "no ar" : c.estado === "running" ? "com problema" : c.estado);
}

// --- telas ------------------------------------------------------------------------------------

async function telaInicio() {
  const [recursos, servicos, gasto, sistema] = await Promise.all([
    consultar("status.recursos"), consultar("status.servicos"), consultar("gasto.api"), consultar("status.sistema"),
  ]);
  const cartoes = [];

  if (recursos.ok === false) cartoes.push(cartao("Servidor", falha(recursos)));
  else {
    const r = recursos.resultado;
    const usada = r.ram_total_mb - r.ram_disponivel_mb;
    cartoes.push(cartao("Servidor",
      linha("CPU (carga)", `${r.carga[0].toFixed(2)} / ${r.nucleos} núcleos`), medidor(r.carga[0] / r.nucleos),
      linha("RAM", `${gb(usada)} de ${gb(r.ram_total_mb)}`), medidor(usada / r.ram_total_mb),
      ...Object.entries(r.discos).map(([ponto, d]) => [
        linha(`Disco ${ponto}`, `${d.livre_gb} GB livres de ${d.total_gb} GB`), medidor(1 - d.livre_gb / d.total_gb, 0.9),
      ]),
      r.gpu && [linha("GPU", `${r.gpu.uso_pct}% · ${r.gpu.vram_usada_mb} de ${r.gpu.vram_total_mb} MB · ${r.gpu.temperatura_c} °C`),
        medidor(r.gpu.vram_usada_mb / r.gpu.vram_total_mb)],
      linha("Temperatura", [r.temperaturas.cpu_c != null && `CPU ${r.temperaturas.cpu_c} °C`,
        r.temperaturas.nvme_c != null && `NVMe ${r.temperaturas.nvme_c} °C`].filter(Boolean).join(" · ") || "sem leitura"),
    ));
  }

  if (servicos.ok === false) cartoes.push(cartao("Serviços", falha(servicos)));
  else {
    const lista = servicos.resultado;
    const ruins = lista.filter((c) => c.estado !== "running" || /unhealthy/.test(c.status));
    cartoes.push(cartao("Serviços",
      h("p", { class: "destaque" }, `${lista.length - ruins.length} de ${lista.length} containers no ar`),
      ruins.length ? h("ul", { class: "lista" }, ruins.map((c) => h("li", null, estadoContainer(c), ` ${c.container} `, h("small", null, c.status))))
        : h("p", { class: "fraco" }, "Tudo funcionando."),
      h("a", { href: "#servicos" }, "Ver todos"),
    ));
  }

  if (gasto.ok === false) cartoes.push(cartao("Gasto de IA", falha(gasto)));
  else {
    const g = gasto.resultado;
    cartoes.push(cartao(`Gasto de IA em ${g.mes}`,
      h("p", { class: "destaque" }, dinheiro(g.total_usd)),
      g.por_modelo.filter((m) => m.gasto_usd > 0 || m.teto_usd).map((m) => [
        linha(m.modelo, `${dinheiro(m.gasto_usd)}${m.teto_usd ? ` de ${dinheiro(m.teto_usd)}` : ""} · ${m.chamadas} chamadas`),
        m.teto_usd ? medidor(m.gasto_usd / m.teto_usd) : null,
      ]),
      h("p", { class: "fraco" }, g.obs),
    ));
  }

  if (sistema.ok === false) cartoes.push(cartao("Sistema", falha(sistema)));
  else {
    const s = sistema.resultado;
    cartoes.push(cartao("Sistema",
      s.falhas.length ? h("ul", { class: "lista" }, s.falhas.map((u) => h("li", null, h("span", { class: "selo ruim" }, "falhou"), ` ${u}`)))
        : h("p", { class: "fraco" }, "Nenhuma unidade do systemd com falha."),
      h("details", null, h("summary", null, `Timers (${s.timers.length})`),
        h("ul", { class: "lista" }, s.timers.map((t) => h("li", null, t.nome, h("small", null, ` próxima: ${t.proxima ?? "—"}`))))),
    ));
  }
  return cartoes;
}

async function verLogs(stack) {
  abrirJanela(`Logs de ${stack}`, h("p", { class: "fraco" }, "Carregando…"));
  const r = await consultar("servico.logs", { stack, linhas: 200 });
  if (r.ok === false) return abrirJanela(`Logs de ${stack}`, falha(r));
  abrirJanela(`Logs de ${stack}`, Object.entries(r.resultado).map(([nome, texto]) => [
    h("h3", null, nome), h("pre", { class: "log" }, texto || "(vazio)"),
  ]));
}

async function telaServicos() {
  const [servicos, uso] = await Promise.all([consultar("status.servicos"), consultar("status.containers")]);
  if (servicos.ok === false) return [cartao("Serviços", falha(servicos))];
  const consumo = Object.fromEntries((uso.ok === false ? [] : uso.resultado).map((c) => [c.container, c]));
  const zonas = {};
  for (const c of servicos.resultado) ((zonas[c.zona] ??= {})[c.stack] ??= []).push(c);
  const ordem = Object.keys(zonas).sort((a, b) => ORDEM_ZONAS.indexOf(a) - ORDEM_ZONAS.indexOf(b));
  return ordem.map((zona) => cartao(`Zona ${zona}`,
    Object.entries(zonas[zona]).sort(([a], [b]) => a.localeCompare(b)).map(([stack, containers]) =>
      h("div", { class: "stack" },
        h("div", { class: "stack-topo" },
          h("strong", null, stack),
          h("span", { class: "botoes" },
            h("button", { type: "button", class: "discreto", onclick: () => verLogs(stack) }, "Logs"),
            h("button", { type: "button", onclick: async () => {
              if (await mudar("servico.reiniciar", { stack }, `Reiniciar ${stack}?`)) atualizar();
            } }, "Reiniciar"))),
        h("ul", { class: "lista" }, containers.map((c) => h("li", null,
          estadoContainer(c), ` ${c.container} `,
          h("small", null, [c.status, consumo[c.container] && `CPU ${consumo[c.container].cpu} · RAM ${consumo[c.container].ram}`].filter(Boolean).join(" · "))))),
      )),
  ));
}

async function telaPC() {
  const r = await consultar("pc.estado");
  if (r.ok === false) return [cartao("PC gamer", falha(r))];
  const { ligado, lm_studio } = r.resultado;
  const depois = async (resposta) => { if (resposta) setTimeout(atualizar, 3000); };
  return [cartao("PC gamer",
    linha("Estado", h("span", { class: `selo ${ligado ? "ok" : "neutro"}` }, ligado ? "ligado" : "desligado")),
    linha("LM Studio", lm_studio ? "respondendo" : "fora do ar"),
    h("div", { class: "botoes grandes" },
      !ligado && h("button", { type: "button", onclick: async () => depois(await mudar("pc.ligar", {})) }, "Ligar"),
      ligado && h("button", { type: "button", onclick: async () => depois(await mudar("pc.desligar", {}, "Desligar o PC gamer? Ele desliga em 60 s.")) }, "Desligar"),
      ligado && h("button", { type: "button", onclick: async () => depois(await mudar("pc.reiniciar", {}, "Reiniciar o PC gamer? Ele reinicia em 60 s.")) }, "Reiniciar"),
      ligado && h("button", { type: "button", class: "discreto", onclick: async () => depois(await mudar("pc.cancelar", {})) }, "Cancelar desligamento"),
    ),
    h("p", { class: "fraco" }, "Ligar leva uns 25 s; o LM Studio sobe uns 25 s depois."),
  )];
}

async function telaLab() {
  const r = await consultar("app.lista");
  if (r.ok === false) return [cartao("Lab", falha(r))];
  const { projetos, lixeira } = r.resultado;
  return [
    cartao("Apps do lab", projetos.length ? projetos.map((p) => h("div", { class: "stack" },
      h("div", { class: "stack-topo" },
        h("strong", null, p.projeto),
        h("span", { class: "botoes" },
          p.app !== "não publicado" && h("button", { type: "button", onclick: async () => {
            if (await mudar("app.reiniciar", { projeto: p.projeto }, `Reiniciar o app ${p.projeto}?`)) atualizar();
          } }, "Reiniciar"),
          p.app !== "não publicado" && p.app !== "parado" && h("button", { type: "button", class: "discreto", onclick: async () => {
            if (await mudar("app.parar", { projeto: p.projeto }, `Tirar o app ${p.projeto} do ar? Os dados ficam.`)) atualizar();
          } }, "Parar"))),
      linha("App", p.app),
      p.fora_de_casa && linha("Endereço", h("a", { href: p.fora_de_casa, target: "_blank", rel: "noopener" }, p.fora_de_casa)),
      p.endereco && linha("Na rede de casa", h("a", { href: p.endereco, target: "_blank", rel: "noopener" }, p.endereco)),
      p.em_andamento && linha("Em andamento", JSON.stringify(p.em_andamento)),
    )) : h("p", { class: "fraco" }, "Nenhum projeto no lab ainda.")),
    lixeira.length ? cartao("Lixeira", h("ul", { class: "lista" }, lixeira.map((l) =>
      h("li", null, l.projeto, h("small", null, ` apagado em ${l.apagado_em}; some de vez em ${l.some_de_vez_em}`))))) : null,
  ];
}

async function telaHistorico() {
  const r = await api("GET", "/api/historico");
  if (r.ok === false) return [cartao("Histórico", falha(r))];
  return [cartao("Histórico (90 dias)", r.historico.length ? h("ul", { class: "lista historico" }, r.historico.map((x) => {
    const params = Object.values(JSON.parse(x.params)).join(", ");
    const ok = x.estado === "concluido";
    return h("li", null,
      h("span", { class: `selo ${ok ? "ok" : TERMINADOS.has(x.estado) ? "ruim" : "neutro"}` }, x.estado),
      ` ${NOMES[x.acao] ?? x.acao}${params ? ` (${params})` : ""} `,
      h("small", null, data(x.quando)),
      x.resumo && h("div", { class: "fraco resumo" }, x.resumo));
  })) : h("p", { class: "fraco" }, "Nenhuma ação feita pelo painel ainda."))];
}

async function telaAjustes() {
  const r = await api("GET", "/api/sessoes");
  if (r.ok === false) return [cartao("Ajustes", falha(r))];
  return [
    cartao("Aparelhos conectados", h("ul", { class: "lista" }, r.sessoes.map((s) => h("li", null,
      `${s.aparelho} `, h("small", null, `entrou ${data(s.criada)} · usado ${data(s.vista)}`),
      s.esta ? h("span", { class: "selo neutro" }, "este") : h("button", { type: "button", class: "discreto", onclick: async () => {
        if (!confirm(`Desconectar ${s.aparelho}?`)) return;
        const x = await api("POST", "/api/sessoes/encerrar", { id: s.id });
        if (x.ok === false) avisar(x.erro, "erro");
        atualizar();
      } }, "Desconectar"))))),
    cartao("Conta",
      h("p", { class: "fraco" }, "Para trocar a senha, rode no servidor: sudo atena-painel-senha (todos os aparelhos saem)."),
      h("button", { type: "button", onclick: async () => { await api("POST", "/api/sair", {}); mostrarEntrada(); } }, "Sair deste aparelho")),
  ];
}

const TELAS = { inicio: telaInicio, servicos: telaServicos, pc: telaPC, lab: telaLab, historico: telaHistorico, ajustes: telaAjustes };
const ATUALIZAM_SOZINHAS = new Set(["inicio", "servicos", "pc"]);

// --- navegação --------------------------------------------------------------------------------

let geracao = 0;

function telaAtual() {
  const nome = location.hash.slice(1);
  return TELAS[nome] ? nome : "inicio";
}

async function atualizar() {
  const nome = telaAtual();
  const minha = ++geracao;
  for (const a of document.querySelectorAll(".abas a")) a.classList.toggle("ativa", a.getAttribute("href") === `#${nome}`);
  const tela = $("#tela");
  if (!tela.dataset.tela || tela.dataset.tela !== nome) {
    tela.dataset.tela = nome;
    tela.replaceChildren(h("p", { class: "fraco" }, "Carregando…"));
  }
  const conteudo = await TELAS[nome]();
  if (minha !== geracao || !$("#entrada").hidden) return; // outra tela foi aberta enquanto esta carregava
  tela.replaceChildren(...conteudo.flat(Infinity).filter(Boolean));
}

function abrirJanela(titulo, ...conteudo) {
  $("#janela-titulo").textContent = titulo;
  $("#janela-corpo").replaceChildren(...conteudo.flat(Infinity).filter(Boolean));
  if (!$("#janela").open) $("#janela").showModal();
}

function mostrarEntrada() {
  $(".topo").hidden = true;
  $("#tela").replaceChildren();
  delete $("#tela").dataset.tela;
  $("#entrada").hidden = false;
  $("#senha").focus();
}

function mostrarPainel() {
  $("#entrada").hidden = true;
  $(".topo").hidden = false;
  atualizar();
}

$("#form-entrada").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const botao = evento.target.querySelector("button");
  botao.disabled = true;
  const r = await api("POST", "/api/entrar", { senha: $("#senha").value });
  botao.disabled = false;
  if (r.ok === false) {
    $("#msg-entrada").textContent = r.erro;
    return;
  }
  $("#senha").value = "";
  $("#msg-entrada").textContent = "";
  mostrarPainel();
});

$("#janela-fechar").addEventListener("click", () => $("#janela").close());
addEventListener("hashchange", atualizar);
setInterval(() => {
  if (document.visibilityState === "visible" && $("#entrada").hidden && !$("#janela").open && ATUALIZAM_SOZINHAS.has(telaAtual())) atualizar();
}, INTERVALO);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && $("#entrada").hidden) atualizar();
});

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

const eu = await api("GET", "/api/eu");
if (eu.ok === false && eu.status !== 401) {
  $("#tela").replaceChildren(cartao("Atena", falha(eu)));
} else if (eu.ok !== false) mostrarPainel();
