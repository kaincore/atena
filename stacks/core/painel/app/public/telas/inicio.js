// Início: uma lâmina só, planejada como uma prancha impressa. No alto, a cabeça da folha: a data, a frase do dia
// escrita a partir dos dados e, quando há algo, a rubrica com o que pede você. No meio, as duas pranchas (o
// instrumento do servidor, com a legenda das letras, e a crepidoma das zonas); nas margens, as notas: a agenda e as
// pendências de um lado, o gasto e o systemd do outro; embaixo, o colofão com a hora da leitura. Rolando para
// baixo, o que importa não se perde: uma régua presa no alto da tela guarda os pedidos, as zonas e as leituras
// fora do limite.
import { api, atualizar, avisar, cartao, consultar, containerOk, dinheiro, falha, gb, h, item, itens, linha, medidor,
  modulo, num, plural, statusDocker } from "../comum.js";
import { daAtena, proximosDeTodos, quandoTexto } from "./agenda.js";
import { abrirPedido, quem, relativo } from "./aprovacoes.js";
import { abrirZona, marcarZonas, resumirZonas } from "../zonas.js";
import { crepidoma, prancha, s, tom } from "../desenhos.js";
import { desenhavel } from "../ornamentos.js";

const GREGAS = ["Α", "Β", "Γ", "Δ", "Ε", "Ζ"];
// como cada leitura se chama na régua (curto) e na frase do dia; os discos são "Disco /srv" e "o disco /srv"
const CHAMAR = { CPU: ["CPU", "a CPU"], RAM: ["RAM", "a RAM"], Temperatura: ["Temp.", "a temperatura"], GPU: ["GPU", "a GPU"] };

// as leituras do instrumento, de fora para dentro: a CPU, a RAM, a temperatura, a GPU e cada disco, com o
// limite de cada uma (a tinta passa a ocre perto dele e a cinábrio passado dele, como nos medalhões). n e fmt
// deixam o número andar de um valor ao outro
function leituras(r) {
  const carga = r.carga[0] / r.nucleos;
  const usada = (r.ram_total_mb - r.ram_disponivel_mb) / 1024, total = r.ram_total_mb / 1024;
  const cpu = r.temperaturas.cpu_c;
  const leitura = (nome, n, casas, unidade, nota, fracao, alerta, limite) => ({ nome, n, fmt: (x) => `${num(x, casas)}${unidade}`, nota, fracao, alerta, limite });
  return [
    leitura("CPU", Math.min(99.9, carga * 100), carga < 0.1 ? 1 : 0, "%", `carga ${num(r.carga[0], 2)} em ${r.nucleos} núcleos`, carga, 1, "100% de carga"),
    leitura("RAM", usada, 1, "\u00a0GB", `de ${num(total, 1)}\u00a0GB`, usada / total, 0.95, `${num(total * 0.95, 1)}\u00a0GB`),
    cpu != null && leitura("Temperatura", cpu, 1, "\u00a0°C", "da CPU", cpu / 85, 1, "85\u00a0°C"),
    r.gpu && leitura("GPU", r.gpu.temperatura_c, 0, "\u00a0°C",
      `uso ${num(r.gpu.uso_pct)}% · VRAM ${num(r.gpu.vram_usada_mb / 1024, 1)} de ${num(r.gpu.vram_total_mb / 1024, 1)}\u00a0GB`, r.gpu.temperatura_c / 85, 1, "85\u00a0°C"),
    ...Object.entries(r.discos).map(([ponto, d]) => leitura(`Disco ${ponto}`, 100 * (1 - d.livre_gb / d.total_gb), 0, "%",
      `${num(d.livre_gb, 1)}\u00a0GB livres de ${num(d.total_gb, 1)}\u00a0GB`, 1 - d.livre_gb / d.total_gb, 0.9, "90%")),
  ].filter(Boolean).slice(0, GREGAS.length)
    .map((l, i) => ({ ...l, valor: l.fmt(l.n), letra: GREGAS[i], tom: tom(Math.min(1, l.fracao) / l.alerta),
      curto: CHAMAR[l.nome]?.[0] ?? l.nome, frase: CHAMAR[l.nome]?.[1] ?? `o ${l.nome.toLowerCase()}` }));
}

// as notas da margem: o módulo sem a placa, só o título com a régua e o conteúdo
const nota = (el, nome) => {
  el?.classList.add("nota", `n-${nome}`);
  return el;
};

const reduzido = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

// o número anda do valor de antes ao novo, junto com a tinta do anel (o mesmo jeito de assentar)
function contar(els, l, de, atraso, dura) {
  if (reduzido() || Math.abs(de - l.n) < 1e-6) return;
  const inicio = performance.now() + atraso;
  for (const el of els) el.textContent = l.fmt(de);
  const passo = (agora) => {
    const x = Math.max(0, Math.min(1, (agora - inicio) / dura));
    const v = de + (l.n - de) * (1 - (1 - x) ** 4);
    for (const el of els) el.textContent = x < 1 ? l.fmt(v) : l.valor;
    if (x < 1) requestAnimationFrame(passo);
  };
  requestAnimationFrame(passo);
}

// a última leitura vista neste aparelho: ao abrir de novo, o número conta dela até a de agora (nunca do zero,
// que seria um número que o servidor não deu); a primeira vez no aparelho, ele já nasce certo
const GUARDADAS = "atena-leituras";
const vistos = new Map((() => {
  try { return Object.entries(JSON.parse(localStorage.getItem(GUARDADAS) ?? "{}")); } catch { return []; }
})());
const contados = new Set(); // as leituras já mostradas desde que o painel abriu
function guardarVistos() {
  try { localStorage.setItem(GUARDADAS, JSON.stringify(Object.fromEntries(vistos))); } catch { /* sem onde guardar: na próxima abertura, só não conta */ }
}

// a linha acesa da legenda (pelo nome): continua acesa quando a folha se lê de novo
let acesa = null;
// leva ao instrumento que está na página e, com i, acende o anel daquela leitura (a régua e a rubrica chamam;
// o da página, e não o da montagem: uma leitura descartada no meio não pode prender a tecla a uma cópia)
function irParaLeitura(i) {
  const instrumento = document.querySelector("#tela .lamina svg.instrumento");
  if (!instrumento) return;
  instrumento.scrollIntoView({ behavior: reduzido() ? "auto" : "smooth", block: "center" });
  if (i != null) instrumento.fixar?.(String(i));
}

// tocar, passar o mouse ou dar Enter numa linha da legenda acende o anel dela e apaga os outros
function ligarLegenda(instrumento, linhas, ls) {
  let fixo = acesa == null ? null : (() => { const i = ls.findIndex((l) => l.nome === acesa); return i < 0 ? null : String(i); })();
  const acender = (i) => {
    instrumento.classList.toggle("focado", i != null);
    for (const g of instrumento.querySelectorAll(".anel-g")) g.classList.toggle("acesa", g.dataset.i === i);
    for (const li of linhas) {
      li.classList.toggle("acesa", li.dataset.i === i);
      li.setAttribute("aria-pressed", String(li.dataset.i === fixo));
    }
  };
  const fixar = (i) => {
    fixo = i;
    acesa = i == null ? null : ls[Number(i)].nome;
    acender(fixo);
  };
  for (const li of linhas) {
    li.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") acender(li.dataset.i); });
    li.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") acender(fixo); });
    li.addEventListener("click", () => fixar(fixo === li.dataset.i ? null : li.dataset.i));
    li.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      li.click();
    });
  }
  acender(fixo);
  return fixar;
}

// Prancha I: o instrumento, com a legenda das letras dos dois lados (no celular, embaixo, em duas colunas).
// Os números contam junto com a tinta: ao abrir, da última leitura vista neste aparelho, quando o instrumento
// se grava; depois, do valor de antes, quando a leitura muda
function pranchaServidor(r, ls, regua) {
  const metade = Math.ceil(ls.length / 2);
  const linhas = ls.map((l, i) => h("li", { class: l.tom, "data-i": String(i), "data-chave": `leitura:${l.nome}`, tabindex: "0", role: "button" },
    h("span", { class: "letra-legenda", "aria-hidden": "true" }, l.letra), h("span", { class: "nome" }, l.nome),
    h("span", { class: "leitura" }, l.valor), h("span", { class: "nota-leitura" }, l.nota)));
  // o disco desenha o que a legenda diz: o leitor de tela lê a legenda, e o disco só se anuncia
  const instrumento = desenhavel(prancha(ls, "O instrumento do servidor: um anel por leitura da legenda"), "prancha-servidor");
  instrumento.fixar = ligarLegenda(instrumento, linhas, ls);
  ls.forEach((l, i) => {
    const els = [linhas[i].querySelector(".leitura"), regua?.querySelector(`.v[data-i="${i}"]`)].filter(Boolean);
    const antes = vistos.get(l.nome);
    vistos.set(l.nome, l.n);
    if (antes == null) return;
    if (contados.has(l.nome)) contar(els, l, antes, 0, 1000);
    else instrumento.addEventListener("desenhar", (e) => contar(els, l, antes, 950 + i * 120 - e.detail, 1400), { once: true });
  });
  for (const l of ls) contados.add(l.nome);
  guardarVistos();
  return h("figure", { class: "prancha prancha-servidor n-servidor" },
    h("ul", { class: "prancha-legenda lado-esq" }, linhas.slice(0, metade)), instrumento,
    h("ul", { class: "prancha-legenda lado-dir" }, linhas.slice(metade)),
    h("figcaption", null, h("span", { class: "prancha-numero" }, "Prancha I"), ` · o servidor, com ${r.nucleos} núcleos e ${gb(r.ram_total_mb)}`));
}

// Prancha II: a crepidoma das zonas; os degraus se assentam quando ela aparece na tela
function pranchaZonas(lista) {
  const zonas = resumirZonas(lista);
  marcarZonas(zonas);
  return h("figure", { class: "prancha prancha-zonas n-zonas" }, desenhavel(crepidoma(zonas, abrirZona), "crepidoma-inicio", "visivel"),
    h("figcaption", null, h("span", { class: "prancha-numero" }, "Prancha II"),
      ` · as zonas, com ${lista.filter(containerOk).length} de ${plural(lista.length, "container", "containers")} no ar · `,
      h("a", { href: "#servicos" }, "ver os serviços")));
}

// a régua presa no alto: quando o instrumento sai da tela, ela desce com o que não pode se perder, cada um
// levando ao seu lugar: os pedidos, as zonas e, depois do instrumento em miniatura (que volta a ele), as
// leituras fora do azul, com a letra e o nome curto
function miniatura(ls) {
  return s("svg", { class: "mini", viewBox: "-9 -9 18 18", "aria-hidden": "true" }, s("circle", { class: "aro", r: 8.6 }), ls.map((l, i) => {
    const arco = s("circle", { class: `arco ${l.tom}`, r: 7.4 - i * 1.3, pathLength: 1 });
    arco.style.setProperty("--f", Math.max(0, Math.min(1, l.fracao)).toFixed(4));
    arco.style.setProperty("--i", i);
    return arco;
  }));
}
function reguaFixa(ls, lista, pedidos) {
  const ruins = lista ? lista.filter((c) => !containerOk(c)) : [];
  const fora = ls.filter((l) => l.tom !== "azul");
  const sinal = (classe, acao, rotulo, ...conteudo) => h("button", { type: "button", class: `sinal ${classe}`, "data-chave": `regua:${classe}`, "aria-label": rotulo, onclick: acao }, conteudo);
  const regua = h("nav", { class: "regua-fixa", "aria-label": "O servidor em resumo" },
    pedidos.length > 0 && sinal("pede", () => (pedidos.length === 1 ? abrirPedido(pedidos[0].id) : (location.hash = "#aprovacoes")), null,
      h("i", { class: "led morno" }), plural(pedidos.length, "pedido", "pedidos")),
    lista && sinal("zonas", () => (ruins.length ? abrirZona(ruins[0].zona) : (location.hash = "#servicos")), null,
      h("i", { class: `led ${ruins.length ? "ruim" : "ok"}` }), `${num(lista.length - ruins.length)}/${num(lista.length)} no ar`),
    sinal("leituras", () => irParaLeitura(), fora.length ? "Voltar ao instrumento" : null, miniatura(ls), !fora.length && "Leituras em ordem"),
    fora.map((l) => {
      const i = ls.indexOf(l);
      const tecla = sinal(l.tom, () => irParaLeitura(i), null, h("b", { "aria-hidden": "true" }, l.letra), `${l.curto} `, h("span", { class: "v", "data-i": String(i) }, l.valor));
      tecla.dataset.chave = `regua:${l.nome}`;
      return tecla;
    }));
  // a régua da atualização anterior já estava à vista: a nova entra no lugar dela sem descer de novo, e a
  // posição se confere assim que ela chega à página (a rubrica pode ter crescido ou encolhido)
  if (document.querySelector("#tela .regua-fixa.visivel")) regua.classList.add("visivel", "ja");
  let tentativas = 120;
  const chegou = () => {
    if (regua.isConnected) conferirRegua();
    else if (--tentativas > 0) requestAnimationFrame(chegou);
  };
  requestAnimationFrame(chegou);
  return regua;
}
// a régua desce quando o instrumento passou do alto da tela. Confere a cada rolagem (uma vez por quadro), e
// não só quando ele cruza a borda: um salto de rolagem (a volta à tela, um "Ver") o leva de baixo para cima
// sem ele nunca estar à vista. Olha a régua e o instrumento que estão na página
function conferirRegua() {
  const regua = document.querySelector("#tela .regua-fixa"), instrumento = document.querySelector("#tela .lamina svg.instrumento");
  if (!regua || !instrumento) return;
  const passou = instrumento.getBoundingClientRect().bottom < 64;
  regua.classList.toggle("visivel", passou);
  if (!passou) regua.classList.remove("ja");
}
let quadro = 0;
addEventListener("scroll", () => {
  quadro ||= requestAnimationFrame(() => {
    quadro = 0;
    conferirRegua();
  });
}, { passive: true });

const juntar = (...frases) => frases.filter(Boolean).join(" ");

// a frase do dia, em duas no máximo: o veredito (o que está errado, ou "Tudo em ordem", que só se diz quando
// tudo foi lido) e o que espera você; na calma, sem nada esperando, o próximo agendamento
function fraseDoDia({ total, ruins, falhas, alertas, naoLidos, fora, pedidos, abertas, proximo }) {
  const esperando = [pedidos && plural(pedidos, "aprovação", "aprovações"), abertas && plural(abertas, "pendência", "pendências")].filter(Boolean);
  const espera = esperando.length > 0 && `${esperando.join(" e ")} ${pedidos + abertas === 1 ? "espera" : "esperam"} você.`;
  if (fora) return juntar("Não consegui ler o servidor agora.", espera);
  const males = [
    ...ruins.map((c) => (c.estado === "running" ? `o ${c.container} falha na verificação de saúde` : `o ${c.container} está fora do ar`)),
    ...falhas.map((u) => `a unidade ${u} falhou`),
    ...alertas.map((l) => `${l.frase} passou do limite`),
    ...naoLidos.map((n) => `não consegui ler ${n.oque}`),
  ];
  if (!males.length) return juntar(`Tudo em ordem: ${plural(total, "container", "containers")} no ar.`,
    espera || (proximo && `O próximo agendamento é ${proximo.nome}, ${quandoTexto(proximo.proxima)}.`));
  // com três ou mais, o primeiro e a conta do resto: os detalhes estão logo abaixo, na rubrica
  const veredito = males.length <= 2 ? males.join(" e ") : `${males[0]} e mais ${num(males.length - 1)} coisas pedem atenção`;
  return juntar(`${veredito[0].toUpperCase()}${veredito.slice(1)}.`, espera);
}

// a rubrica: o que pede você, na cabeça da folha, logo abaixo da frase (só quando há algo), com o título na
// tinta do mais grave: o que não deu para ler, o que caiu, o que falhou, a leitura que passou do limite e, por
// fim, os pedidos, cada um com o motivo e o "Ver" que abre ele mesmo
function rubrica(dados) {
  const tentar = () => h("button", { type: "button", class: "discreto", onclick: () => atualizar() }, "Tentar de novo");
  const linhas = [
    dados.fora ? item({ led: "ruim", nome: "Não consegui ler o servidor", detalhe: dados.fora, acoes: tentar(), chave: "fora" })
      : dados.naoLidos.map((n) => item({ led: "ruim", nome: `Não consegui ler ${n.oque}`, detalhe: n.erro, acoes: tentar(), chave: `nao-lido:${n.oque}` })),
    dados.ruins.map((c) => item({ led: "ruim", nome: c.container, detalhe: statusDocker(c.status), rachado: c.container, chave: `caiu:${c.container}`,
      acoes: h("button", { type: "button", class: "discreto", onclick: () => abrirZona(c.zona) }, "Ver") })),
    dados.falhas.map((u) => item({ led: "ruim", nome: u, detalhe: "unidade do systemd que falhou", rachado: u, chave: `falhou:${u}` })),
    dados.alertas.map((l) => item({ led: "ruim", nome: l.nome, detalhe: `${l.valor} · passou do limite de ${l.limite}`, chave: `limite:${l.nome}`,
      acoes: h("button", { type: "button", class: "discreto", onclick: () => irParaLeitura(dados.ls.indexOf(l)) }, "Ver") })),
    dados.listaPedidos.map((p) => item({ led: "morno", nome: p.titulo ?? p.acao, detalhe: `${quem(p.cliente)} · vence ${relativo(p.expira)}`, chave: `pedido:${p.id}`,
      extra: (p.texto ?? p.pergunta) && h("p", { class: "motivo" }, p.texto ?? p.pergunta),
      acoes: h("button", { type: "button", class: "discreto", onclick: () => abrirPedido(p.id) }, "Ver") })),
  ].flat();
  if (!linhas.length) return null;
  const grave = linhas.length > dados.listaPedidos.length;
  return h("section", { class: `rubrica ${grave ? "grave" : "espera"}`, "aria-labelledby": "rubrica-titulo" },
    h("h2", { class: "rubrica-titulo", id: "rubrica-titulo" }, "O que pede você"), itens(linhas));
}

// a cabeça da folha: a data, a frase e a rubrica
function topo(dados) {
  const hoje = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
  return h("header", { class: "lamina-topo" }, h("p", { class: "dia-data" }, hoje[0].toUpperCase() + hoje.slice(1)),
    h("p", { class: `dia-frase${dados.fora ? " erro" : ""}` }, fraseDoDia(dados)), rubrica(dados));
}

// o fim da folha: quando ela foi lida (a tela se lê de novo sozinha a cada 30 s)
function colofao(fora) {
  const agora = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return h("footer", { class: "colofao" }, fora
    ? `Tentei ler o servidor às ${agora}; tento de novo a cada 30\u00a0s.`
    : `Lido do servidor às ${agora} · uma leitura nova a cada 30\u00a0s, com o painel aberto.`);
}

// "**negrito**" e "`código`" do README, sem innerHTML
function marcado(texto) {
  return texto.split(/(\*\*[^*]+\*\*|`[^`]+`)/).filter(Boolean).map((s) =>
    s.startsWith("**") ? h("strong", null, s.slice(2, -2)) : s.startsWith("`") ? h("code", null, s.slice(1, -1)) : s);
}

// r: as pendências já lidas pela tela (marcar, apagar ou acrescentar refaz o cartão lendo de novo)
async function cartaoPendencias(r) {
  r ??= await api("GET", "/api/pendencias");
  if (r.ok === false) return nota(cartao("Pendências", falha(r)), "pendencias");
  const refazer = async () => c.replaceWith(await cartaoPendencias());
  const pendencia = (p) => item({
    nome: h("label", { class: "opcao" }, h("input", { type: "checkbox", checked: Boolean(p.feita), onchange: async (evento) => {
      const x = await api("POST", "/api/pendencias/marcar", { id: p.id, feita: evento.currentTarget.checked });
      if (x.ok === false) avisar(x.erro, "erro");
      refazer();
    } }), h("span", null, marcado(p.texto))),
    acoes: p.origem === "manual" && h("button", { type: "button", class: "discreto perigo", onclick: async () => {
      if (!confirm("Apagar esta pendência?")) return;
      await api("POST", "/api/pendencias/apagar", { id: p.id });
      refazer();
    } }, "Apagar"),
  });
  const abertas = r.pendencias.filter((p) => !p.feita);
  const feitas = r.pendencias.filter((p) => p.feita);
  const campo = h("input", { name: "texto", maxlength: "300", placeholder: "Nova pendência", autocomplete: "off", "aria-label": "Nova pendência" });
  const c = nota(cartao(`Pendências (${abertas.length})`,
    itens(abertas.map(pendencia), "Nenhuma pendência aberta."),
    h("form", { class: "nova", onsubmit: async (evento) => {
      evento.preventDefault();
      if (!campo.value.trim()) return;
      const x = await api("POST", "/api/pendencias/nova", { texto: campo.value });
      if (x.ok === false) return avisar(x.erro, "erro");
      refazer();
    } }, campo, h("button", { type: "submit", class: "discreto" }, "Adicionar")),
    feitas.length > 0 && h("details", null, h("summary", null, `Resolvidas (${feitas.length})`), itens(feitas.map(pendencia))),
    h("p", { class: "fraco" }, r.readme
      ? `As da seção "Pendências conhecidas" de ${r.readme} entram sozinhas e ficam resolvidas quando saem de lá.`
      : "Este servidor não tem README com pendências: as daqui são as que você escrever.")), "pendencias");
  return c;
}

// os três próximos das duas agendas, a do painel e a da Atena
function cartaoProximos(r, atena) {
  if (r.ok === false && !atena.length) return null;
  const proximos = proximosDeTodos(r, atena).slice(0, 3);
  return cartao("Próximos agendamentos",
    itens(proximos.map((a) => item({ led: "info", nome: a.nome,
      detalhe: `${quandoTexto(a.proxima)}${a.de === "atena" ? " · a Atena" : ""}` })), "Nada agendado."),
    h("p", null, h("a", { href: "#agenda", class: "ir" }, "Ver a agenda")));
}

// o gasto do mês numa linha, na medida das leituras, com um medidor só (o de todos os tetos); o de cada
// modelo fica recolhido
function notaGasto(g) {
  const mes = new Date(`${g.mes}-15T12:00:00`).toLocaleDateString("pt-BR", { month: "long" });
  const comTeto = g.por_modelo.filter((m) => m.teto_usd);
  const teto = comTeto.reduce((t, m) => t + m.teto_usd, 0);
  const modelos = g.por_modelo.filter((m) => m.gasto_usd > 0 || m.teto_usd);
  return modulo("Gasto de IA", mes === "Invalid Date" ? g.mes : mes,
    h("p", { class: "gasto-total" }, h("strong", null, dinheiro(g.total_usd)), teto ? ` de ${dinheiro(teto)} no mês` : " no mês"),
    teto > 0 && medidor(g.total_usd / teto),
    h("details", null, h("summary", null, `Por modelo (${modelos.length})`),
      modelos.map((m) => [
        linha(m.modelo, [`${dinheiro(m.gasto_usd)}${m.teto_usd ? ` de ${dinheiro(m.teto_usd)}` : ""}`, h("small", null, ` · ${plural(m.chamadas, "chamada", "chamadas")}`)]),
        m.teto_usd ? medidor(m.gasto_usd / m.teto_usd) : null,
      ]),
      h("p", { class: "fraco" }, g.obs)));
}

export async function telaInicio() {
  const [recursos, servicos, gasto, sistema, aprovacoes, pendencias, agenda, agendaAtena] = await Promise.all([
    consultar("status.recursos"), consultar("status.servicos"), consultar("gasto.api"), consultar("status.sistema"),
    consultar("aprovacoes.lista"), api("GET", "/api/pendencias"), api("GET", "/api/agendamentos"), consultar("atena.agenda"),
  ]);
  const atena = daAtena(agendaAtena);
  // o que não deu para ler não vira "nada": sem nenhuma das quatro, o servidor não respondeu; sem uma ou
  // outra, a frase diz qual. Sem a central de aprovações (403 ou 404: o executor antigo ou o token sem a
  // ação), não há o que ler, e isso não é falha
  const semAprovacoes = aprovacoes.status === 403 || aprovacoes.status === 404;
  const lidas = [[recursos, "as leituras do servidor"], [servicos, "os serviços"], [sistema, "o systemd"],
    ...(semAprovacoes ? [] : [[aprovacoes, "as aprovações"]])];
  const naoLidos = lidas.filter(([r]) => r.ok === false).map(([r, oque]) => ({ oque, erro: r.erro }));
  const fora = naoLidos.length === lidas.length ? naoLidos[0].erro ?? "o executor não respondeu" : null;
  // com o servidor fora, a rubrica diz o erro uma vez só, e as notas só dizem que não há leitura
  const semLeitura = (r) => (fora ? h("p", { class: "fraco" }, "Sem leitura agora.") : falha(r));

  const lista = servicos.ok === false ? [] : servicos.resultado;
  const falhas = sistema.ok === false ? [] : sistema.resultado.falhas;
  const listaPedidos = aprovacoes.ok === false ? [] : aprovacoes.resultado.pendentes;
  const proximo = proximosDeTodos(agenda, atena)[0] ?? null;
  const r = recursos.ok === false ? null : recursos.resultado;
  const ls = r ? leituras(r) : [];
  const dados = {
    total: lista.length, ruins: lista.filter((c) => !containerOk(c)), falhas, ls, alertas: ls.filter((l) => l.tom === "cinabrio"),
    naoLidos: fora ? [] : naoLidos, fora, listaPedidos, pedidos: listaPedidos.length,
    abertas: pendencias.ok === false ? 0 : pendencias.pendencias.filter((p) => !p.feita).length, proximo,
  };

  // o systemd: as falhas sobem para o que pede você; aqui ficam a conta e os timers
  let notaSistema;
  if (sistema.ok === false) notaSistema = cartao("Sistema", semLeitura(sistema));
  else {
    const s = sistema.resultado;
    notaSistema = modulo("Sistema", s.falhas.length ? `${s.falhas.length} com falha` : null,
      h("p", { class: "fraco" }, s.falhas.length ? `${plural(s.falhas.length, "unidade falhou", "unidades falharam")}: estão no que pede você.`
        : "Nenhuma unidade do systemd com falha."),
      h("details", null, h("summary", null, `Timers (${s.timers.length})`),
        itens(s.timers.map((t) => item({ nome: t.nome, detalhe: `próxima: ${t.proxima ?? "—"}` })))));
  }

  const regua = r ? reguaFixa(ls, servicos.ok === false ? null : lista, listaPedidos) : null;
  const servidor = r ? pranchaServidor(r, ls, regua) : nota(cartao("Servidor", semLeitura(recursos)), "servidor");
  // no celular, uma coluna na ordem do código: o servidor, as zonas, a agenda, as pendências, o gasto, o
  // systemd; na lâmina larga, a grade põe cada parte no seu lugar
  return [h("section", { class: "lamina largo" }, regua, topo(dados),
    h("div", { class: "lamina-corpo" },
      h("div", { class: "centro" }, servidor,
        servicos.ok === false ? nota(cartao("Zonas", semLeitura(servicos)), "zonas") : pranchaZonas(lista)),
      h("div", { class: "margem esquerda" }, nota(cartaoProximos(agenda, atena), "agenda"), await cartaoPendencias(pendencias)),
      h("div", { class: "margem direita" },
        nota(gasto.ok === false ? cartao("Gasto de IA", semLeitura(gasto)) : notaGasto(gasto.resultado), "gasto"), nota(notaSistema, "sistema"))),
    colofao(fora))];
}
