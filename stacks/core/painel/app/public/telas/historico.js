// Histórico: o que o painel pediu ao executor.
import { NOMES, TERMINADOS, api, cartao, data, estadoTexto, falha, h } from "../comum.js";

export async function telaHistorico() {
  let r = await api("GET", "/api/historico");
  // o que ficou em andamento quando a tela fechou: pergunta ao executor como terminou
  const abertos = r.ok === false ? [] : r.historico.filter((x) => x.pedido && !TERMINADOS.has(x.estado)).slice(0, 10);
  if (abertos.length) {
    await Promise.all(abertos.map((x) => api("GET", `/api/pedido/${x.pedido}`)));
    r = await api("GET", "/api/historico");
  }
  if (r.ok === false) return [cartao("Histórico", falha(r))];
  const historico = cartao("Histórico (90 dias)", r.historico.length ? h("ul", { class: "lista historico" }, r.historico.map((x) => {
    const params = Object.values(JSON.parse(x.params)).join(", ");
    const ok = x.estado === "concluido";
    return h("li", null,
      h("span", { class: `selo ${ok ? "ok" : TERMINADOS.has(x.estado) ? "ruim" : "neutro"}` }, estadoTexto(x.estado)),
      ` ${NOMES[x.acao] ?? x.acao}${params ? ` (${params})` : ""} `,
      h("small", null, data(x.quando)),
      x.resumo && h("div", { class: "fraco resumo" }, x.resumo));
  })) : h("p", { class: "fraco" }, "Nenhuma ação feita pelo painel ainda."));
  historico.classList.add("largo");
  return [historico];
}
