// Histórico: o que o painel pediu ao executor.
import { NOMES, TERMINADOS, api, cartao, data, estadoTexto, falha, h, item, itens, ledEstado, vazio } from "../comum.js";

export async function telaHistorico() {
  let r = await api("GET", "/api/historico");
  // o que ficou em andamento quando a tela fechou: pergunta ao executor como terminou
  const abertos = r.ok === false ? [] : r.historico.filter((x) => x.pedido && !TERMINADOS.has(x.estado)).slice(0, 10);
  if (abertos.length) {
    await Promise.all(abertos.map((x) => api("GET", `/api/pedido/${x.pedido}`)));
    r = await api("GET", "/api/historico");
  }
  if (r.ok === false) return [cartao("Histórico", falha(r))];
  const historico = cartao("Histórico (90 dias)", itens(r.historico.map((x) => {
    const params = Object.values(JSON.parse(x.params)).join(", ");
    return item({
      led: ledEstado(x.estado), nome: `${NOMES[x.acao] ?? x.acao}${params ? ` (${params})` : ""}`,
      detalhe: `${estadoTexto(x.estado)} · ${data(x.quando)}`,
      extra: x.resumo && h("div", { class: "fraco resumo" }, x.resumo),
    });
  }), vazio("Nenhuma ação feita pelo painel ainda.", "pega"), null, "historico"));
  historico.classList.add("largo");
  return [historico];
}
