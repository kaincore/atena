// Pictogramas do painel: desenhados aqui, numa grade de 24 e num traço só (1,75), como os rótulos
// impressos de um aparelho. Nada de caractere Unicode fazendo papel de ícone.

const SVG = "http://www.w3.org/2000/svg";

// cada um: lista de [elemento, atributos]; o traço e a cor vêm do CSS (currentColor)
const DESENHOS = {
  inicio: [["path", { d: "M4 11.2 12 4.5l8 6.7V19a1 1 0 0 1-1 1h-4.5v-5.5h-5V20H5a1 1 0 0 1-1-1z" }]],
  aprovacoes: [["rect", { x: 4, y: 4, width: 16, height: 16, rx: 2.5 }], ["path", { d: "m8.2 12.3 2.6 2.6 5-5.6" }]],
  servicos: [
    ["rect", { x: 4, y: 4.5, width: 16, height: 4.2, rx: 1 }], ["rect", { x: 4, y: 9.9, width: 16, height: 4.2, rx: 1 }],
    ["rect", { x: 4, y: 15.3, width: 16, height: 4.2, rx: 1 }],
    ["circle", { cx: 7, cy: 6.6, r: 0.6, class: "cheio" }], ["circle", { cx: 7, cy: 12, r: 0.6, class: "cheio" }],
    ["circle", { cx: 7, cy: 17.4, r: 0.6, class: "cheio" }],
  ],
  sistema: [["path", { d: "M4.5 16.5a7.5 7.5 0 1 1 15 0" }], ["path", { d: "m12 16.5 3.6-4.4" }], ["path", { d: "M4.5 19.5h15" }]],
  pc: [["path", { d: "M12 4v7" }], ["path", { d: "M7.4 7.2a6.8 6.8 0 1 0 9.2 0" }]],
  lab: [["path", { d: "M9.5 4h5M10.5 4v5.2L5.6 17.8A1.5 1.5 0 0 0 6.9 20h10.2a1.5 1.5 0 0 0 1.3-2.2L13.5 9.2V4" }], ["path", { d: "M7.6 14.5h8.8" }]],
  agenda: [["circle", { cx: 12, cy: 12, r: 8 }], ["path", { d: "M12 7.5V12l3 2" }]],
  arquivos: [["path", { d: "M3.8 7.2A1.7 1.7 0 0 1 5.5 5.5h4l2 2.2h7a1.7 1.7 0 0 1 1.7 1.7v8.4a1.7 1.7 0 0 1-1.7 1.7h-13a1.7 1.7 0 0 1-1.7-1.7z" }]],
  documento: [["path", { d: "M7 3.8h6.6l4.2 4.2v11a1.2 1.2 0 0 1-1.2 1.2H7a1.2 1.2 0 0 1-1.2-1.2V5A1.2 1.2 0 0 1 7 3.8z" }],
    ["path", { d: "M13.4 4v4.2h4.2M9 12.6h6M9 15.9h4" }]],
  subir: [["path", { d: "M8.5 9.5 12 6l3.5 3.5" }], ["path", { d: "M12 6v8.5a3 3 0 0 0 3 3h4" }]],
  atividade: [["path", { d: "M3.5 12.5h4l2.2-5.5 4.2 10 2.3-4.5h4.3" }]],
  historico: [["path", { d: "M5.2 9.2A7.5 7.5 0 1 1 4.5 12" }], ["path", { d: "M4.5 5.5v3.7h3.7" }], ["path", { d: "M12 8v4.3l2.6 1.6" }]],
  ajustes: [
    ["path", { d: "M6.5 4v16M12 4v16M17.5 4v16" }],
    ["rect", { x: 4.5, y: 13, width: 4, height: 2.6, rx: 0.8, class: "tampa" }],
    ["rect", { x: 10, y: 7, width: 4, height: 2.6, rx: 0.8, class: "tampa" }],
    ["rect", { x: 15.5, y: 15.5, width: 4, height: 2.6, rx: 0.8, class: "tampa" }],
  ],
  mais: [["circle", { cx: 6.5, cy: 12, r: 1.4, class: "cheio" }], ["circle", { cx: 12, cy: 12, r: 1.4, class: "cheio" }], ["circle", { cx: 17.5, cy: 12, r: 1.4, class: "cheio" }]],
  buscar: [["circle", { cx: 10.5, cy: 10.5, r: 5.8 }], ["path", { d: "m15 15 4.8 4.8" }]],
  fechar: [["path", { d: "m6.5 6.5 11 11M17.5 6.5l-11 11" }]],
  seguir: [["path", { d: "m9.5 6.5 5.5 5.5-5.5 5.5" }]],
  sair: [["path", { d: "M10 4.5H6a1.5 1.5 0 0 0-1.5 1.5v12A1.5 1.5 0 0 0 6 19.5h4" }], ["path", { d: "M14 8.5 17.5 12 14 15.5M17.5 12H9.5" }]],
};

export function picto(nome, rotulo) {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", `picto picto-${nome}`);
  if (rotulo) {
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", rotulo);
  } else svg.setAttribute("aria-hidden", "true");
  for (const [tag, atributos] of DESENHOS[nome] ?? []) {
    const el = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(atributos)) el.setAttribute(k, String(v));
    svg.append(el);
  }
  return svg;
}
