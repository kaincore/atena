// Os desenhos do painel, no mundo da policromia (os templos gregos eram pintados): o meandro, que
// também mede; a coruja de Atena na entrada, em traço de gravura; os medalhões dos números; a
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

// --- a coruja de Atena, como nas moedas de Atenas: a cabeça de frente, o corpo de perfil, num ramo ----
// Traço de gravura, numa cor só. Desenha-se traço a traço ao abrir; fecha os olhos enquanto você
// digita a senha; inclina a cabeça quando a senha está errada e abre bem os olhos quando está certa
// (as classes vêm do app.js).

const tracar = (d, classe, atraso) => s("path", { d, class: `traco ${classe}`.trim(), pathLength: 1, "data-atraso": atraso });

function folha(x, y, angulo, comprimento, largura, atraso) {
  const L = comprimento, w = largura;
  return s("g", { transform: `translate(${x} ${y}) rotate(${angulo})` },
    tracar(`M0 0 C${r2(L * 0.3)} ${-w} ${r2(L * 0.72)} ${r2(-w * 0.8)} ${L} 0 C${r2(L * 0.72)} ${r2(w * 0.8)} ${r2(L * 0.3)} ${w} 0 0Z`, "folha", atraso),
    tracar(`M2 0 L${L - 3} 0`, "nervura fino", atraso + 0.08));
}

function olho(cx, cy, lado) {
  return s("g", { class: `olho olho-${lado}` },
    s("circle", { cx, cy, r: 9.2, class: "olho-disco traco", pathLength: 1, "data-atraso": 1.1 }),
    s("g", { class: "iris-grupo" },
      s("circle", { cx, cy, r: 6, class: "iris" }),
      s("circle", { cx, cy, r: 3.4, class: "pupila" }),
      s("circle", { cx: cx + 1.6, cy: cy - 1.6, r: 0.9, class: "brilho" })),
    s("path", { d: `M${cx - 9} ${cy + 1} Q${cx} ${cy + 6.5} ${cx + 9} ${cy + 1}`, class: "palpebra" }));
}

// pequenas escamas (as penas cobertas da asa) e as estrias do peito
const escamas = [[86, 124], [94, 123], [102, 126], [84, 136], [92, 135], [100, 138], [86, 148], [94, 148], [102, 151], [89, 160], [97, 161]]
  .map(([x, y]) => `M${x - 2.4} ${y - 1.2} L${x} ${y + 1.2} L${x + 2.4} ${y - 1.2}`).join(" ");
const estrias = [[118, 117], [126, 124], [120, 131], [129, 139], [122, 146], [130, 154], [121, 161], [128, 169]]
  .map(([x, y]) => `M${x} ${y} q1.4 2.8 0 5.6`).join(" ");
const pintas = [[90, 49], [100, 46], [110, 47], [119, 51], [84, 56], [125, 58], [95, 53], [113, 53]];

export function coruja() {
  const ramo = s("g", { class: "ramo" },
    tracar("M16 204 C 58 195, 120 199, 188 183", "galho", 0),
    folha(38, 200, -158, 23, 4.2, 0.1), folha(56, 198, 24, 22, 4, 0.16),
    folha(146, 193, -164, 21, 4, 0.22), folha(164, 189, 20, 23, 4.2, 0.28), folha(183, 184, -14, 19, 3.8, 0.34),
    tracar("M66.4 205 a3.6 2.8 0 1 0 7.2 0 a3.6 2.8 0 1 0 -7.2 0", "azeitona", 0.3),
    tracar("M150.6 198 a3.4 2.6 0 1 0 6.8 0 a3.4 2.6 0 1 0 -6.8 0", "azeitona", 0.36));
  const corpo = s("g", { class: "corpo" },
    // as costas (à esquerda), o peito (à direita, a ave olha para a direita), a asa dobrada e a cauda
    tracar("M75 98 C 60 120, 60 160, 82 179 C 92 188, 104 192, 114 192", "", 0.42),
    tracar("M133 98 C 148 118, 150 156, 135 176 C 129 184, 122 190, 114 192", "", 0.48),
    tracar("M80 108 C 98 114, 112 134, 112 156 C 112 172, 102 186, 88 198", "asa", 0.6),
    tracar(escamas, "escamas fino", 0.7),
    tracar("M99 172 L 86 200 M105 166 L 93 199 M109 158 L 101 195", "remiges fino", 0.78),
    tracar(estrias, "estrias fino", 0.82),
    tracar("M92 192 L 84 209 M98 193 L 92 211", "cauda", 0.86),
    tracar("M108 192 l -2 5 M111 193 l 0 5.5 M114 192 l 2 5 M118 190 l -1.5 5 M121 190 l .5 5.5 M124 189 l 2 4.5", "pes fino", 0.92));
  const cabeca = s("g", { class: "cabeca" },
    tracar("M72 76 C 71 52, 88 40, 104 40 C 120 40, 137 52, 136 76 C 135 94, 122 106, 104 106 C 86 106, 73 94, 72 76 Z", "", 0.95),
    tracar("M78 82 C 76 66, 86 58, 97 60 M130 82 C 132 66, 122 58, 111 60", "disco-facial fino", 1.02),
    tracar("M80 64 Q 93 57 103 70 M128 64 Q 115 57 105 70", "sobrancelhas", 1.06),
    pintas.map(([x, y]) => s("circle", { cx: x, cy: y, r: 0.85, class: "pinta" })),
    olho(92, 77, "esquerdo"), olho(116, 77, "direito"),
    s("path", { d: "M100.5 86 Q104 83 107.5 86 Q105.6 91 104 95 Q102.4 91 100.5 86 Z", class: "bico" }));
  return s("svg", { viewBox: "8 34 188 184", class: "coruja", role: "img", "aria-label": "a coruja de Atena num ramo de oliveira" },
    ramo, corpo, cabeca);
}

// cada traço começa a se desenhar no seu atraso (em segundos, do mais antigo ao mais novo)
export function prepararTracos(svg, escala = 1) {
  for (const el of svg.querySelectorAll("[data-atraso]")) el.style.setProperty("--atraso", `${(+el.dataset.atraso * escala).toFixed(2)}s`);
  return svg;
}
