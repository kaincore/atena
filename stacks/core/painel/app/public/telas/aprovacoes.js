// Aprovações: a central do que espera o dono (os tempos do executor vêm em segundos) e a faixa amarela.
import { $, atualizar, avisar, cartao, consultar, estadoTexto, falha, h, hora, item, itens, ledEstado, mudar, semCentral, telaAtual } from "../comum.js";
import { picto } from "../pictos.js";

function relativo(s) {
  const minutos = Math.round((s * 1000 - Date.now()) / 60000);
  if (minutos === 0) return "agora";
  return minutos > 0 ? `em ${minutos}\u00a0min` : `há ${-minutos}\u00a0min`;
}

let pendentes = 0;

// a contagem vai para a tecla das Aprovações (trilho e "Mais"), para o "Mais" da barra e para o título;
// quando cresce, a faixa amarela aparece (ou pulsa) na tela aberta
function marcarPendentes(n) {
  const cresceu = n > pendentes;
  pendentes = n;
  for (const el of document.querySelectorAll('[data-tela="aprovacoes"], [data-tela="mais"]')) {
    el.querySelector(".contagem")?.remove();
    if (n) el.append(h("span", { class: "contagem", "aria-label": `${n} esperando` }, String(n)));
  }
  const base = document.title.replace(/^\(\d+\) /, ""); // o nome da tela fica; a contagem vai na frente
  document.title = n ? `(${n}) ${base}` : base;
  const atual = $("#tela .faixa");
  const nova = faixaAprovacoes(cresceu);
  if (atual) atual.replaceWith(nova ?? "");
  else if (nova && $("#entrada").hidden) $("#tela").prepend(nova);
}

export function faixaAprovacoes(pulsar = false) {
  if (!pendentes || telaAtual() === "aprovacoes") return null;
  const faixa = h("a", { class: `faixa${pulsar ? " pulsa" : ""}`, href: "#aprovacoes" },
    h("strong", null, picto("aprovacoes"), ` ${pendentes} ${pendentes === 1 ? "aprovação esperando" : "aprovações esperando"} você`),
    h("span", { class: "rotulo" }, "Ver", picto("seguir")));
  // a luz passa uma vez: a faixa fica na tela entre as trocas, e não pode chamar de novo a cada uma
  if (pulsar) setTimeout(() => faixa.classList.remove("pulsa"), 2200);
  return faixa;
}

export async function contarPendentes() {
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
      } }, campo, h("button", { type: "submit", class: "principal" }, "Responder")));
  }
  const params = Object.entries(p.params ?? {});
  return cartao(p.titulo ?? p.acao, meta,
    p.texto && h("pre", { class: "texto-pedido" }, p.texto),
    params.length > 0 && h("details", null, h("summary", null, "Parâmetros"),
      h("ul", { class: "lista" }, params.map(([k, v]) => h("li", null, h("span", { class: "rotulo" }, `${k}: `), v)))),
    h("div", { class: "botoes grandes" },
      h("button", { type: "button", class: "principal", onclick: () => decidirPedido(p, "aprovar") }, "Aprovar"),
      h("button", { type: "button", onclick: () => decidirPedido(p, "recusar") }, "Recusar")));
}

export async function telaAprovacoes() {
  const r = await consultar("aprovacoes.lista");
  if (r.ok === false) return [cartao("Aprovações", falha(r), semCentral(r))];
  const { pendentes, recentes } = r.resultado;
  marcarPendentes(pendentes.length);
  return [
    pendentes.length ? pendentes.map(cartaoPendente)
      : cartao("Aprovações", h("p", { class: "fraco" }, "Nada esperando por você. Os pedidos da Atena e do Claude Code aparecem aqui e no celular.")),
    cartao("Decididos há pouco", itens(recentes.map((x) => item({
      led: ledEstado(x.estado), nome: x.titulo ?? x.acao,
      detalhe: [estadoTexto(x.estado), x.cliente, hora(x.quando), x.por && `por ${x.por}`].filter(Boolean).join(" · "),
      extra: x.erro && h("div", { class: "fraco resumo" }, x.erro),
    })), "Nenhum ainda.")),
  ];
}
