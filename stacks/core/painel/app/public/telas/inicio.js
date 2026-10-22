// Início: o servidor nos medalhões, a crepidoma das zonas, o gasto, os próximos agendamentos e as pendências.
import { api, avisar, cartao, consultar, containerOk, dinheiro, falha, gb, h, item, itens, linha, medidor, modulo,
  num, numeroGrande, plural, statusDocker } from "../comum.js";
import { quandoTexto } from "./agenda.js";
import { abrirZona, marcarZonas, resumirZonas } from "../zonas.js";
import { crepidoma, medalhao, medalhoes } from "../desenhos.js";

// a CPU, a temperatura dela, a RAM e a GPU: o meandro da borda pintado até onde cada uma chega
function medalhoesServidor(r) {
  const carga = r.carga[0] / r.nucleos;
  const usada = (r.ram_total_mb - r.ram_disponivel_mb) / 1024;
  const total = r.ram_total_mb / 1024;
  const cpu = r.temperaturas.cpu_c;
  return medalhoes(
    medalhao({ rotulo: "CPU", numero: num(Math.min(99.9, carga * 100), carga < 0.1 ? 1 : 0), unidade: "%", fracao: carga,
      nota: `carga ${num(r.carga[0], 2)} em ${r.nucleos} núcleos` }),
    cpu != null && medalhao({ rotulo: "Temperatura", numero: num(cpu, 1), unidade: "°C", fracao: cpu / 85, nota: "da CPU" }),
    medalhao({ rotulo: "RAM", numero: num(usada, 1), unidade: "GB", fracao: usada / total, alerta: 0.95, nota: `de ${num(total, 1)}\u00a0GB` }),
    r.gpu && medalhao({ rotulo: "GPU", numero: num(r.gpu.temperatura_c), unidade: "°C", fracao: r.gpu.temperatura_c / 85,
      nota: `uso ${num(r.gpu.uso_pct)}% · VRAM ${num(r.gpu.vram_usada_mb / 1024, 1)} de ${num(r.gpu.vram_total_mb / 1024, 1)}\u00a0GB` }),
  );
}

// "**negrito**" e "`código`" do README, sem innerHTML
function marcado(texto) {
  return texto.split(/(\*\*[^*]+\*\*|`[^`]+`)/).filter(Boolean).map((s) =>
    s.startsWith("**") ? h("strong", null, s.slice(2, -2)) : s.startsWith("`") ? h("code", null, s.slice(1, -1)) : s);
}

async function cartaoPendencias() {
  const r = await api("GET", "/api/pendencias");
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

async function cartaoProximos() {
  const r = await api("GET", "/api/agendamentos");
  if (r.ok === false) return null;
  const proximos = r.agendamentos.filter((a) => a.ativo && a.proxima).slice(0, 3);
  return cartao("Próximos agendamentos",
    itens(proximos.map((a) => item({ led: "info", nome: a.nome, detalhe: quandoTexto(a.proxima) })), "Nada agendado."),
    h("p", null, h("a", { href: "#agenda" }, "Ver a agenda")));
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
      medalhoesServidor(r),
      h("div", { class: "discos" }, Object.entries(r.discos).map(([ponto, d]) => [
        linha(`Disco ${ponto}`, `${num(d.livre_gb, 1)}\u00a0GB livres de ${num(d.total_gb, 1)}\u00a0GB`), medidor(1 - d.livre_gb / d.total_gb, 0.9),
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
      crepidoma(zonas, abrirZona),
      ruins.length ? itens(ruins.map((c) => item({ led: "ruim", nome: c.container, detalhe: statusDocker(c.status) })))
        : h("p", { class: "fraco" }, "Todos os containers no ar. Toque numa zona para ver os serviços dela."),
      h("p", null, h("a", { href: "#servicos" }, "Ver os serviços")));
    cartoes.push(desenho);
  }

  if (gasto.ok === false) cartoes.push(cartao("Gasto de IA", falha(gasto)));
  else {
    const g = gasto.resultado;
    cartoes.push(modulo("Gasto de IA", g.mes,
      numeroGrande(dinheiro(g.total_usd), "no mês"),
      g.por_modelo.filter((m) => m.gasto_usd > 0 || m.teto_usd).map((m) => [
        linha(m.modelo, [`${dinheiro(m.gasto_usd)}${m.teto_usd ? ` de ${dinheiro(m.teto_usd)}` : ""}`, h("small", null, ` · ${plural(m.chamadas, "chamada", "chamadas")}`)]),
        m.teto_usd ? medidor(m.gasto_usd / m.teto_usd) : null,
      ]),
      h("p", { class: "fraco" }, g.obs),
    ));
  }

  if (sistema.ok === false) cartoes.push(cartao("Sistema", falha(sistema)));
  else {
    const s = sistema.resultado;
    cartoes.push(modulo("Sistema", s.falhas.length ? `${s.falhas.length} com falha` : `${s.timers.length} timers`,
      s.falhas.length ? itens(s.falhas.map((u) => item({ led: "ruim", nome: u, detalhe: "falhou" })))
        : h("p", { class: "fraco" }, "Nenhuma unidade do systemd com falha."),
      h("details", null, h("summary", null, `Timers (${s.timers.length})`),
        itens(s.timers.map((t) => item({ nome: t.nome, detalhe: `próxima: ${t.proxima ?? "—"}` })))),
    ));
  }
  cartoes.push(...await extras);
  return cartoes;
}
