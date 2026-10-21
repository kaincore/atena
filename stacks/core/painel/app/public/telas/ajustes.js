// Ajustes: as sessões abertas, a senha e sair.
import { api, atualizar, avisar, cartao, data, falha, h, mostrarEntrada } from "../comum.js";

export async function telaAjustes() {
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
