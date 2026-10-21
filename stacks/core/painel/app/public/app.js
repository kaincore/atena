// Interface do painel: telas montadas com elementos (nunca innerHTML com dados do servidor).

const NOMES = {
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
  "aprovacoes.decidir": "Decisão",
};
const ORDEM_ZONAS = ["core", "ai", "agents", "apps", "lab", "prod"];
const TERMINADOS = new Set(["concluido", "falhou", "recusado", "expirado", "cancelado"]);
const TIQUE = 10_000;

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

// ações que mudam algo: confirma, pede, acompanha o pedido (202) e avisa o resultado.
// acompanhar = false: só avisa que começou (o trabalho do Claude Code leva de minutos a horas)
async function mudar(nome, params, pergunta, acompanhar = true) {
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

function avisar(texto, tipo = "") {
  const aviso = h("div", { class: `aviso ${tipo}` }, texto);
  // com a janela aberta, o aviso vai dentro dela (a janela fica por cima de tudo)
  ($("#janela").open ? $("#janela-avisos") : $("#avisos")).append(aviso);
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

// --- lab: os apps que o Claude Code fez e os trabalhos dele ------------------------------------------

const NOME_PROJETO = "[a-z0-9][a-z0-9\\-]{0,39}";
const rascunho = { projeto: "", pedido: "", conta: "", modelo: "", esforco: "", minutos: "60", somente_plano: false, publicar: false };

// os botões de um app; cada um confirma, pede e recarrega a tela
function botoesApp(p) {
  const publicado = p.app !== "não publicado";
  const noAr = /^Up/.test(p.app);
  const fazer = (nome, pergunta, params = {}) => async () => {
    if (await mudar(nome, { projeto: p.projeto, ...params }, pergunta)) atualizar();
  };
  return h("span", { class: "botoes" },
    p.em_andamento && h("button", { type: "button", onclick: fazer("app.cancelar",
      `Parar o que está em andamento em ${p.projeto} (trabalho do Claude Code, construção ou pedido esperando o celular)?`) }, "Cancelar"),
    p.codigo && !p.em_andamento && h("button", { type: "button", onclick: fazer("app.publicar",
      `${publicado ? "Publicar de novo" : "Publicar"} ${p.projeto} na rede de casa? Constrói pelo Dockerfile; pode levar alguns minutos.`) },
      publicado ? "Publicar de novo" : "Publicar"),
    publicado && h("button", { type: "button", class: "discreto", onclick: fazer("app.reiniciar", `Reiniciar o app ${p.projeto}?`) }, "Reiniciar"),
    noAr && h("button", { type: "button", class: "discreto", onclick: fazer("app.parar", `Tirar o app ${p.projeto} do ar? Os dados ficam.`) }, "Parar"),
    noAr && h("button", { type: "button", class: "discreto", onclick: () => janelaComando(p.projeto) }, "Comando"),
    !p.em_andamento && h("button", { type: "button", class: "discreto perigo", onclick: () => janelaApagar(p) }, "Apagar"));
}

function janelaComando(projeto) {
  const saida = h("div");
  const campo = h("input", { name: "comando", required: true, placeholder: "ex.: ls -la /data", autocomplete: "off" });
  abrirJanela(`Comando em ${projeto}`,
    h("p", { class: "fraco" }, "Roda dentro do container do app, como o usuário dele (sh -c), por até 30 s. Fica no histórico."),
    h("form", { class: "resposta", onsubmit: async (evento) => {
      evento.preventDefault();
      const botao = evento.currentTarget.querySelector("button");
      botao.disabled = true;
      saida.replaceChildren(h("p", { class: "fraco" }, "Rodando…"));
      const r = await consultar("app.comando", { projeto, comando: campo.value });
      botao.disabled = false;
      saida.replaceChildren(...(r.ok === false ? [falha(r)] : [
        linha("Código de saída", h("span", { class: `selo ${r.resultado.codigo === 0 ? "ok" : "ruim"}` }, String(r.resultado.codigo))),
        h("pre", { class: "log" }, r.resultado.saida || "(sem saída)"),
        r.resultado.dica && h("p", { class: "fraco" }, r.resultado.dica),
      ].filter(Boolean)));
    } }, campo, h("button", { type: "submit" }, "Rodar")),
    saida);
  campo.focus();
}

function janelaApagar(p) {
  const publicado = p.app !== "não publicado";
  const opcao = (valor, texto, marcado) => h("label", { class: "opcao" },
    h("input", { type: "checkbox", name: "partes", value: valor, checked: marcado }), ` ${texto}`);
  const confirmacao = h("input", { name: "nome", autocomplete: "off", placeholder: p.projeto });
  const aviso = h("p", { class: "erro" });
  const form = h("form", { class: "resposta", onsubmit: async (evento) => {
    evento.preventDefault();
    const partes = [...form.querySelectorAll("input[name=partes]:checked")].map((x) => x.value);
    if (!partes.length) return void (aviso.textContent = "Escolha o que apagar.");
    if (partes.includes("dados") && confirmacao.value.trim() !== p.projeto)
      return void (aviso.textContent = `Para apagar os dados, digite ${p.projeto}.`);
    $("#janela").close();
    if (await mudar("app.apagar", { projeto: p.projeto, partes })) atualizar();
  } },
    publicado && opcao("docker", "Tirar do Docker: o container e a imagem (publicar de novo reconstrói)", true),
    p.codigo && opcao("codigo", "Código: vai para a lixeira, onde dá para restaurar por 30 dias", !publicado),
    p.dados_guardados && [opcao("dados", "Dados do app (sai do Docker junto): NÃO TEM VOLTA", false),
      h("label", null, `Para apagar os dados, digite ${p.projeto}: `, confirmacao)],
    aviso,
    h("button", { type: "submit", class: "perigo" }, "Apagar"));
  abrirJanela(`Apagar ${p.projeto}`, form);
}

const ESTADOS_TRABALHO = { planejando: "planejando", executando: "rodando", aguardando: "esperando o celular" };

function itemTrabalho(t) {
  const rodando = t.estado === "planejando" || t.estado === "executando";
  const quem = t.cliente && t.cliente !== "painel" ? (t.cliente === "hermes" ? "pela Atena" : `por ${t.cliente}`) : null;
  return h("li", null,
    h("div", { class: "stack-topo" },
      h("span", null,
        h("span", { class: `selo ${t.estado === "concluido" ? "ok" : ESTADOS_TRABALHO[t.estado] ? "neutro" : "ruim"}` }, ESTADOS_TRABALHO[t.estado] ?? t.estado),
        ` ${t.projeto ?? "?"} `),
      rodando && h("button", { type: "button", class: "discreto", onclick: async () => {
        if (await mudar("claude.cancelar", { pedido: t.id }, `Interromper o trabalho ${t.id} em ${t.projeto}? A conversa fica guardada.`)) atualizar();
      } }, "Cancelar")),
    h("div", null, t.pedido),
    h("small", null, [quem, t.conta, t.modelo, t.esforco, t.criado, `trabalho ${t.id}`, t.commits ? `${t.commits} commits` : null].filter(Boolean).join(" · ")),
    t.esperando_permissao_no_celular && h("div", null, h("a", { href: "#aprovacoes" }, "Esperando a sua permissão: ver em Aprovações")),
    t.resumo && h("details", null, h("summary", null, "Resumo"), h("pre", { class: "texto-pedido" }, t.resumo)));
}

function cartaoNovoTrabalho(trabalhos, projetos) {
  const contas = trabalhos.contas_com_login ?? [];
  if (!rascunho.conta || !contas.includes(rascunho.conta)) rascunho.conta = contas[0] ?? "";
  const guardar = (evento) => {
    const f = evento.currentTarget;
    Object.assign(rascunho, {
      projeto: f.projeto.value, pedido: f.pedido.value, conta: f.conta.value, modelo: f.modelo.value, esforco: f.esforco.value,
      minutos: f.minutos.value, somente_plano: f.somente_plano.checked, publicar: f.publicar.checked,
    });
  };
  const opcoes = (nome, lista) => h("select", { name: nome }, lista.map(([v, t]) => h("option", { value: v, selected: v === rascunho[nome] }, t)));
  const marcar = (nome, texto) => h("label", { class: "opcao" }, h("input", { type: "checkbox", name: nome, checked: rascunho[nome] }), ` ${texto}`);
  return cartao("Novo trabalho do Claude Code",
    contas.length ? null : h("p", { class: "erro" }, "Nenhuma conta do Claude Code com login no servidor (sudo atena-claude-conta entrar <conta>)."),
    h("form", { class: "resposta", oninput: guardar, onchange: guardar, onsubmit: async (evento) => {
      evento.preventDefault();
      guardar(evento);
      const params = { projeto: rascunho.projeto.trim(), pedido: rascunho.pedido.trim(), conta: rascunho.conta, minutos: Number(rascunho.minutos),
        ...(rascunho.modelo ? { modelo: rascunho.modelo } : {}), ...(rascunho.esforco ? { esforco: rascunho.esforco } : {}),
        ...(rascunho.somente_plano ? { somente_plano: true } : {}), ...(rascunho.publicar ? { publicar: true } : {}) };
      const r = await mudar("claude.tarefa", params, null, false);
      if (r && r.ok !== false) {
        Object.assign(rascunho, { projeto: "", pedido: "", somente_plano: false, publicar: false });
        atualizar();
      }
    } },
      h("label", null, "Projeto ", h("input", { name: "projeto", list: "projetos-lab", required: true, pattern: NOME_PROJETO,
        value: rascunho.projeto, placeholder: "lista-compras", autocomplete: "off", title: "minúsculas, números e hífen" })),
      h("datalist", { id: "projetos-lab" }, projetos.map((p) => h("option", { value: p.projeto }))),
      h("textarea", { name: "pedido", rows: "4", minlength: "3", maxlength: "4000", required: true,
        placeholder: "O que o Claude Code deve fazer (um nome de projeto novo cria a pasta)" }, rascunho.pedido),
      h("div", { class: "filtros" },
        h("label", null, "Conta ", opcoes("conta", contas.map((c) => [c, c]))),
        h("label", null, "Modelo ", opcoes("modelo", [["", "padrão"], ["fable", "fable"], ["opus", "opus"], ["sonnet", "sonnet"], ["haiku", "haiku"]])),
        h("label", null, "Esforço ", opcoes("esforco", [["", "padrão"], ...["low", "medium", "high", "xhigh", "max"].map((e) => [e, e])])),
        h("label", null, "Tempo ", opcoes("minutos", [["15", "15 min"], ["30", "30 min"], ["60", "1 h"], ["120", "2 h"], ["240", "4 h"], ["600", "10 h"]]))),
      h("div", { class: "filtros" },
        marcar("somente_plano", "só planejar (não muda nada)"),
        marcar("publicar", "publicar quando terminar bem")),
      h("button", { type: "submit", disabled: !contas.length }, "Mandar")),
    h("p", { class: "fraco" }, "O Claude Code trabalha sozinho na pasta do projeto, sem sudo e sem Docker. As permissões e perguntas dele aparecem em Aprovações e no celular."));
}

async function cartaoTrabalhos(trabalhos) {
  const c = trabalhos.ok === false ? cartao("Trabalhos do Claude Code", falha(trabalhos), semAcao(trabalhos, "claude.trabalhos"))
    : cartao("Trabalhos do Claude Code", trabalhos.resultado.trabalhos.length
      ? h("ul", { class: "lista" }, trabalhos.resultado.trabalhos.map(itemTrabalho))
      : h("p", { class: "fraco" }, "Nenhum trabalho ainda."));
  c.append(botaoAtualizar(async () => c.replaceWith(await cartaoTrabalhos(await consultar("claude.trabalhos")))));
  return c;
}

async function telaLab() {
  const [r, trabalhos] = await Promise.all([consultar("app.lista"), consultar("claude.trabalhos")]);
  if (r.ok === false) return [cartao("Lab", falha(r))];
  const { projetos, lixeira } = r.resultado;
  const apps = cartao("Apps do lab", projetos.length ? projetos.map((p) => h("div", { class: "stack" },
    h("div", { class: "stack-topo" }, h("strong", null, p.projeto), botoesApp(p)),
    linha("App", p.app),
    p.fora_de_casa && linha("Endereço", h("a", { href: p.fora_de_casa, target: "_blank", rel: "noopener" }, p.fora_de_casa)),
    p.endereco && linha("Na rede de casa", h("a", { href: p.endereco, target: "_blank", rel: "noopener" }, p.endereco)),
    linha("Guardado", [p.codigo ? "código" : "sem código", p.dados_guardados ? "dados" : "sem dados"].join(" · ")),
    p.em_andamento && linha("Em andamento", `pedido ${p.em_andamento}`),
  )) : h("p", { class: "fraco" }, "Nenhum projeto no lab ainda. Mande um trabalho ao Claude Code para começar."));
  return [
    trabalhos.ok === false ? null : cartaoNovoTrabalho(trabalhos.resultado, projetos),
    await cartaoTrabalhos(trabalhos),
    apps,
    lixeira.length ? cartao("Lixeira", h("ul", { class: "lista" }, lixeira.map((l) => h("li", null,
      h("div", { class: "stack-topo" },
        h("span", null, l.projeto, h("small", null, ` apagado em ${l.apagado_em}; some de vez em ${l.some_de_vez_em}`)),
        h("button", { type: "button", class: "discreto", onclick: async () => {
          if (await mudar("app.restaurar", { projeto: l.projeto }, `Trazer o código de ${l.projeto} de volta da lixeira?`)) atualizar();
        } }, "Restaurar")))))) : null,
  ];
}

async function telaHistorico() {
  let r = await api("GET", "/api/historico");
  // o que ficou em andamento quando a tela fechou: pergunta ao executor como terminou
  const abertos = r.ok === false ? [] : r.historico.filter((x) => x.pedido && !TERMINADOS.has(x.estado)).slice(0, 10);
  if (abertos.length) {
    await Promise.all(abertos.map((x) => api("GET", `/api/pedido/${x.pedido}`)));
    r = await api("GET", "/api/historico");
  }
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

// --- central de aprovações e atividade do executor (os tempos do executor vêm em segundos) ---------

const hora = (s) => new Date(s * 1000).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });

function relativo(s) {
  const minutos = Math.round((s * 1000 - Date.now()) / 60000);
  if (minutos === 0) return "agora";
  return minutos > 0 ? `em ${minutos} min` : `há ${-minutos} min`;
}

// executor antigo ou token do painel sem as ações da central
function semCentral(r) {
  if (r.status !== 403 && r.status !== 404) return null;
  return h("p", { class: "fraco" }, "A central precisa do executor novo e das ações aprovacoes.lista, aprovacoes.decidir e atividade.lista no token do painel (rode o instalador com --painel).");
}

function marcarPendentes(n) {
  const aba = document.querySelector('.abas a[href="#aprovacoes"]');
  if (aba) aba.textContent = n ? `Aprovações (${n})` : "Aprovações";
  document.title = n ? `(${n}) Atena` : "Atena";
}

async function contarPendentes() {
  const r = await consultar("aprovacoes.lista");
  if (r.ok !== false) marcarPendentes(r.resultado.pendentes.length);
}

async function decidirPedido(p, decisao, resposta) {
  const r = await mudar("aprovacoes.decidir", { pedido: p.id, decisao, ...(resposta ? { resposta } : {}) });
  const resultado = r?.resultado?.resultado;
  if (resultado === "expirado") avisar(`O pedido ${p.id} já tinha vencido; nada foi feito.`, "erro");
  else if (resultado === "ignorado") avisar(`O pedido ${p.id} já tinha sido decidido.`, "erro");
  atualizar();
}

function cartaoPendente(p) {
  const meta = h("p", { class: "fraco" }, [p.cliente, p.acao, `pedido ${p.id}`, `pedido ${relativo(p.criado)}`,
    `vence ${relativo(p.expira)}`, p.origem && `origem ${p.origem}`].filter(Boolean).join(" · "));
  if (p.tipo === "pergunta") {
    const campo = h("textarea", { rows: "2", maxlength: "2000", placeholder: "Ou escreva a resposta" });
    return cartao(p.titulo ?? "Pergunta do Claude Code", meta,
      h("p", { class: "pergunta" }, p.pergunta),
      p.por_que && h("p", { class: "fraco" }, `Por quê: ${p.por_que}`),
      p.opcoes.length > 0 && h("div", { class: "botoes" }, p.opcoes.map((o) =>
        h("button", { type: "button", onclick: () => decidirPedido(p, "responder", o) }, o))),
      h("form", { class: "resposta", onsubmit: (evento) => {
        evento.preventDefault();
        if (campo.value.trim()) decidirPedido(p, "responder", campo.value.trim());
      } }, campo, h("button", { type: "submit" }, "Responder")));
  }
  const params = Object.entries(p.params ?? {});
  return cartao(p.titulo ?? p.acao, meta,
    p.texto && h("pre", { class: "texto-pedido" }, p.texto),
    params.length > 0 && h("details", null, h("summary", null, "Parâmetros"),
      h("ul", { class: "lista" }, params.map(([k, v]) => h("li", null, h("span", { class: "rotulo" }, `${k}: `), v)))),
    h("div", { class: "botoes grandes" },
      h("button", { type: "button", onclick: () => decidirPedido(p, "aprovar") }, "Aprovar"),
      h("button", { type: "button", class: "discreto", onclick: () => decidirPedido(p, "recusar") }, "Recusar")));
}

async function telaAprovacoes() {
  const r = await consultar("aprovacoes.lista");
  if (r.ok === false) return [cartao("Aprovações", falha(r), semCentral(r))];
  const { pendentes, recentes } = r.resultado;
  marcarPendentes(pendentes.length);
  return [
    pendentes.length ? pendentes.map(cartaoPendente)
      : cartao("Aprovações", h("p", { class: "fraco" }, "Nada esperando por você. Os pedidos da Atena e do Claude Code aparecem aqui e no celular.")),
    cartao("Decididos há pouco", recentes.length ? h("ul", { class: "lista" }, recentes.map((x) => h("li", null,
      h("span", { class: `selo ${x.estado === "concluido" ? "ok" : TERMINADOS.has(x.estado) ? "ruim" : "neutro"}` }, x.estado),
      ` ${x.titulo ?? x.acao} `,
      h("small", null, [x.cliente, hora(x.quando), x.por && `por ${x.por}`].filter(Boolean).join(" · ")),
      x.erro && h("div", { class: "fraco resumo" }, x.erro)))) : h("p", { class: "fraco" }, "Nenhum ainda.")),
  ];
}

const filtro = { cliente: "", so_erros: false, linhas: 200 };
const clientesVistos = new Set(["hermes", "painel"]);

function linhaAtividade(i) {
  const erro = i.ok === false || Boolean(i.erro);
  const oque = i.acao && i.evento ? `${i.evento}: ${i.acao}` : i.acao ?? i.evento ?? "?";
  const detalhes = [
    i.params && Object.entries(i.params).map(([k, v]) => `${k}=${v}`).join(" "),
    i.decisao && `decisão ${i.decisao}${i.por ? ` por ${i.por}` : ""}`,
    i.pedido && `pedido ${i.pedido}`, i.aprovacao && `aprovação ${i.aprovacao}`,
    i.origem && `origem ${i.origem}`, i.segundos != null && `${i.segundos} s`,
  ].filter(Boolean).join(" · ");
  return h("li", null,
    h("span", { class: `selo ${erro ? "ruim" : i.ok ? "ok" : "neutro"}` }, erro ? "erro" : i.ok ? "ok" : "evento"),
    ` ${oque} `, h("small", null, `${i.cliente ?? "executor"} · ${hora(i.quando)}`),
    detalhes && h("div", { class: "fraco resumo" }, detalhes),
    i.erro && h("div", { class: "erro resumo" }, i.erro));
}

async function telaAtividade() {
  const r = await consultar("atividade.lista", { linhas: filtro.linhas, so_erros: filtro.so_erros, ...(filtro.cliente ? { cliente: filtro.cliente } : {}) });
  if (r.ok === false) return [cartao("Atividade", falha(r), semCentral(r))];
  for (const i of r.resultado.itens) if (i.cliente) clientesVistos.add(i.cliente);
  const controles = h("form", { class: "filtros", onchange: (evento) => {
    const f = evento.currentTarget;
    filtro.cliente = f.cliente.value;
    filtro.so_erros = f.so_erros.checked;
    filtro.linhas = Number(f.linhas.value);
    atualizar();
  } },
    h("label", null, "Cliente ", h("select", { name: "cliente" }, ["", ...[...clientesVistos].sort()].map((c) =>
      h("option", { value: c, selected: c === filtro.cliente }, c || "todos")))),
    h("label", null, h("input", { type: "checkbox", name: "so_erros", checked: filtro.so_erros }), " só erros"),
    h("label", null, "Linhas ", h("select", { name: "linhas" }, [100, 200, 500, 1000].map((n) =>
      h("option", { value: String(n), selected: n === filtro.linhas }, String(n))))));
  const itens = r.resultado.itens;
  const c = cartao("Atividade do executor", controles,
    h("p", { class: "fraco" }, "Tudo o que a Atena, o painel e o lab pediram ao executor, as suas decisões e os eventos dele, do mais novo ao mais velho."),
    itens.length ? h("ul", { class: "lista atividade" }, itens.map(linhaAtividade)) : h("p", { class: "fraco" }, "Nada no registro com esse filtro."));
  c.classList.add("largo");
  return [c];
}

// --- sistema: sensores, processos, rede e o registro do systemd ---------------------------------
// Cada cartão se refaz sozinho (botão Atualizar, filtros), sem recarregar a tela toda.

// token do painel sem a ação (instalado antes desta versão)
function semAcao(r, nome) {
  if (r.status !== 403) return null;
  return h("p", { class: "fraco" }, `O token do painel ainda não tem ${nome} (rode o instalador com --painel).`);
}

function botaoAtualizar(refazer) {
  return h("div", { class: "botoes" }, h("button", { type: "button", class: "discreto", onclick: (evento) => {
    evento.currentTarget.disabled = true;
    refazer();
  } }, "Atualizar"));
}

function grau(rotulo, c, quente) {
  if (c == null) return linha(rotulo, "sem leitura");
  return [linha(rotulo, `${c} °C`), medidor(c / quente, 1)];
}

async function cartaoSensores() {
  const r = await consultar("sistema.sensores");
  const c = r.ok === false ? cartao("Sensores", falha(r), semAcao(r, "sistema.sensores")) : (() => {
    const s = r.resultado;
    const placa = s.placa ?? {};
    return cartao("Sensores",
      linha("Avaliação", h("span", { class: `selo ${s.avaliacao === "normal" ? "ok" : "ruim"}` }, s.avaliacao)),
      grau("CPU", s.cpu.temperatura_c, s.cpu.quente_a_partir_de_c),
      s.cpu.nucleos_c && linha("Núcleos", Object.entries(s.cpu.nucleos_c).map(([n, t]) => `${n} ${t} °C`).join(" · ")),
      grau("NVMe", s.nvme.temperatura_c, s.nvme.alerta_c),
      s.gpu && [grau("GPU", s.gpu.temperatura_c, s.gpu.quente_a_partir_de_c),
        linha("GPU agora", [s.gpu.uso_pct != null && `uso ${s.gpu.uso_pct}%`, s.gpu.consumo_w != null && `${s.gpu.consumo_w} W`,
          s.gpu.ventoinha_pct != null && `ventoinha ${s.gpu.ventoinha_pct}%`].filter(Boolean).join(" · ") || "sem leitura")],
      Object.entries(placa.ventoinhas_rpm ?? {}).map(([f, rpm]) => linha(`Ventoinha ${f}`, `${rpm} RPM`)),
      placa.temperaturas_c && h("details", null, h("summary", null, "Sensores da placa"),
        h("ul", { class: "lista" }, Object.entries(placa.temperaturas_c).map(([n, t]) => h("li", null, `${n}: ${t} °C`)))),
      placa.obs && h("p", { class: "fraco" }, placa.obs),
      s.cpu.quente_a_partir_de_c && h("p", { class: "fraco" }, `As barras enchem até o ponto de alerta (CPU ${s.cpu.quente_a_partir_de_c} °C).`));
  })();
  c.append(botaoAtualizar(async () => c.replaceWith(await cartaoSensores())));
  return c;
}

// "1-21:19:42" (dias-horas:min:seg, como o ps mostra) em "1 d 21 h"
function duracao(etime) {
  const [dias, resto] = etime.includes("-") ? etime.split("-") : ["0", etime];
  const [s = 0, m = 0, hr = 0] = resto.split(":").reverse().map(Number);
  if (+dias) return `${+dias} d ${hr} h`;
  if (hr) return `${hr} h ${m} min`;
  return m ? `${m} min` : `${s} s`;
}

const tamanho = (kb) => (kb >= 1024 * 1024 ? gb(kb / 1024) : `${Math.round(kb / 1024)} MB`);

// a saída do ps: PID USER %CPU %MEM RSS ELAPSED COMMAND
function lerProcessos(texto) {
  return texto.split("\n").slice(1).filter((l) => l.trim()).map((l) => {
    const [pid, usuario, cpu, mem, rss, tempo, ...comando] = l.trim().split(/\s+/);
    return { pid, usuario, cpu, mem, rss: Number(rss), tempo, comando: comando.join(" ") };
  });
}

const processosOrdem = { ordem: "cpu" };

async function cartaoProcessos() {
  const r = await consultar("sistema.processos", { ordem: processosOrdem.ordem, quantos: 25 });
  const refazer = async () => c.replaceWith(await cartaoProcessos());
  const escolha = h("label", { class: "filtros" }, "Mais usam ", h("select", { onchange: (evento) => {
    processosOrdem.ordem = evento.target.value;
    refazer();
  } }, [["cpu", "CPU"], ["ram", "RAM"]].map(([v, t]) => h("option", { value: v, selected: v === processosOrdem.ordem }, t))));
  const c = r.ok === false ? cartao("Processos", falha(r), semAcao(r, "sistema.processos")) : cartao("Processos", escolha,
    h("ul", { class: "lista processos" }, lerProcessos(r.resultado).map((p) => h("li", null,
      h("div", { class: "comando", title: p.comando, onclick: (evento) => evento.currentTarget.classList.toggle("aberto") }, p.comando),
      h("small", null, `${p.usuario} · CPU ${p.cpu}% · RAM ${tamanho(p.rss)} · pid ${p.pid} · há ${duracao(p.tempo)}`)))),
    h("p", { class: "fraco" }, "A CPU é a média desde que o processo começou (é assim que o ps mede). Toque no comando para ver inteiro."));
  c.append(botaoAtualizar(refazer));
  return c;
}

// --- rede: o ip -br addr e o ss -tuln do servidor ---

function tipoInterface(nome) {
  if (nome === "lo") return "só o servidor";
  if (nome.startsWith("tailscale")) return "Tailscale";
  if (/^(br-|docker|veth)/.test(nome)) return "containers";
  return "rede de casa";
}

function lerInterfaces(texto) {
  return texto.split("\n").filter((l) => l.trim()).map((l) => {
    const [nome, estado, ...enderecos] = l.trim().split(/\s+/);
    return { nome: nome.split("@")[0], estado, enderecos: enderecos.map((e) => e.split("/")[0]) };
  });
}

// "100.64.0.1%tailscale0:3000", "[::1]:323", "*:5353" → onde a porta está aberta
function lerPortas(texto, interfaces) {
  const deQuem = new Map(interfaces.flatMap((i) => i.enderecos.map((e) => [e, i.nome])));
  const portas = new Map();
  for (const l of texto.split("\n")) {
    const [proto, , , , local] = l.trim().split(/\s+/);
    if (!local) continue;
    const corte = local.lastIndexOf(":");
    const [endereco, iface] = local.slice(0, corte).replace(/[[\]]/g, "").split("%");
    const porta = Number(local.slice(corte + 1));
    const alcance = iface ? tipoInterface(iface)
      : ["0.0.0.0", "::", "*"].includes(endereco) ? "todas as redes"
      : /^127\.|^::1$/.test(endereco) ? "só o servidor"
      : deQuem.has(endereco) ? tipoInterface(deQuem.get(endereco)) : endereco;
    const chave = `${porta}/${proto}`;
    if (!portas.has(chave)) portas.set(chave, { porta, proto, alcances: new Set(), enderecos: new Set() });
    portas.get(chave).alcances.add(alcance);
    portas.get(chave).enderecos.add(endereco);
  }
  return [...portas.values()].sort((a, b) => a.porta - b.porta || a.proto.localeCompare(b.proto));
}

async function cartaoRede() {
  const r = await consultar("sistema.rede");
  const c = r.ok === false ? cartao("Rede", falha(r), semAcao(r, "sistema.rede")) : (() => {
    const interfaces = lerInterfaces(r.resultado.enderecos);
    const visiveis = interfaces.filter((i) => !i.nome.startsWith("veth"));
    const portas = lerPortas(r.resultado.portas, interfaces);
    return cartao("Rede",
      h("h3", null, "Endereços"),
      h("ul", { class: "lista" }, visiveis.map((i) => h("li", null,
        h("strong", null, i.nome), ` ${tipoInterface(i.nome)} `,
        i.estado === "DOWN" && h("span", { class: "selo neutro" }, "desligada"),
        h("div", { class: "fraco resumo" }, i.enderecos.filter((e) => !e.startsWith("fe80:")).join(" · ") || "sem endereço")))),
      interfaces.length > visiveis.length && h("p", { class: "fraco" }, `Mais ${interfaces.length - visiveis.length} interfaces veth, uma por container.`),
      h("h3", null, `Portas abertas (${portas.length})`),
      h("ul", { class: "lista" }, portas.map((p) => h("li", null,
        h("strong", null, `${p.porta}`), h("small", null, ` ${p.proto} `),
        [...p.alcances].map((a) => h("span", { class: `selo ${a === "todas as redes" ? "ruim" : "neutro"}` }, a)),
        h("div", { class: "fraco resumo" }, [...p.enderecos].join(" · "))))),
      h("p", { class: "fraco" }, "Aberta aqui não quer dizer aberta lá fora: o firewall (ufw) ainda filtra o que chega."));
  })();
  c.append(botaoAtualizar(async () => c.replaceWith(await cartaoRede())));
  return c;
}

// --- registro do systemd (journalctl) ---

const registro = { unidade: "", prioridade: "err", desde: "6h", linhas: 100 };
const UNIDADES_COMUNS = ["atena-executor.service", "docker.service", "containerd.service", "ssh.service", "tailscaled.service", "ufw.service"];
let unidadesVistas = null;

async function cartaoRegistro() {
  const [r, sistema] = await Promise.all([
    consultar("servico.journal", {
      linhas: registro.linhas, ...(registro.unidade ? { unidade: registro.unidade } : {}),
      ...(registro.prioridade ? { prioridade: registro.prioridade } : {}), ...(registro.desde ? { desde: registro.desde } : {}),
    }),
    unidadesVistas ? null : consultar("status.sistema"),
  ]);
  if (sistema && sistema.ok !== false) unidadesVistas = sistema.resultado.unidades.map((u) => u.nome);
  const opcoes = (nome, lista) => h("select", { name: nome }, lista.map(([v, t]) =>
    h("option", { value: String(v), selected: String(v) === String(registro[nome]) }, t)));
  const formulario = h("form", { class: "filtros", onsubmit: async (evento) => {
    evento.preventDefault();
    const f = evento.currentTarget;
    Object.assign(registro, { unidade: f.unidade.value.trim(), prioridade: f.prioridade.value, desde: f.desde.value, linhas: Number(f.linhas.value) });
    f.querySelector("button").disabled = true;
    c.replaceWith(await cartaoRegistro());
  } },
    h("label", null, "Unidade ", h("input", { name: "unidade", list: "unidades", value: registro.unidade, placeholder: "o sistema todo", size: "22" })),
    h("datalist", { id: "unidades" }, [...new Set([...UNIDADES_COMUNS, ...(unidadesVistas ?? [])])].sort().map((u) => h("option", { value: u }))),
    h("label", null, "Gravidade ", opcoes("prioridade", [["", "todas"], ["warning", "avisos e erros"], ["err", "só erros"], ["crit", "só críticos"]])),
    h("label", null, "Período ", opcoes("desde", [["30min", "30 min"], ["1h", "1 h"], ["6h", "6 h"], ["24h", "24 h"], ["7d", "7 dias"], ["", "tudo"]])),
    h("label", null, "Linhas ", opcoes("linhas", [[50, "50"], [100, "100"], [200, "200"]])),
    h("button", { type: "submit" }, "Ver"));
  const texto = r.ok === false ? null : r.resultado.trim();
  const log = texto && h("pre", { class: "log" }, texto);
  const c = cartao("Registro do systemd", formulario,
    r.ok === false ? [falha(r), semAcao(r, "servico.journal")]
      : log || h("p", { class: "fraco" }, "Nada no registro com esse filtro."),
    h("p", { class: "fraco" }, "As linhas mais novas ficam embaixo. Segredos saem ocultos."));
  c.classList.add("largo");
  if (log) requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; }); // já na tela: rola até o mais novo
  return c;
}

async function telaSistema() {
  return Promise.all([cartaoSensores(), cartaoProcessos(), cartaoRede(), cartaoRegistro()]);
}

const TELAS = {
  inicio: telaInicio, aprovacoes: telaAprovacoes, servicos: telaServicos, sistema: telaSistema, pc: telaPC, lab: telaLab,
  atividade: telaAtividade, historico: telaHistorico, ajustes: telaAjustes,
};
// de quantos em quantos tiques (10 s) cada tela se atualiza sozinha
const ATUALIZAM_SOZINHAS = { aprovacoes: 1, inicio: 3, servicos: 3, pc: 3 };

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
  if (telaAtual() !== "aprovacoes") contarPendentes();
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
let tiques = 0;
setInterval(() => {
  if (document.visibilityState !== "visible" || !$("#entrada").hidden) return;
  tiques++;
  const cada = ATUALIZAM_SOZINHAS[telaAtual()];
  // não apaga uma resposta que você está escrevendo
  const escrevendo = [...document.querySelectorAll("#tela textarea")].some((t) => t.value || t === document.activeElement);
  if (cada && tiques % cada === 0 && !$("#janela").open && !escrevendo) atualizar();
  else if (telaAtual() !== "aprovacoes" && tiques % 3 === 0) contarPendentes();
}, TIQUE);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && $("#entrada").hidden) atualizar();
});

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

const eu = await api("GET", "/api/eu");
if (eu.ok === false && eu.status !== 401) {
  $("#tela").replaceChildren(cartao("Atena", falha(eu)));
} else if (eu.ok !== false) mostrarPainel();
