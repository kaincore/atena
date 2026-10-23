// Início: uma lâmina só, planejada como uma prancha impressa. No alto, a data e a frase do dia escrita a partir
// dos dados; no meio, as duas pranchas (o instrumento do servidor, com a legenda das letras, e a crepidoma das
// zonas); nas margens, as notas: o que pede você e as pendências de um lado, os próximos agendamentos, o gasto
// e o systemd do outro. Rolando para baixo, as leituras não se perdem: uma régua presa no alto da tela as
// mantém à vista.
import { api, avisar, cartao, consultar, containerOk, dinheiro, falha, gb, h, item, itens, linha, medidor, modulo,
  num, numeroGrande, plural, statusDocker } from "../comum.js";
import { quandoTexto } from "./agenda.js";
import { relativo } from "./aprovacoes.js";
import { abrirZona, marcarZonas, resumirZonas } from "../zonas.js";
import { crepidoma, prancha, s, tom } from "../desenhos.js";
import { desenhavel } from "../ornamentos.js";

const GREGAS = ["Α", "Β", "Γ", "Δ", "Ε", "Ζ"];

// as leituras do instrumento, de fora para dentro: a CPU, a RAM, a temperatura, a GPU e cada disco, com o
// limite de cada uma (a tinta passa a ocre perto dele e a cinábrio passado dele, como nos medalhões). n e fmt
// deixam o número andar de um valor ao outro
function leituras(r) {
  const carga = r.carga[0] / r.nucleos;
  const usada = (r.ram_total_mb - r.ram_disponivel_mb) / 1024, total = r.ram_total_mb / 1024;
  const cpu = r.temperaturas.cpu_c;
  const leitura = (nome, n, casas, unidade, nota, fracao, alerta) => ({ nome, n, fmt: (x) => `${num(x, casas)}${unidade}`, nota, fracao, alerta });
  return [
    leitura("CPU", Math.min(99.9, carga * 100), carga < 0.1 ? 1 : 0, "%", `carga ${num(r.carga[0], 2)} em ${r.nucleos} núcleos`, carga, 1),
    leitura("RAM", usada, 1, "\u00a0GB", `de ${num(total, 1)}\u00a0GB`, usada / total, 0.95),
    cpu != null && leitura("Temperatura", cpu, 1, "\u00a0°C", "da CPU", cpu / 85, 1),
    r.gpu && leitura("GPU", r.gpu.temperatura_c, 0, "\u00a0°C",
      `uso ${num(r.gpu.uso_pct)}% · VRAM ${num(r.gpu.vram_usada_mb / 1024, 1)} de ${num(r.gpu.vram_total_mb / 1024, 1)}\u00a0GB`, r.gpu.temperatura_c / 85, 1),
    ...Object.entries(r.discos).map(([ponto, d]) => leitura(`Disco ${ponto}`, 100 * (1 - d.livre_gb / d.total_gb), 0, "%",
      `${num(d.livre_gb, 1)}\u00a0GB livres de ${num(d.total_gb, 1)}\u00a0GB`, 1 - d.livre_gb / d.total_gb, 0.9)),
  ].filter(Boolean).slice(0, GREGAS.length)
    .map((l, i) => ({ ...l, valor: l.fmt(l.n), letra: GREGAS[i], tom: tom(Math.min(1, l.fracao) / l.alerta) }));
}

// as notas da margem: o módulo sem a placa, só o título com a régua e o conteúdo (n-…: a ordem no celular)
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
const vistos = new Map(); // a última leitura mostrada de cada coisa

// tocar (ou passar o mouse) numa linha da legenda acende o anel dela e apaga os outros
function ligarLegenda(instrumento, linhas) {
  let fixo = null;
  const acender = (i) => {
    instrumento.classList.toggle("focado", i != null);
    for (const g of instrumento.querySelectorAll(".anel-g")) g.classList.toggle("acesa", g.dataset.i === i);
    for (const li of linhas) li.classList.toggle("acesa", li.dataset.i === i);
  };
  for (const li of linhas) {
    li.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") acender(li.dataset.i); });
    li.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") acender(fixo); });
    li.addEventListener("click", () => {
      fixo = fixo === li.dataset.i ? null : li.dataset.i;
      acender(fixo);
    });
  }
}

// Prancha I: o instrumento, com a legenda das letras dos dois lados (no celular, embaixo, em duas colunas).
// Os números contam junto com a tinta: na primeira vez, do zero, quando o instrumento se grava; depois, do
// valor de antes, quando a leitura muda
function pranchaServidor(r, ls, regua) {
  const metade = Math.ceil(ls.length / 2);
  const linhas = ls.map((l, i) => h("li", { class: l.tom, "data-i": String(i) },
    h("span", { class: "letra-legenda", "aria-hidden": "true" }, l.letra), h("span", { class: "nome" }, l.nome),
    h("span", { class: "leitura" }, l.valor), h("span", { class: "nota-leitura" }, l.nota)));
  const instrumento = desenhavel(prancha(ls, `O servidor: ${ls.map((l) => `${l.nome}, ${l.valor}`).join("; ")}`), "prancha-servidor");
  ligarLegenda(instrumento, linhas);
  const primeira = ls.some((l) => !vistos.has(l.nome));
  ls.forEach((l, i) => {
    const els = [linhas[i].querySelector(".leitura"), regua?.querySelector(`[data-i="${i}"] .v`)].filter(Boolean);
    const antes = vistos.get(l.nome);
    vistos.set(l.nome, l.n);
    if (antes != null && !primeira) contar(els, l, antes, 0, 1000);
    else instrumento.addEventListener("desenhar", (e) => contar(els, l, 0, 950 + i * 120 - e.detail, 1400), { once: true });
  });
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

// a régua presa no alto: quando o instrumento sai da tela, ela desce com as leituras (um anel pequeno por
// letra), as zonas e os pedidos; tocar nela volta ao instrumento
function anelPequeno(f) {
  const arco = s("circle", { class: "arco", r: 7, pathLength: 1 });
  arco.style.setProperty("--f", Math.max(0, Math.min(1, f)).toFixed(4));
  return s("svg", { class: "mini", viewBox: "-9 -9 18 18", "aria-hidden": "true" }, s("circle", { class: "fundo", r: 7 }), arco);
}
function reguaFixa(ls, lista, pedidos) {
  const ruins = lista ? lista.filter((c) => !containerOk(c)).length : 0;
  const regua = h("button", { type: "button", class: "regua-fixa", "aria-label": "Voltar às leituras do servidor" },
    ls.map((l, i) => {
      const sinal = h("span", { class: `sinal ${l.tom}`, "data-i": String(i) }, anelPequeno(l.fracao), h("b", null, l.letra), h("span", { class: "v" }, l.valor));
      sinal.style.setProperty("--i", i);
      return sinal;
    }),
    lista && h("span", { class: "sinal zonas" }, h("i", { class: `led ${ruins ? "ruim" : "ok"}` }), `${num(lista.length - ruins)}/${num(lista.length)} no ar`),
    pedidos > 0 && h("span", { class: "sinal pede" }, h("i", { class: "led morno" }), plural(pedidos, "pedido", "pedidos")));
  // a régua da atualização anterior já estava à vista: a nova entra no lugar dela, sem descer de novo
  if (document.querySelector(".regua-fixa.visivel")) regua.classList.add("visivel", "ja");
  return regua;
}
let vigia = null;
function vigiar(alvo, regua) {
  vigia?.disconnect();
  vigia = new IntersectionObserver(([e]) => {
    const passou = !e.isIntersecting && e.boundingClientRect.bottom < 80;
    regua.classList.toggle("visivel", passou);
    if (!passou) regua.classList.remove("ja");
  }, { rootMargin: "-64px 0px 0px 0px" });
  vigia.observe(alvo);
  regua.addEventListener("click", () => alvo.scrollIntoView({ behavior: reduzido() ? "auto" : "smooth", block: "center" }));
}

// a frase do dia: primeiro o que está errado (o que caiu, o que falhou, a leitura que passou do limite),
// depois o que espera você, por fim o próximo agendamento
function fraseDoDia({ total, ruins, falhas, alertas, pedidos, abertas, proximo }) {
  const partes = [];
  if (!ruins.length && !falhas.length && !alertas.length) partes.push(`Tudo em ordem: ${plural(total, "container", "containers")} no ar.`);
  if (ruins.length === 1) partes.push(`O container ${ruins[0].container} está fora do ar.`);
  else if (ruins.length) partes.push(`${ruins.length} containers estão fora do ar.`);
  if (falhas.length === 1) partes.push(`A unidade ${falhas[0]} falhou.`);
  else if (falhas.length) partes.push(`${falhas.length} unidades do systemd falharam.`);
  for (const l of alertas) partes.push(`${l.nome} passou do limite: ${l.valor}.`);
  const esperando = [pedidos && plural(pedidos, "aprovação", "aprovações"), abertas && plural(abertas, "pendência", "pendências")].filter(Boolean);
  if (esperando.length) partes.push(`${esperando.join(" e ")} ${pedidos + abertas === 1 ? "espera" : "esperam"} você.`);
  if (proximo) partes.push(`O próximo agendamento é ${proximo.nome}, ${quandoTexto(proximo.proxima)}.`);
  return partes.join(" ");
}

// o alto da folha: a data e a frase
function topo(dados) {
  const hoje = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
  return h("header", { class: "lamina-topo" }, h("p", { class: "dia-data" }, hoje[0].toUpperCase() + hoje.slice(1)),
    h("p", { class: "dia-frase" }, fraseDoDia(dados)));
}

// o que pede você: os pedidos, o que caiu e o que falhou (só aparece quando há algo)
function notaPede(dados) {
  const pede = [
    dados.listaPedidos.map((p) => item({ led: "morno", nome: p.titulo ?? p.acao, detalhe: `${p.cliente} · vence ${relativo(p.expira)}`,
      acoes: h("button", { type: "button", class: "discreto", onclick: () => { location.hash = "#aprovacoes"; } }, "Ver") })),
    dados.ruins.map((c) => item({ led: "ruim", nome: c.container, detalhe: statusDocker(c.status), rachado: c.container,
      acoes: h("button", { type: "button", class: "discreto", onclick: () => abrirZona(c.zona) }, "Ver") })),
    dados.falhas.map((u) => item({ led: "ruim", nome: u, detalhe: "unidade do systemd que falhou", rachado: u })),
  ].flat();
  return pede.length ? nota(modulo("O que pede você", null, itens(pede)), "pede") : null;
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

function cartaoProximos(r) {
  if (r.ok === false) return null;
  const proximos = r.agendamentos.filter((a) => a.ativo && a.proxima).slice(0, 3);
  return cartao("Próximos agendamentos",
    itens(proximos.map((a) => item({ led: "info", nome: a.nome, detalhe: quandoTexto(a.proxima) })), "Nada agendado."),
    h("p", null, h("a", { href: "#agenda" }, "Ver a agenda")));
}

export async function telaInicio() {
  const [recursos, servicos, gasto, sistema, aprovacoes, pendencias, agenda] = await Promise.all([
    consultar("status.recursos"), consultar("status.servicos"), consultar("gasto.api"), consultar("status.sistema"),
    consultar("aprovacoes.lista"), api("GET", "/api/pendencias"), api("GET", "/api/agendamentos"),
  ]);
  const lista = servicos.ok === false ? [] : servicos.resultado;
  const falhas = sistema.ok === false ? [] : sistema.resultado.falhas;
  const listaPedidos = aprovacoes.ok === false ? [] : aprovacoes.resultado.pendentes;
  const proximo = agenda.ok === false ? null : agenda.agendamentos.filter((a) => a.ativo && a.proxima).sort((a, b) => a.proxima - b.proxima)[0];
  const alertas = recursos.ok === false ? [] : leituras(recursos.resultado).filter((l) => l.tom === "cinabrio");
  const dados = {
    total: lista.length, ruins: lista.filter((c) => !containerOk(c)), falhas, alertas, listaPedidos, pedidos: listaPedidos.length,
    abertas: pendencias.ok === false ? 0 : pendencias.pendencias.filter((p) => !p.feita).length, proximo,
  };

  let notaGasto;
  if (gasto.ok === false) notaGasto = cartao("Gasto de IA", falha(gasto));
  else {
    const g = gasto.resultado;
    notaGasto = modulo("Gasto de IA", g.mes,
      numeroGrande(dinheiro(g.total_usd), "no mês"),
      g.por_modelo.filter((m) => m.gasto_usd > 0 || m.teto_usd).map((m) => [
        linha(m.modelo, [`${dinheiro(m.gasto_usd)}${m.teto_usd ? ` de ${dinheiro(m.teto_usd)}` : ""}`, h("small", null, ` · ${plural(m.chamadas, "chamada", "chamadas")}`)]),
        m.teto_usd ? medidor(m.gasto_usd / m.teto_usd) : null,
      ]),
      h("p", { class: "fraco" }, g.obs));
  }

  // o systemd: as falhas sobem para o que pede você; aqui ficam a conta e os timers
  let notaSistema;
  if (sistema.ok === false) notaSistema = cartao("Sistema", falha(sistema));
  else {
    const s = sistema.resultado;
    notaSistema = modulo("Sistema", s.falhas.length ? `${s.falhas.length} com falha` : `${s.timers.length} timers`,
      h("p", { class: "fraco" }, s.falhas.length ? `${plural(s.falhas.length, "unidade falhou", "unidades falharam")}: estão no que pede você.`
        : "Nenhuma unidade do systemd com falha."),
      h("details", null, h("summary", null, `Timers (${s.timers.length})`),
        itens(s.timers.map((t) => item({ nome: t.nome, detalhe: `próxima: ${t.proxima ?? "—"}` })))));
  }

  const r = recursos.ok === false ? null : recursos.resultado;
  const ls = r ? leituras(r) : [];
  const regua = r ? reguaFixa(ls, servicos.ok === false ? null : lista, listaPedidos.length) : null;
  const servidor = r ? pranchaServidor(r, ls, regua) : nota(cartao("Servidor", falha(recursos)), "servidor");
  if (regua) vigiar(servidor, regua);
  return [h("section", { class: "lamina largo" }, regua, topo(dados),
    h("div", { class: "lamina-corpo" },
      h("div", { class: "margem esquerda" }, notaPede(dados), await cartaoPendencias(pendencias)),
      h("div", { class: "centro" }, servidor,
        servicos.ok === false ? nota(cartao("Zonas", falha(servicos)), "zonas") : pranchaZonas(lista)),
      h("div", { class: "margem direita" }, nota(cartaoProximos(agenda), "agenda"), nota(notaGasto, "gasto"), nota(notaSistema, "sistema"))))];
}
