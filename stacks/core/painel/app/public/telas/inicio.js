// Início: o servidor no visor, as zonas, o gasto, os próximos agendamentos e as pendências.
import { api, avisar, cartao, consultar, containerOk, dinheiro, estadoContainer, falha, gb, h, linha, medidor, modulo,
  mostrador, statusDocker } from "../comum.js";
import { quandoTexto } from "./agenda.js";
import { abrirZona, marcarZonas, resumirZonas } from "../zonas.js";
import { visorInicio, vistaExplodida } from "../visor.js";

// "**negrito**" e "`código`" do README, sem innerHTML
function marcado(texto) {
  return texto.split(/(\*\*[^*]+\*\*|`[^`]+`)/).filter(Boolean).map((s) =>
    s.startsWith("**") ? h("strong", null, s.slice(2, -2)) : s.startsWith("`") ? h("code", null, s.slice(1, -1)) : s);
}

async function cartaoPendencias() {
  const r = await api("GET", "/api/pendencias");
  if (r.ok === false) return cartao("Pendências", falha(r));
  const refazer = async () => c.replaceWith(await cartaoPendencias());
  const item = (p) => h("li", null,
    h("div", { class: "stack-topo" },
      h("label", { class: "opcao" }, h("input", { type: "checkbox", checked: Boolean(p.feita), onchange: async (evento) => {
        const x = await api("POST", "/api/pendencias/marcar", { id: p.id, feita: evento.currentTarget.checked });
        if (x.ok === false) avisar(x.erro, "erro");
        refazer();
      } }), h("span", null, marcado(p.texto))),
      p.origem === "manual" && h("button", { type: "button", class: "discreto", onclick: async () => {
        if (!confirm("Apagar esta pendência?")) return;
        await api("POST", "/api/pendencias/apagar", { id: p.id });
        refazer();
      } }, "Apagar")));
  const abertas = r.pendencias.filter((p) => !p.feita);
  const feitas = r.pendencias.filter((p) => p.feita);
  const campo = h("input", { name: "texto", maxlength: "300", placeholder: "Nova pendência", autocomplete: "off" });
  const c = cartao(`Pendências (${abertas.length})`,
    abertas.length ? h("ul", { class: "lista" }, abertas.map(item)) : h("p", { class: "fraco" }, "Nenhuma pendência aberta."),
    h("form", { class: "filtros", onsubmit: async (evento) => {
      evento.preventDefault();
      if (!campo.value.trim()) return;
      const x = await api("POST", "/api/pendencias/nova", { texto: campo.value });
      if (x.ok === false) return avisar(x.erro, "erro");
      refazer();
    } }, campo, h("button", { type: "submit" }, "Adicionar")),
    feitas.length > 0 && h("details", null, h("summary", null, `Resolvidas (${feitas.length})`), h("ul", { class: "lista" }, feitas.map(item))),
    h("p", { class: "fraco" }, r.readme
      ? `As da seção "Pendências conhecidas" de ${r.readme} entram sozinhas e ficam resolvidas quando saem de lá.`
      : "Este servidor não tem README com pendências: as daqui são as que você escrever."));
  return c;
}

async function cartaoProximos() {
  const r = await api("GET", "/api/agendamentos");
  if (r.ok === false) return null;
  const proximos = r.agendamentos.filter((a) => a.ativo && a.proxima).slice(0, 3);
  return cartao("Próximos agendamentos",
    proximos.length ? h("ul", { class: "lista" }, proximos.map((a) => h("li", null, a.nome, h("small", null, ` ${quandoTexto(a.proxima)}`))))
      : h("p", { class: "fraco" }, "Nada agendado."),
    h("a", { href: "#agenda" }, "Ver a agenda"));
}

export async function telaInicio() {
  const extras = Promise.all([cartaoProximos(), cartaoPendencias()]);
  const [recursos, servicos, gasto, sistema] = await Promise.all([
    consultar("status.recursos"), consultar("status.servicos"), consultar("gasto.api"), consultar("status.sistema"),
  ]);
  const cartoes = [];

  if (recursos.ok === false) cartoes.push(cartao("Servidor", falha(recursos)));
  else {
    const r = recursos.resultado;
    const servidor = modulo("Servidor", `${r.nucleos} núcleos · ${gb(r.ram_total_mb)}`,
      visorInicio(r),
      h("div", { class: "discos" }, Object.entries(r.discos).map(([ponto, d]) => [
        linha(`Disco ${ponto}`, `${d.livre_gb} GB livres de ${d.total_gb} GB`), medidor(1 - d.livre_gb / d.total_gb, 0.9),
      ])));
    servidor.classList.add("largo");
    cartoes.push(servidor);
  }

  if (servicos.ok === false) cartoes.push(cartao("Zonas", falha(servicos)));
  else {
    const lista = servicos.resultado;
    const zonas = resumirZonas(lista);
    marcarZonas(zonas);
    const ruins = lista.filter((c) => !containerOk(c));
    const desenho = modulo("Zonas", `${lista.length - ruins.length} de ${lista.length} no ar`,
      vistaExplodida(zonas, abrirZona),
      ruins.length ? h("ul", { class: "lista" }, ruins.map((c) => h("li", null, estadoContainer(c), ` ${c.container} `, h("small", null, statusDocker(c.status, true)))))
        : h("p", { class: "fraco" }, "Todos os containers no ar. Toque numa zona para ver os serviços dela."),
      h("a", { href: "#servicos" }, "Ver os serviços"));
    cartoes.push(desenho);
  }

  if (gasto.ok === false) cartoes.push(cartao("Gasto de IA", falha(gasto)));
  else {
    const g = gasto.resultado;
    cartoes.push(modulo("Gasto de IA", g.mes,
      mostrador(Number(g.total_usd).toFixed(2), "US$ no mês"),
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
    cartoes.push(modulo("Sistema", s.falhas.length ? `${s.falhas.length} com falha` : `${s.timers.length} timers`,
      s.falhas.length ? h("ul", { class: "lista" }, s.falhas.map((u) => h("li", null, h("span", { class: "selo ruim" }, "falhou"), ` ${u}`)))
        : h("p", { class: "fraco" }, "Nenhuma unidade do systemd com falha."),
      h("details", null, h("summary", null, `Timers (${s.timers.length})`),
        h("ul", { class: "lista" }, s.timers.map((t) => h("li", null, t.nome, h("small", null, ` próxima: ${t.proxima ?? "—"}`))))),
    ));
  }
  cartoes.push(...await extras);
  return cartoes;
}
