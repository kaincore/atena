// Início: a frase do dia escrita a partir dos dados, o que pede você, as duas pranchas (o instrumento do
// servidor e a crepidoma das zonas) e, embaixo, os próximos agendamentos, o gasto, o systemd e as pendências.
import { api, avisar, cartao, consultar, containerOk, dinheiro, falha, gb, h, item, itens, linha, medidor, modulo,
  num, numeroGrande, plural, statusDocker } from "../comum.js";
import { quandoTexto } from "./agenda.js";
import { relativo } from "./aprovacoes.js";
import { abrirZona, marcarZonas, resumirZonas } from "../zonas.js";
import { crepidoma, prancha, tom } from "../desenhos.js";
import { desenhavel } from "../ornamentos.js";

const GREGAS = ["Α", "Β", "Γ", "Δ", "Ε", "Ζ"];

// as leituras do instrumento, de fora para dentro: a CPU, a RAM, a temperatura, a GPU e cada disco, com o
// limite de cada uma (a tinta passa a ocre perto dele e a cinábrio passado dele, como nos medalhões)
function leituras(r) {
  const carga = r.carga[0] / r.nucleos;
  const usada = (r.ram_total_mb - r.ram_disponivel_mb) / 1024, total = r.ram_total_mb / 1024;
  const cpu = r.temperaturas.cpu_c;
  return [
    { nome: "CPU", valor: `${num(Math.min(99.9, carga * 100), carga < 0.1 ? 1 : 0)}%`, nota: `carga ${num(r.carga[0], 2)} em ${r.nucleos} núcleos`, fracao: carga, alerta: 1 },
    { nome: "RAM", valor: `${num(usada, 1)}\u00a0GB`, nota: `de ${num(total, 1)}\u00a0GB`, fracao: usada / total, alerta: 0.95 },
    cpu != null && { nome: "Temperatura", valor: `${num(cpu, 1)}\u00a0°C`, nota: "da CPU", fracao: cpu / 85, alerta: 1 },
    r.gpu && { nome: "GPU", valor: `${num(r.gpu.temperatura_c)}\u00a0°C`, fracao: r.gpu.temperatura_c / 85, alerta: 1,
      nota: `uso ${num(r.gpu.uso_pct)}% · VRAM ${num(r.gpu.vram_usada_mb / 1024, 1)} de ${num(r.gpu.vram_total_mb / 1024, 1)}\u00a0GB` },
    ...Object.entries(r.discos).map(([ponto, d]) => ({ nome: `Disco ${ponto}`, valor: `${num(100 * (1 - d.livre_gb / d.total_gb))}%`,
      nota: `${num(d.livre_gb, 1)}\u00a0GB livres de ${num(d.total_gb, 1)}\u00a0GB`, fracao: 1 - d.livre_gb / d.total_gb, alerta: 0.9 })),
  ].filter(Boolean).slice(0, GREGAS.length)
    .map((l, i) => ({ ...l, letra: GREGAS[i], tom: tom(Math.min(1, l.fracao) / l.alerta) }));
}

// Prancha I: o instrumento e a legenda das letras dele
function pranchaServidor(r) {
  const lista = leituras(r);
  const instrumento = prancha(lista, `O servidor: ${lista.map((l) => `${l.nome}, ${l.valor}`).join("; ")}`);
  return h("figure", { class: "prancha servidor" }, desenhavel(instrumento, "prancha-servidor"),
    h("ul", { class: "prancha-legenda" }, lista.map((l) => h("li", { class: l.tom },
      h("span", { class: "letra-legenda", "aria-hidden": "true" }, l.letra), h("span", { class: "nome" }, l.nome),
      h("span", { class: "leitura" }, l.valor), h("span", { class: "nota" }, l.nota)))),
    h("figcaption", null, h("span", { class: "prancha-numero" }, "Prancha I"), ` · o servidor, com ${r.nucleos} núcleos e ${gb(r.ram_total_mb)}`));
}

// Prancha II: a crepidoma das zonas
function pranchaZonas(lista) {
  const zonas = resumirZonas(lista);
  marcarZonas(zonas);
  const noAr = lista.filter(containerOk).length;
  return h("figure", { class: "prancha zonas" }, crepidoma(zonas, abrirZona),
    h("figcaption", null, h("span", { class: "prancha-numero" }, "Prancha II"), ` · as zonas, com ${noAr} de ${plural(lista.length, "container", "containers")} no ar · `,
      h("a", { href: "#servicos" }, "ver os serviços")));
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

// o alto da página: a data, a frase e, se houver, o que pede você (os pedidos, o que caiu e o que falhou)
function dia(dados) {
  const hoje = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
  const pede = [
    dados.listaPedidos.map((p) => item({ led: "morno", nome: p.titulo ?? p.acao, detalhe: `${p.cliente} · vence ${relativo(p.expira)}`,
      acoes: h("button", { type: "button", class: "discreto", onclick: () => { location.hash = "#aprovacoes"; } }, "Ver") })),
    dados.ruins.map((c) => item({ led: "ruim", nome: c.container, detalhe: statusDocker(c.status), rachado: c.container,
      acoes: h("button", { type: "button", class: "discreto", onclick: () => abrirZona(c.zona) }, "Ver") })),
    dados.falhas.map((u) => item({ led: "ruim", nome: u, detalhe: "unidade do systemd que falhou", rachado: u })),
  ].flat();
  return h("section", { class: "dia largo" },
    h("div", { class: "dia-texto" }, h("p", { class: "dia-data" }, hoje[0].toUpperCase() + hoje.slice(1)),
      h("p", { class: "dia-frase" }, fraseDoDia(dados))),
    pede.length > 0 && modulo("O que pede você", null, itens(pede)));
}

// "**negrito**" e "`código`" do README, sem innerHTML
function marcado(texto) {
  return texto.split(/(\*\*[^*]+\*\*|`[^`]+`)/).filter(Boolean).map((s) =>
    s.startsWith("**") ? h("strong", null, s.slice(2, -2)) : s.startsWith("`") ? h("code", null, s.slice(1, -1)) : s);
}

// r: as pendências já lidas pela tela (marcar, apagar ou acrescentar refaz o cartão lendo de novo)
async function cartaoPendencias(r) {
  r ??= await api("GET", "/api/pendencias");
  if (r.ok === false) return cartao("Pendências", falha(r));
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
  const c = cartao(`Pendências (${abertas.length})`,
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
      : "Este servidor não tem README com pendências: as daqui são as que você escrever."));
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
  const telas = [dia({
    total: lista.length, ruins: lista.filter((c) => !containerOk(c)), falhas, alertas, listaPedidos, pedidos: listaPedidos.length,
    abertas: pendencias.ok === false ? 0 : pendencias.pendencias.filter((p) => !p.feita).length, proximo,
  })];

  telas.push(h("div", { class: "pranchas largo" },
    recursos.ok === false ? cartao("Servidor", falha(recursos)) : pranchaServidor(recursos.resultado),
    servicos.ok === false ? cartao("Zonas", falha(servicos)) : pranchaZonas(lista)));

  telas.push(cartaoProximos(agenda));

  if (gasto.ok === false) telas.push(cartao("Gasto de IA", falha(gasto)));
  else {
    const g = gasto.resultado;
    telas.push(modulo("Gasto de IA", g.mes,
      numeroGrande(dinheiro(g.total_usd), "no mês"),
      g.por_modelo.filter((m) => m.gasto_usd > 0 || m.teto_usd).map((m) => [
        linha(m.modelo, [`${dinheiro(m.gasto_usd)}${m.teto_usd ? ` de ${dinheiro(m.teto_usd)}` : ""}`, h("small", null, ` · ${plural(m.chamadas, "chamada", "chamadas")}`)]),
        m.teto_usd ? medidor(m.gasto_usd / m.teto_usd) : null,
      ]),
      h("p", { class: "fraco" }, g.obs),
    ));
  }

  // o systemd: as falhas sobem para o alto (o que pede você); aqui ficam a conta e os timers
  if (sistema.ok === false) telas.push(cartao("Sistema", falha(sistema)));
  else {
    const s = sistema.resultado;
    telas.push(modulo("Sistema", s.falhas.length ? `${s.falhas.length} com falha` : `${s.timers.length} timers`,
      h("p", { class: "fraco" }, s.falhas.length ? `${plural(s.falhas.length, "unidade falhou", "unidades falharam")}: estão no alto da página.`
        : "Nenhuma unidade do systemd com falha."),
      h("details", null, h("summary", null, `Timers (${s.timers.length})`),
        itens(s.timers.map((t) => item({ nome: t.nome, detalhe: `próxima: ${t.proxima ?? "—"}` })))),
    ));
  }
  telas.push(await cartaoPendencias(pendencias));
  return telas;
}
