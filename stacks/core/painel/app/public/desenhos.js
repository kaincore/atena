// Os desenhos do painel, no mundo da policromia (os templos gregos eram pintados): o meandro, que
// também mede; a construção do templo na entrada, como uma prancha de arquiteto; os medalhões dos números; a
// crepidoma das zonas (os degraus do templo, em 3D) e o relógio de sol da agenda. Tudo em SVG ou em
// elementos montados um a um, a partir dos dados de verdade. O movimento vem do CSS e para com
// prefers-reduced-motion.

const SVG = "http://www.w3.org/2000/svg";

export function s(tag, atributos, ...filhos) {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(atributos ?? {})) if (v != null && v !== false) el.setAttribute(k, String(v));
  for (const f of filhos.flat(Infinity)) if (f != null && f !== false) el.append(f instanceof Node ? f : document.createTextNode(String(f)));
  return el;
}

function h(tag, classe, ...filhos) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  for (const f of filhos.flat(Infinity)) if (f != null && f !== false) el.append(f instanceof Node ? f : String(f));
  return el;
}

const limite = (x, a = 0, b = 1) => Math.max(a, Math.min(b, Number.isFinite(x) ? x : 0));
const r2 = (n) => Math.round(n * 100) / 100;
// a cor do que mede: azul até perto do limite, ocre perto, cinábrio passado
export const tom = (fracao) => (fracao >= 1 ? "cinabrio" : fracao >= 0.85 ? "ocre" : "azul");

// --- o meandro: um traço só, que entra na espiral e sai pela base até a volta seguinte --------------
// cada volta ocupa 4 unidades de largura e 3 de altura; o traço chega pela base em (0,3)
const VOLTA = [[0, 0], [3, 0], [3, 2], [2, 2], [2, 1], [1, 1], [1, 3], [4, 3]];

export function caminhoMeandro(voltas, g = 4) {
  let d = `M0 ${3 * g}`;
  for (let i = 0; i < voltas; i++) for (const [x, y] of VOLTA) d += ` L${(i * 4 + x) * g} ${y * g}`;
  return d;
}

const voltasDoAnel = (raio, g) => Math.max(6, Math.round((2 * Math.PI * (raio - 1.5 * g)) / (4 * g)));

// o mesmo meandro dando a volta num círculo (a borda de um medalhão), fechado sem emenda
export function caminhoMeandroCircular(raio, g) {
  const voltas = voltasDoAnel(raio, g);
  const total = voltas * 4;
  const ponto = (x, y) => {
    const a = (x / total) * 2 * Math.PI - Math.PI / 2;
    const r = raio - y * g;
    return `${r2(r * Math.cos(a))} ${r2(r * Math.sin(a))}`;
  };
  let [px, py] = [0, 3];
  let d = `M${ponto(0, 3)}`;
  for (let i = 0; i < voltas; i++) for (const [x, y] of VOLTA) {
    const X = i * 4 + x;
    // no mesmo raio, o traço é um arco; entre raios, uma reta
    d += y === py ? ` A${r2(raio - y * g)} ${r2(raio - y * g)} 0 0 ${X > px ? 1 : 0} ${ponto(X, y)}` : ` L${ponto(X, y)}`;
    [px, py] = [X, y];
  }
  return `${d} Z`;
}

// uma faixa de meandro na largura do que estiver em volta (corta no fim, como uma faixa que continua)
export function faixa(classe = "", voltas = 60, g = 4) {
  return s("svg", { viewBox: `-1 -1 ${voltas * 4 * g + 2} ${3 * g + 2}`, preserveAspectRatio: "xMinYMid slice", class: `faixa-meandro ${classe}`.trim(), "aria-hidden": "true" },
    s("path", { d: caminhoMeandro(voltas, g), class: "traco", pathLength: 1 }));
}

// a chave: uma volta do meandro, o ornamento antes do título de cada módulo
export function chave() {
  return s("svg", { viewBox: "-1 -1 18 14", class: "chave", "aria-hidden": "true" },
    s("path", { d: "M0 12 V0 H12 V8 H8 V4 H4 V12 H16", class: "traco", pathLength: 1 }));
}

// --- os medalhões: o número no meio, e o meandro da borda pintado até onde ele chega -----------------

// alerta: a fração em que a medida passa do limite (a cor vai do azul ao ocre e ao cinábrio);
// cor: uma cor fixa no lugar dessa conta (o PC ligado fica no azul de acento)
export function medalhao({ rotulo, numero, unidade, fracao, alerta = 1, nota, desenho, cor, classe }) {
  const f = fracao == null ? null : limite(fracao);
  const anel = caminhoMeandroCircular(56, 3.6);
  const pintado = f != null && s("path", { d: anel, class: "tinta", pathLength: 1 });
  // a tinta acaba numa volta inteira do meandro; um valor acima de zero pinta ao menos uma
  const voltas = voltasDoAnel(56, 3.6);
  if (pintado) pintado.style.setProperty("--fracao", (f > 0 ? Math.max(1, Math.round(f * voltas)) / voltas : 0).toFixed(4));
  return h("figure", ["medalhao", f != null && (cor ?? tom(Math.min(1, fracao) / alerta)), classe].filter(Boolean).join(" "),
    h("div", "medalhao-disco",
      s("svg", { viewBox: "-60 -60 120 120", class: "medalhao-anel", "aria-hidden": "true" },
        s("circle", { r: 58.5, class: "borda" }), s("circle", { r: 43.4, class: "borda" }),
        s("path", { d: anel, class: "risco" }), pintado),
      h("div", "medalhao-miolo", desenho,
        numero != null && h("span", "medalhao-numero", numero, unidade && h("span", "medalhao-unidade", unidade)))),
    h("figcaption", null, h("span", "medalhao-rotulo", rotulo), nota && h("span", "medalhao-nota", nota)));
}

export function medalhoes(...lista) {
  return h("div", "medalhoes", lista);
}

// --- a roseta: a flor de oito pétalas dos frisos; gira na velocidade de uma ventoinha -----------------

export function roseta(segundosPorVolta) {
  const petalas = Array.from({ length: 8 }, (_, i) => s("path", {
    d: "M0 -3.2 C 4.2 -7.5, 3.6 -15.5, 0 -17.5 C -3.6 -15.5, -4.2 -7.5, 0 -3.2 Z", transform: `rotate(${i * 45})`, class: "petala",
  }));
  const svg = s("svg", { viewBox: "-20 -20 40 40", class: "roseta", "aria-hidden": "true" },
    s("g", { class: segundosPorVolta ? "gira" : null }, petalas, s("circle", { r: 3.2, class: "miolo" })));
  if (segundosPorVolta) svg.style.setProperty("--volta", `${segundosPorVolta.toFixed(2)}s`);
  return svg;
}

// --- a crepidoma das zonas: os degraus do templo em 3D, um degrau de mármore por zona ---------------
// A zona de base (core) é o degrau de baixo; no piso de cada um, um ponto por container. Os degraus
// sobem um a um ao entrar, a escada respira devagar, e a zona com problema escorrega para o lado. A
// legenda ao lado é a parte que se lê e se toca; os degraus repetem o toque.

export function crepidoma(zonas, aoEscolher) {
  const n = zonas.length;
  const pares = zonas.map((z, i) => {
    const ruins = z.problemas.length;
    const pontos = h("span", "laje-pontos", Array.from({ length: z.total }, (_, k) => h("i", k < z.total - ruins ? "ok" : "ruim")));
    const laje = h("span", `laje${ruins ? " fora" : ""}`, h("span", "laje-face", pontos), h("span", "laje-frente"), h("span", "laje-lado"));
    laje.style.setProperty("--i", i);
    const linha = h("button", `crepidoma-zona${ruins ? " fora" : ""}`,
      h("i", ruins ? "led ruim" : "led ok"),
      h("span", "crepidoma-nome", z.zona),
      h("span", "crepidoma-conta", `${z.total - ruins}/${z.total}`),
      ruins > 0 && h("span", "crepidoma-problema", z.problemas.join(", ")));
    linha.type = "button";
    linha.setAttribute("aria-label", `zona ${z.zona}: ${z.total - ruins} de ${z.total} no ar${ruins ? `; com problema: ${z.problemas.join(", ")}` : ""}`);
    linha.style.setProperty("--i", i);
    // tocar a laje ou a linha da legenda abre a zona; passar por uma acende a outra
    for (const el of [laje, linha]) {
      if (aoEscolher) el.addEventListener("click", () => aoEscolher(z.zona));
      el.addEventListener("pointerenter", () => { laje.classList.add("acesa"); linha.classList.add("acesa"); });
      el.addEventListener("pointerleave", () => { laje.classList.remove("acesa"); linha.classList.remove("acesa"); });
    }
    return [laje, linha];
  });
  const cena = h("div", "crepidoma-cena", h("div", "crepidoma-pilha", pares.map(([laje]) => laje)));
  cena.setAttribute("aria-hidden", "true");
  cena.style.setProperty("--n", n);
  // a legenda lê de cima para baixo, como a pilha: a zona do topo primeiro
  return h("div", "crepidoma", cena, h("div", "crepidoma-legenda", pares.map(([, linha]) => linha).reverse()));
}

// --- o relógio de sol da agenda: 24 h, a sombra na hora de agora e as próximas vezes pintadas ---------

function ponto(a, raio) {
  return [r2(50 + raio * Math.cos((a * Math.PI) / 180)), r2(50 + raio * Math.sin((a * Math.PI) / 180))];
}
const anguloDa = (data) => ((data.getHours() + data.getMinutes() / 60) / 24) * 360 - 90;

export function relogioDeSol(agendamentos, girando) {
  const agora = new Date();
  const proximas = agendamentos.filter((a) => a.ativo && a.proxima && a.proxima - agora.getTime() < 24 * 3600_000)
    .sort((a, b) => a.proxima - b.proxima);
  const a = anguloDa(agora);
  const [x1, y1] = ponto(a - 7, 40);
  const [x2, y2] = ponto(a + 7, 40);
  const [px, py] = ponto(a, 44);
  return s("svg", { viewBox: "0 0 100 100", class: "relogio", role: "img",
    "aria-label": `agora, ${agora.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}; ${proximas.length} nas próximas 24 h` },
    s("circle", { cx: 50, cy: 50, r: 47, class: "borda" }),
    s("g", { transform: "translate(50 50)" }, s("path", { d: caminhoMeandroCircular(46.5, 1.9), class: "risco" })),
    s("circle", { cx: 50, cy: 50, r: 34.5, class: "borda" }),
    Array.from({ length: 24 }, (_, i) => {
      const ang = (i / 24) * 360 - 90;
      const [ax, ay] = ponto(ang, i % 6 === 0 ? 24 : 29);
      const [bx, by] = ponto(ang, 33);
      return s("line", { x1: ax, y1: ay, x2: bx, y2: by, class: i % 6 === 0 ? "hora forte" : "hora" });
    }),
    s("g", { class: girando ? "sombra girando" : "sombra" },
      s("path", { d: `M50 50 L${x1} ${y1} A40 40 0 0 1 ${x2} ${y2} Z`, class: "cunha" }),
      s("line", { x1: 50, y1: 50, x2: px, y2: py, class: "gnomon" })),
    // os numerais vêm depois da sombra, para ficar por cima do ponteiro
    [0, 6, 12, 18].map((hh) => {
      const [x, y] = ponto((hh / 24) * 360 - 90, 17);
      return s("text", { x, y: y + 2.4, class: "numeral", "text-anchor": "middle" }, String(hh));
    }),
    proximas.map((ag, i) => {
      const [x, y] = ponto(anguloDa(new Date(ag.proxima)), 39.5);
      return s("circle", { cx: x, cy: y, r: i === 0 ? 3.4 : 2.3, class: i === 0 ? "vez proxima" : "vez" });
    }),
    s("circle", { cx: 50, cy: 50, r: 2.4, class: "centro" }));
}

// --- a entrada: a construção do templo, como numa prancha de arquiteto --------------------------------
// Três atos. A geometria, em linha fina: o chão, o eixo, um quadrado e o arco do compasso (centrado no
// meio da base dele) que estende o quadrado até o retângulo de ouro, que é o corpo da fachada. O templo
// a tinta: os três degraus (a crepidoma), as seis colunas subindo do centro para fora, os capitéis, a
// arquitrave, o friso com os tríglifos, a cornija e o frontão, cujas duas linhas se encontram no topo.
// O acabamento: a geometria recua para um fantasma, como num desenho técnico. Quando a senha está certa,
// o tímpano se pinta de azul egípcio, como eram os templos (as classes vêm do app.js).

const traco = (d, classe, atraso, duracao) =>
  s("path", { d, class: `traco ${classe}`.trim(), pathLength: 1, "data-atraso": atraso, "data-duracao": duracao });

const COLUNAS = [82, 113.2, 144.4, 175.6, 206.8, 238];

export function templo() {
  // o quadrado de lado 136 sobre a base (50 a 186), o raio do meio da base (118, 200) até o canto de cima
  // (186, 64) e o arco desse raio, que cai na base em 270: 220 por 136 é a razão de ouro
  const raio = Math.hypot(186 - 118, 200 - 64);
  const geometria = s("g", { class: "geometria" },
    traco("M20 200 H300", "guia", 0, 0.8),
    traco("M160 214 V22", "guia", 0.15, 0.8),
    traco("M50 200 V64 H186 V200", "guia", 0.4, 0.9),
    traco("M118 200 L186 64", "guia", 0.95, 0.4),
    traco(`M186 64 A${raio.toFixed(2)} ${raio.toFixed(2)} 0 0 1 ${(118 + raio).toFixed(2)} 200`, "guia compasso", 1.15, 0.8),
    traco("M186 64 H270 V200", "guia", 1.7, 0.5),
    s("circle", { cx: 118, cy: 200, r: 1.7, class: "pivo" }),
    s("circle", { cx: 186, cy: 64, r: 1.3, class: "pivo" }));
  // as colunas sobem do centro para fora: as duas do meio, depois as do lado, depois as das pontas
  const ordem = (cx) => [144.4, 175.6].includes(cx) ? 0 : [113.2, 206.8].includes(cx) ? 1 : 2;
  const colunas = COLUNAS.map((cx) => {
    const a = 1.95 + ordem(cx) * 0.1;
    return s("g", { class: "coluna" },
      traco(`M${cx - 6.5} 164 L${cx - 5.3} 103`, "pedra", a, 0.6),
      traco(`M${cx + 6.5} 164 L${cx + 5.3} 103`, "pedra", a, 0.6),
      s("path", { d: `M${cx - 2.2} 162 L${cx - 1.8} 105 M${cx + 2.2} 162 L${cx + 1.8} 105`, class: "estria" }),
      traco(`M${cx - 5.3} 103 Q${cx - 8} 101.5 ${cx - 8} 100 H${cx + 8} Q${cx + 8} 101.5 ${cx + 5.3} 103 M${cx - 8} 100 V97 H${cx + 8} V100`, "pedra capitel", a + 0.5, 0.35));
  });
  // os tríglifos: sobre cada coluna e no meio de cada vão
  const xs = COLUNAS.flatMap((x, i) => (i ? [(x + COLUNAS[i - 1]) / 2, x] : [x]));
  const triglifos = s("path", { d: xs.map((x) => `M${(x - 2).toFixed(1)} 82 V72 M${x.toFixed(1)} 82 V72 M${(x + 2).toFixed(1)} 82 V72`).join(" "), class: "triglifos" });
  const pedra = s("g", { class: "obra" },
    traco("M50 200 V188 H270 V200", "pedra", 1.75, 0.45),
    traco("M58 188 V176 H262 V188", "pedra", 1.85, 0.45),
    traco("M66 176 V164 H254 V176", "pedra", 1.95, 0.45),
    colunas,
    traco("M58 97 H262 V84 H58 Z", "pedra", 2.55, 0.55),
    traco("M58 84 V70 H262 V84", "pedra", 2.65, 0.5),
    triglifos,
    traco("M50 70 H270 V64 H50 Z", "pedra", 2.75, 0.5),
    s("path", { d: "M64 61 L160 40 L256 61 Z", class: "timpano" }),
    traco("M50 64 L160 36", "pedra", 2.95, 0.5),
    traco("M270 64 L160 36", "pedra", 2.95, 0.5),
    s("path", { d: "M66 60.4 L160 41.6 L254 60.4 Z", class: "timpano-tinta" }));
  return s("svg", { viewBox: "14 18 292 200", class: "templo", role: "img", "aria-label": "a fachada de um templo grego, desenhada a partir do retângulo de ouro" },
    geometria, pedra);
}

// cada traço começa a se desenhar no seu atraso (em segundos, do mais antigo ao mais novo)
export function prepararTracos(svg, escala = 1) {
  for (const el of svg.querySelectorAll("[data-atraso]")) {
    el.style.setProperty("--atraso", `${(+el.dataset.atraso * escala).toFixed(2)}s`);
    if (el.dataset.duracao) el.style.setProperty("--duracao", `${(+el.dataset.duracao * escala).toFixed(2)}s`);
  }
  return svg;
}
