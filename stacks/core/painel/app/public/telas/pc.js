// PC: ligar, desligar e reiniciar o PC da rede de casa.
import { atualizar, cartao, consultar, falha, h, modulo, mudar } from "../comum.js";
import { picto } from "../pictos.js";
import { medalhao, medalhoes } from "../desenhos.js";

// a cena do PC ligando: no primeiro minuto depois de ligar, o meandro do medalhão se pinta uma vez
let pcLigadoEm = 0;
let pintado = false;

export function marcarPcLigado() {
  pcLigadoEm = Date.now();
  pintado = false;
}

function medalhoesPC({ ligado, lm_studio }) {
  const pintar = ligado && !pintado && Date.now() - pcLigadoEm < 60_000;
  if (pintar) pintado = true;
  return medalhoes(
    medalhao({ rotulo: "PC gamer", desenho: picto("pc"), fracao: ligado ? 1 : null, cor: "azul",
      nota: [h("span", { class: `led ${ligado ? "ok" : ""}` }), ligado ? "ligado na rede de casa" : "desligado"],
      classe: `${ligado ? "pc-ligado" : "pc-desligado"}${pintar ? " pintando" : ""}` }),
    medalhao({ rotulo: "LM Studio", desenho: picto("atividade"), fracao: lm_studio ? 1 : null, cor: "azul",
      nota: [h("span", { class: `led ${lm_studio ? "ok" : ""}` }), lm_studio ? "respondendo" : "fora do ar"],
      classe: lm_studio ? "pc-ligado" : "pc-desligado" }),
  );
}

export async function telaPC() {
  const r = await consultar("pc.estado");
  if (r.ok === false) return [cartao("PC gamer", falha(r))];
  const { ligado, lm_studio } = r.resultado;
  const depois = async (resposta) => { if (resposta) setTimeout(atualizar, 3000); };
  const pc = modulo("PC gamer", ligado ? "ligado" : "desligado",
    medalhoesPC(r.resultado),
    h("div", { class: "botoes grandes" },
      !ligado && h("button", { type: "button", class: "principal", onclick: async () => {
        const x = await mudar("pc.ligar", {});
        if (x && x.ok !== false) marcarPcLigado();
        depois(x);
      } }, picto("pc"), "Ligar"),
      ligado && h("button", { type: "button", onclick: async () => depois(await mudar("pc.desligar", {}, "Desligar o PC gamer? Ele desliga em 60 s.")) }, "Desligar"),
      ligado && h("button", { type: "button", onclick: async () => depois(await mudar("pc.reiniciar", {}, "Reiniciar o PC gamer? Ele reinicia em 60 s.")) }, "Reiniciar"),
      ligado && h("button", { type: "button", class: "discreto", onclick: async () => depois(await mudar("pc.cancelar", {})) }, "Cancelar desligamento"),
    ),
    h("p", { class: "fraco" }, "Ligar leva uns 25 s; o LM Studio sobe uns 25 s depois."),
  );
  return [pc];
}
