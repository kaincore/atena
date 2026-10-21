// Atividade: o registro do executor (cada pedido, cada decisão e os eventos).
import { atualizar, cartao, consultar, falha, h, hora, semCentral } from "../comum.js";

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

export async function telaAtividade() {
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
