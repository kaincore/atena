// Pictogramas do painel: desenhados aqui, numa grade de 24 e num traço só (1,5), com as coisas do
// mundo grego no lugar das de sempre quando elas dizem o mesmo (o Início é a frente do templo; os
// serviços, que são contêineres, uma ânfora). A parte "tinta" é a área que os gregos pintavam (o
// tímpano, a faixa da ânfora, o líquido do frasco): só se acende na tela ativa. Nada de caractere
// Unicode fazendo papel de ícone.

const SVG = "http://www.w3.org/2000/svg";

// a engrenagem de Anticítera: 9 dentes, o aro e quatro raios
function engrenagem() {
  const p = (r, graus) => {
    const a = ((graus - 90) * Math.PI) / 180;
    return `${(12 + r * Math.cos(a)).toFixed(2)} ${(12 + r * Math.sin(a)).toFixed(2)}`;
  };
  let d = "";
  for (let i = 0; i < 9; i++) {
    const a = i * 40;
    d += `${i ? " L" : "M"}${p(6.9, a - 13)} L${p(8.7, a - 7)} L${p(8.7, a + 7)} L${p(6.9, a + 13)}`;
  }
  return [["path", { d: `${d} Z` }], ["circle", { cx: 12, cy: 12, r: 4.6, class: "tinta" }], ["circle", { cx: 12, cy: 12, r: 4.6 }],
    ["path", { d: "M12 7.4v9.2M7.4 12h9.2" }], ["circle", { cx: 12, cy: 12, r: 1.3, class: "cheio" }]];
}

// cada um: lista de [elemento, atributos]; o traço e a cor vêm do CSS (currentColor)
const DESENHOS = {
  inicio: [
    ["path", { d: "M6.7 8.2 12 5.1l5.3 3.1z", class: "tinta" }],
    ["path", { d: "M3.4 9.2 12 3.9l8.6 5.3z" }], ["path", { d: "M4.2 10.8h15.6" }],
    ["path", { d: "M6.6 12.6v5.3M10.2 12.6v5.3M13.8 12.6v5.3M17.4 12.6v5.3" }], ["path", { d: "M4.6 19.4h14.8M3.4 21h17.2" }],
  ],
  aprovacoes: [
    ["path", { d: "M5 9.3c-1.5-1-1.9-2.9-1.1-4.4 1.4.8 1.9 2.8 1.1 4.4zM4.9 13.6c-1.9-.4-2.9-2-2.8-3.7 1.7.2 2.8 1.9 2.8 3.7zM6.7 17.4c-1.9.2-3.4-.9-3.9-2.5 1.7-.3 3.3.8 3.9 2.5zM19 9.3c1.5-1 1.9-2.9 1.1-4.4-1.4.8-1.9 2.8-1.1 4.4zM19.1 13.6c1.9-.4 2.9-2 2.8-3.7-1.7.2-2.8 1.9-2.8 3.7zM17.3 17.4c1.9.2 3.4-.9 3.9-2.5-1.7-.3-3.3.8-3.9 2.5z", class: "tinta" }],
    ["path", { d: "M10.8 20.4C6.4 19.2 4.2 15 5 9.3M13.2 20.4c4.4-1.2 6.6-5.4 5.8-11.1" }],
    ["path", { d: "M5 9.3c-1.5-1-1.9-2.9-1.1-4.4 1.4.8 1.9 2.8 1.1 4.4zM4.9 13.6c-1.9-.4-2.9-2-2.8-3.7 1.7.2 2.8 1.9 2.8 3.7zM6.7 17.4c-1.9.2-3.4-.9-3.9-2.5 1.7-.3 3.3.8 3.9 2.5zM19 9.3c1.5-1 1.9-2.9 1.1-4.4-1.4.8-1.9 2.8-1.1 4.4zM19.1 13.6c1.9-.4 2.9-2 2.8-3.7-1.7.2-2.8 1.9-2.8 3.7zM17.3 17.4c1.9.2 3.4-.9 3.9-2.5-1.7-.3-3.3.8-3.9 2.5z", class: "fino" }],
    ["path", { d: "m8.9 12.6 2.2 2.3 4.2-4.6" }],
  ],
  servicos: [
    ["path", { d: "M7 10.4h10v2.3H7z", class: "tinta" }],
    ["path", { d: "M9.4 3.6h5.2M10.3 3.6v2.8M13.7 3.6v2.8" }],
    ["path", { d: "M10.3 6.4C6.8 7.6 6 11.6 7.5 15c1.2 2.7 3.1 4.4 4.5 5.4 1.4-1 3.3-2.7 4.5-5.4 1.5-3.4.7-7.4-2.8-8.6" }],
    ["path", { d: "M10.3 4.8C7.8 4.6 6.6 6.8 7.9 9M13.7 4.8c2.5-.2 3.7 2 2.4 4.2M12 20.4v1.2" }],
    ["path", { d: "M7 10.4h10M7 12.7h10", class: "fino" }],
  ],
  sistema: engrenagem(),
  pc: [
    ["rect", { x: 5.3, y: 6.3, width: 13.4, height: 7.8, rx: 0.6, class: "tinta" }],
    ["rect", { x: 3.4, y: 4.4, width: 17.2, height: 11.6, rx: 1.6 }], ["path", { d: "M12 16v3.4M8.6 19.6h6.8" }],
  ],
  // a rede de casa: o servidor no meio, ligado a quatro aparelhos
  rede: [
    ["circle", { cx: 12, cy: 12, r: 2.8, class: "tinta" }], ["circle", { cx: 12, cy: 12, r: 2.8 }],
    ["circle", { cx: 5.2, cy: 6.2, r: 1.7 }], ["circle", { cx: 18.8, cy: 6.2, r: 1.7 }],
    ["circle", { cx: 5.2, cy: 17.8, r: 1.7 }], ["circle", { cx: 18.8, cy: 17.8, r: 1.7 }],
    ["path", { d: "M9.87 10.18 6.49 7.3M14.13 10.18l3.38-2.88M9.87 13.82 6.49 16.7M14.13 13.82l3.38 2.88", class: "fino" }],
  ],
  lab: [
    ["path", { d: "M7.1 14.6h9.8l1.7 3.1a1.4 1.4 0 0 1-1.3 1.9H6.7a1.4 1.4 0 0 1-1.3-1.9z", class: "tinta" }],
    ["path", { d: "M9.4 3.6h5.2M10.3 3.6v5.2L5.3 17.6A1.6 1.6 0 0 0 6.7 20h10.6a1.6 1.6 0 0 0 1.4-2.4l-5-8.8V3.6" }],
    ["path", { d: "M7.1 14.6h9.8", class: "fino" }],
    ["circle", { cx: 11, cy: 12.1, r: 0.75, class: "cheio" }], ["circle", { cx: 13.3, cy: 10.6, r: 0.55, class: "cheio" }],
  ],
  // a cílica (o copo raso de duas alças): a faixa pintada dentro do bojo é a tinta
  receitas: [
    ["path", { d: "M5.5 11.3h13c-.9 2.1-3.4 3.5-6.5 3.5s-5.6-1.4-6.5-3.5z", class: "tinta" }],
    ["path", { d: "M3.6 9.4h16.8c-.6 3.7-3.9 6.2-8.4 6.2s-7.8-2.5-8.4-6.2z" }],
    ["path", { d: "M3.6 9.4C1.8 9.2 1.3 11.3 2.9 12.1M20.4 9.4c1.8-.2 2.3 1.9.7 2.7" }],
    ["path", { d: "M12 15.6v3.2M8.4 19.6h7.2" }],
    ["path", { d: "M5.5 11.3h13", class: "fino" }],
  ],
  // o elmo coríntio de Atena, de frente: a crista é a tinta; as fendas dos olhos e o vão da boca
  atena: [
    ["path", { d: "M8.4 5.3c1-1.9 6.2-1.9 7.2 0L12 6.1z", class: "tinta" }],
    ["path", { d: "M8.4 5.3c1-1.9 6.2-1.9 7.2 0" }],
    ["path", { d: "M5.9 11.4C5.9 7.9 8.6 5.5 12 5.5s6.1 2.4 6.1 5.9v4.5c0 2-1.1 3.6-2.9 4.5M5.9 11.4v4.5c0 2 1.1 3.6 2.9 4.5" }],
    ["path", { d: "M7.6 11.9c1-.6 2.3-.7 3.4-.2M16.4 11.9c-1-.6-2.3-.7-3.4-.2" }],
    ["path", { d: "M12 10.4v3.4M10.5 15v5.4M13.5 15v5.4", class: "fino" }],
  ],
  agenda: [
    ["path", { d: "M12 12V4.4a7.6 7.6 0 0 1 6.6 3.8z", class: "tinta" }],
    ["circle", { cx: 12, cy: 12, r: 8.4 }], ["path", { d: "M12 4.6v1.2M19.4 12h-1.2M12 19.4v-1.2M4.6 12h1.2", class: "fino" }],
    ["path", { d: "M12 7.6V12l3.1 1.9" }],
  ],
  arquivos: [
    ["rect", { x: 7, y: 6.2, width: 10, height: 10.8, class: "tinta" }],
    ["path", { d: "M5.6 3.4h12.8a1.4 1.4 0 0 1 0 2.8H5.6a1.4 1.4 0 0 1 0-2.8zM5.6 17h12.8a1.6 1.6 0 0 1 0 3.2H5.6a1.6 1.6 0 0 1 0-3.2z" }],
    ["path", { d: "M7 6.2V17M17 6.2V17" }], ["path", { d: "M9.5 9.2h5M9.5 11.8h5M9.5 14.4h3.2", class: "fino" }],
  ],
  pasta: [["path", { d: "M3.8 7.2A1.7 1.7 0 0 1 5.5 5.5h4l2 2.2h7a1.7 1.7 0 0 1 1.7 1.7v8.4a1.7 1.7 0 0 1-1.7 1.7h-13a1.7 1.7 0 0 1-1.7-1.7z" }]],
  documento: [["path", { d: "M7 3.8h6.6l4.2 4.2v11a1.2 1.2 0 0 1-1.2 1.2H7a1.2 1.2 0 0 1-1.2-1.2V5A1.2 1.2 0 0 1 7 3.8z" }],
    ["path", { d: "M13.4 4v4.2h4.2M9 12.6h6M9 15.9h4" }]],
  subir: [["path", { d: "M8.5 9.5 12 6l3.5 3.5" }], ["path", { d: "M12 6v8.5a3 3 0 0 0 3 3h4" }]],
  atividade: [["path", { d: "M3.2 12.6h3.4l2-5.2 3.8 10 2.2-5.4h6.2" }]],
  historico: [
    ["path", { d: "M9.3 19.8c.4-2.2 1.6-3.2 2.7-3.2s2.3 1 2.7 3.2zM9.5 6.6h5c-.6 2-1.7 3-2.5 4-.8-1-1.9-2-2.5-4z", class: "tinta" }],
    ["path", { d: "M7 3.8h10M7 20.2h10" }],
    ["path", { d: "M8.2 3.8c0 4.8 3 6.2 3 8.2s-3 3.4-3 8.2M15.8 3.8c0 4.8-3 6.2-3 8.2s3 3.4 3 8.2" }],
    ["path", { d: "M12 12.8v3.4", class: "fino" }],
  ],
  ajustes: [
    ["path", { d: "M6.5 4v16M12 4v16M17.5 4v16" }],
    ["rect", { x: 4.5, y: 13, width: 4, height: 2.6, rx: 0.8, class: "tampa" }],
    ["rect", { x: 10, y: 7, width: 4, height: 2.6, rx: 0.8, class: "tampa" }],
    ["rect", { x: 15.5, y: 15.5, width: 4, height: 2.6, rx: 0.8, class: "tampa" }],
  ],
  mais: [["circle", { cx: 6.5, cy: 12, r: 1.35, class: "cheio" }], ["circle", { cx: 12, cy: 12, r: 1.35, class: "cheio" }], ["circle", { cx: 17.5, cy: 12, r: 1.35, class: "cheio" }]],
  buscar: [["circle", { cx: 10.5, cy: 10.5, r: 5.8 }], ["path", { d: "m15 15 4.8 4.8" }]],
  // o chat da Atena: o estilete na tabuinha (conversa nova), a gaveta das conversas, enviar, parar, descer e
  // copiar (as duas tabuinhas)
  escrever: [["path", { d: "M5.5 18.5h3.2l9.6-9.6a2.26 2.26 0 0 0-3.2-3.2L5.5 15.3z", class: "tinta" }],
    ["path", { d: "M5.5 18.5h3.2l9.6-9.6a2.26 2.26 0 0 0-3.2-3.2L5.5 15.3zM13.6 7.2l3.2 3.2" }], ["path", { d: "M4 21h16", class: "fino" }]],
  lado: [["rect", { x: 3.6, y: 4.6, width: 5.4, height: 14.8, rx: 1.4, class: "tinta" }],
    ["rect", { x: 3.6, y: 4.6, width: 16.8, height: 14.8, rx: 2 }], ["path", { d: "M9 4.6v14.8" }]],
  enviar: [["path", { d: "M12 18.5V5.8M6.6 11.2 12 5.8l5.4 5.4" }]],
  parar: [["rect", { x: 7.4, y: 7.4, width: 9.2, height: 9.2, rx: 1.6, class: "cheio" }]],
  descer: [["path", { d: "M12 5.5v12.7M6.6 12.8l5.4 5.4 5.4-5.4" }]],
  copiar: [["rect", { x: 8.6, y: 8.6, width: 10.8, height: 10.8, rx: 1.8 }],
    ["path", { d: "M15.4 8.6V6.2a1.6 1.6 0 0 0-1.6-1.6H6.2a1.6 1.6 0 0 0-1.6 1.6v7.6a1.6 1.6 0 0 0 1.6 1.6h2.4" }]],
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
    // o traço se refaz quando a tela fica ativa (a tinta e os cheios só acendem)
    if (!/tinta|cheio|tampa/.test(atributos.class ?? "")) el.setAttribute("pathLength", "1");
    svg.append(el);
  }
  return svg;
}
