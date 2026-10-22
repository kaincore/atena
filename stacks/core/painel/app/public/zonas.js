// As zonas: o resumo de cada uma, os pontos do friso (topo e trilho) e a zona em foco na tela de serviços.
import { ORDEM_ZONAS, atualizar, containerOk, h, telaAtual } from "./comum.js";

export let stacksVistas = []; // a paleta oferece logs e reiniciar dessas
let zonaEmFoco = null;

export function resumirZonas(lista) {
  const zonas = new Map();
  for (const c of lista) {
    if (!zonas.has(c.zona)) zonas.set(c.zona, { zona: c.zona, total: 0, problemas: [] });
    const z = zonas.get(c.zona);
    z.total++;
    if (!containerOk(c)) z.problemas.push(c.container);
  }
  stacksVistas = [...new Set(lista.map((c) => `${c.zona}/${c.stack}`))];
  return [...zonas.values()].sort((a, b) => ORDEM_ZONAS.indexOf(a.zona) - ORDEM_ZONAS.indexOf(b.zona));
}

export function marcarZonas(zonas) {
  for (const caixa of document.querySelectorAll(".zonas-pontos")) {
    caixa.replaceChildren(...zonas.map((z, i) => {
      const led = h("span", { class: `led ${z.problemas.length ? "ruim" : "ok"}` });
      led.style.setProperty("--i", i);
      return h("span", { class: "zona-ponto", title: `${z.zona}: ${z.total - z.problemas.length} de ${z.total} no ar` }, led, h("span", null, z.zona));
    }));
  }
}

export function abrirZona(zona) {
  zonaEmFoco = zona;
  if (telaAtual() === "servicos") atualizar();
  else location.hash = "#servicos";
}

// a tela de serviços pega a zona em foco uma vez, e ela some
export function tirarFoco() {
  const foco = zonaEmFoco;
  zonaEmFoco = null;
  return foco;
}
