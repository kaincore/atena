// PC: ligar, desligar e reiniciar o PC da rede de casa.
import { atualizar, cartao, consultar, falha, h, modulo, mudar } from "../comum.js";
import { picto } from "../pictos.js";
import { visorPC } from "../visor.js";

let pcLigadoEm = 0; // a cena da ventoinha acelerando vale no primeiro minuto depois de ligar

export function marcarPcLigado() {
  pcLigadoEm = Date.now();
}

export async function telaPC() {
  const r = await consultar("pc.estado");
  if (r.ok === false) return [cartao("PC gamer", falha(r))];
  const { ligado, lm_studio } = r.resultado;
  const depois = async (resposta) => { if (resposta) setTimeout(atualizar, 3000); };
  const pc = modulo("PC gamer", ligado ? "ligado" : "desligado",
    visorPC(r.resultado, ligado && Date.now() - pcLigadoEm < 60_000),
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
