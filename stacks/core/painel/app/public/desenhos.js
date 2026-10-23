// Os desenhos do painel, no mundo da policromia (os templos gregos eram pintados): o meandro, que
// também mede; as mãos da Criação de Adão na entrada, impressas por pontos; os medalhões dos números; a
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

// --- a entrada: uma gravura clássica, impressa por pontos ----------------------------------------------
// A imagem é uma gravura antiga (a origem de cada uma está em gravuras/ORIGEM.txt) guardada só como tinta:
// a cor vem do CSS (--gravura: azul egípcio de dia, osso à noite). Ao abrir, ela se imprime por um
// pontilhado ordenado (a matriz de Bayer 8×8, em pontos de 2 px) que se adensa da tinta mais escura para a
// mais clara, de cima para baixo ou das bordas para um centro; ao entrar no painel, o mesmo pontilhado a
// desfaz. Opções: canais (a tinta no cinza e o recorte no alfa, em vez de só o alfa), inverterNoEscuro (à
// noite pinta o papel dentro do recorte: o claro fica claro), densidade (o expoente da tinta de dia: abaixo
// de 1 adensa os meios-tons), centro (a fração da largura para onde a impressão converge) e modo "buril"
// (em vez dos pontos, a imagem aparece em passadas finas na direção da hachura, descendo pela chapa, cada
// uma começando numa hora, como linhas gravadas uma a uma; é o das vinhetas).

const BAYER = [0, 32, 8, 40, 2, 34, 10, 42, 48, 16, 56, 24, 50, 18, 58, 26, 12, 44, 4, 36, 14, 46, 6, 38, 60, 28, 52, 20, 62, 30, 54, 22,
  3, 35, 11, 43, 1, 33, 9, 41, 51, 19, 59, 27, 49, 17, 57, 25, 15, 47, 7, 39, 13, 45, 5, 37, 63, 31, 55, 23, 61, 29, 53, 21];

// as gravuras na tela: quando a janela muda de tamanho ou de tema, as que estão na página se refazem já
// prontas, e as que saíram dela saem da lista (as vinhetas se refazem a cada atualização da tela)
const gravuras = new Set();
const refazerGravuras = () => { for (const refazer of gravuras) refazer(); };
addEventListener("resize", refazerGravuras);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", refazerGravuras);

// um número de 0 a 1 que é sempre o mesmo para o mesmo n (a hora de cada passada do buril)
const sorteio = (n) => {
  let x = Math.imul(n ^ 0x9e3779b9, 0x85ebca6b);
  x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
  return ((x ^ (x >>> 16)) >>> 0) / 4294967296;
};

export function gravura(src, rotulo, { canais = false, inverterNoEscuro = false, densidade = 1, centro = null, modo = "pontos" } = {}) {
  const tela = document.createElement("canvas");
  tela.className = "gravura";
  tela.setAttribute("role", "img");
  tela.setAttribute("aria-label", rotulo);
  const imagem = new Image(); // baixada só quando a gravura for para a tela
  let estado = null;
  let quadro = 0;

  // a máscara no tamanho da tela (na densidade do aparelho) e a ordem em que cada ponto aparece
  async function preparar() {
    if (!imagem.src) imagem.src = src;
    await imagem.decode();
    const dpr = Math.min(devicePixelRatio || 1, 3);
    const w = Math.max(1, Math.round(tela.getBoundingClientRect().width * dpr));
    const h = Math.max(1, Math.round((w * imagem.naturalHeight) / imagem.naturalWidth));
    tela.width = w;
    tela.height = h;
    const ctx = tela.getContext("2d", { willReadFrequently: true });
    // a hachura é fina: reduzir ou ampliar com o filtro simples a amolece e faz moiré
    ctx.imageSmoothingQuality = "high";
    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(imagem, 0, 0, w, h);
    const fonte = ctx.getImageData(0, 0, w, h).data;
    const alfa = new Uint8ClampedArray(w * h);
    const ordem = new Float32Array(w * h);
    const passo = Math.max(1, Math.round(2 * dpr));
    const papel = inverterNoEscuro && matchMedia("(prefers-color-scheme: dark)").matches;
    // o buril: passadas finas (1,4 px) a 35°, a direção da hachura, cada uma andando ao longo de si mesma; o
    // gravador desce pela chapa, e num mesmo trecho as linhas entram em horas diferentes
    const espaco = 1.4 * dpr, cos = Math.cos(-0.61), sen = Math.sin(-0.61);
    const comprimento = w * Math.abs(cos) + h * Math.abs(sen) || 1;
    for (let y = 0; y < h; y++) {
      const linha = ((y / passo) | 0) % 8;
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        if (canais) {
          const tinta = fonte[i * 4], recorte = fonte[i * 4 + 3];
          alfa[i] = ((papel ? 255 - tinta : 255 * (tinta / 255) ** densidade) * recorte) / 255;
        } else alfa[i] = fonte[i * 4 + 3];
        if (modo === "buril") {
          const passada = Math.floor((x * sen + y * cos) / espaco);
          const aoLongo = (x * cos - y * sen + h * Math.abs(sen)) / comprimento;
          ordem[i] = (y / h) * 0.45 + sorteio(passada) * 0.35 + aoLongo * 0.2;
          continue;
        }
        // de cima para baixo, ou das bordas para o centro (as mãos vão uma ao encontro da outra)
        const caminho = centro == null ? y / h : 1 - Math.abs(x / w - centro) / Math.max(centro, 1 - centro);
        ordem[i] = (BAYER[linha * 8 + (((x / passo) | 0) % 8)] / 64) * 0.5 + (1 - alfa[i] / 255) * 0.2 + caminho * 0.3;
      }
    }
    const [r, g, b] = (getComputedStyle(tela).color.match(/\d+(\.\d+)?/g) ?? [0, 0, 0]).map(Number);
    estado = { ctx, w, h, alfa, ordem, cor: [r, g, b], saida: ctx.createImageData(w, h) };
    gravuras.add(refazer);
  }

  // os pontos cuja ordem já passou de t aparecem com a tinta deles
  function pintar(t) {
    const { ctx, w, h, alfa, ordem, cor, saida } = estado;
    const d = saida.data;
    d.fill(0);
    for (let i = 0; i < w * h; i++) {
      if (alfa[i] && ordem[i] <= t) {
        d[i * 4] = cor[0];
        d[i * 4 + 1] = cor[1];
        d[i * 4 + 2] = cor[2];
        d[i * 4 + 3] = alfa[i];
      }
    }
    ctx.putImageData(saida, 0, 0);
  }

  // ja: quanto da animação já passou (a cópia de uma gravura que a tela refez no meio continua dali)
  function animar(de, ate, ms, ja = 0) {
    cancelAnimationFrame(quadro);
    return new Promise((pronto) => {
      const inicio = performance.now() - ja;
      const passo = (agora) => {
        const x = Math.min(1, (agora - inicio) / ms);
        // o buril anda num ritmo só, como a mão; a impressão por pontos acelera e assenta
        const suave = modo === "buril" ? x : x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2;
        pintar(de + (ate - de) * suave);
        if (x < 1) quadro = requestAnimationFrame(passo);
        else pronto();
      };
      quadro = requestAnimationFrame(passo);
    });
  }

  const reduzido = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  tela.imprimir = async (ms = 1900, ja = 0) => {
    const pedido = performance.now() - ja;
    await preparar();
    if (reduzido()) pintar(1.1);
    else await animar(-0.05, 1.1, ms, performance.now() - pedido);
  };
  tela.desfazer = async (ms = 650) => {
    if (!estado || reduzido()) return;
    await animar(1.1, -0.05, ms);
  };
  // já pronta, sem a impressão (a vinheta que já se desenhou nesta sessão)
  tela.mostrar = async () => {
    await preparar();
    pintar(1.1);
  };
  async function refazer() {
    if (!tela.isConnected) return gravuras.delete(refazer);
    await preparar();
    pintar(1.1);
  }
  return tela;
}

// cada traço começa a se desenhar no seu atraso (em segundos, do mais antigo ao mais novo)
export function prepararTracos(svg, escala = 1) {
  for (const el of svg.querySelectorAll("[data-atraso]")) {
    el.style.setProperty("--atraso", `${(+el.dataset.atraso * escala).toFixed(2)}s`);
    if (el.dataset.duracao) el.style.setProperty("--duracao", `${(+el.dataset.duracao * escala).toFixed(2)}s`);
  }
  return svg;
}

// --- a esfera armilar da rede: um anel por alcance, do servidor para fora, e um ponto em cada anel por
// porta aberta nele; o eixo e o servidor no meio ficam parados. Os anéis se desenham e os pontos chegam
// na primeira vez; a esfera gira devagar e, quando a tela se refaz, continua do ângulo em que estava
const INCLINACOES = [[0, 68], [28, 74], [-24, 64], [58, 72], [-58, 70]];
const GIRO_MS = 90_000;

export function esferaArmilar(aneis, rotulo) {
  const giro = h("div", "esfera-giro");
  giro.style.setProperty("--ja", `${-(performance.now() % GIRO_MS)}ms`);
  aneis.forEach((anel, i) => {
    const raio = 22 + i * 10;
    const [z, x] = INCLINACOES[i % INCLINACOES.length];
    const pontos = Array.from({ length: anel.portas }, (_, k) => {
      const a = ((k + 0.5) / anel.portas) * 2 * Math.PI + i * 0.7;
      return s("circle", { class: `porta${anel.exposto ? " exposta" : ""}`, cx: r2(raio * Math.cos(a)), cy: r2(raio * Math.sin(a)), r: 1.9,
        "data-atraso": (0.35 + i * 0.16 + 0.5 + k * 0.03).toFixed(2) });
    });
    const plano = h("div", "anel",
      prepararTracos(s("svg", { viewBox: `${-raio - 3} ${-raio - 3} ${2 * raio + 6} ${2 * raio + 6}`, "aria-hidden": "true" },
        s("circle", { class: "traco", r: raio, pathLength: 1, "data-atraso": (0.35 + i * 0.16).toFixed(2), "data-duracao": "0.9" }), pontos)));
    plano.style.setProperty("--raio", `${raio}px`);
    plano.style.setProperty("--z", `${z}deg`);
    plano.style.setProperty("--x", `${x}deg`);
    giro.append(plano);
  });
  const lado = 22 + (aneis.length - 1) * 10 + 8;
  const eixo = prepararTracos(s("svg", { class: "esfera-eixo", viewBox: `${-lado} ${-lado} ${2 * lado} ${2 * lado}`, "aria-hidden": "true" },
    s("path", { class: "traco", d: `M0 ${-lado + 2}V${lado - 2}`, pathLength: 1, transform: "rotate(-16)", "data-atraso": "0", "data-duracao": "0.5" }),
    s("circle", { class: "servidor", r: 4.2 })));
  const esfera = h("div", "esfera", giro, eixo);
  esfera.setAttribute("role", "img");
  esfera.setAttribute("aria-label", rotulo);
  esfera.style.setProperty("--lado", `${2 * lado}px`);
  return esfera;
}

// --- a prancha do servidor: o instrumento gravado do Início, como numa prancha científica antiga. Um anel
// por leitura, de fora para dentro, com as bordas finas e a tinta em hachura pintada até o valor, desde o
// zero no alto; as letras gregas no eixo do zero, que a legenda embaixo explica; a graduação em volta e a
// estrela no meio. Na primeira vez a graduação se desenha em volta e os anéis se pintam; nas outras, a
// tinta anda do valor anterior até o novo
const ultimasLeituras = new Map();
let pranchas = 0;

export function prancha(aneis, rotulo) {
  const id = `hachura-${++pranchas}`;
  const padroes = ["azul", "ocre", "cinabrio"].map((t) => s("pattern", { id: `${id}-${t}`, patternUnits: "userSpaceOnUse", width: 2.6, height: 2.6, patternTransform: "rotate(35)" },
    s("line", { x1: 0, y1: 0, x2: 0, y2: 2.6, class: `hachura ${t}` })));
  let graduacao = "";
  for (let k = 0; k < 72; k++) {
    const a = (k * 5 * Math.PI) / 180 - Math.PI / 2, dentro = k % 6 ? 89.5 : 85.5;
    graduacao += `M${r2(dentro * Math.cos(a))} ${r2(dentro * Math.sin(a))}L${r2(93 * Math.cos(a))} ${r2(93 * Math.sin(a))}`;
  }
  const centro = Array.from({ length: 16 }, (_, k) => {
    const a = (k * Math.PI) / 8 - Math.PI / 2, r = k % 2 ? 4.2 : 11;
    return `${k ? "L" : "M"}${r2(r * Math.cos(a))} ${r2(r * Math.sin(a))}`;
  }).join("") + "Z";
  const partes = aneis.map((anel, i) => {
    const r = 76 - i * 11, f = limite(anel.fracao);
    const antes = ultimasLeituras.get(anel.letra);
    ultimasLeituras.set(anel.letra, f);
    const valor = s("circle", { r, pathLength: 1, transform: "rotate(-90)", stroke: `url(#${id}-${anel.tom})`,
      class: `valor${antes != null && Math.abs(antes - f) > 0.004 ? " andando" : ""}`, "data-atraso": (0.95 + i * 0.12).toFixed(2) });
    valor.style.setProperty("--f", f.toFixed(4));
    if (antes != null) valor.style.setProperty("--de", antes.toFixed(4));
    return [
      s("circle", { r: r + 3.7, class: "traco borda", pathLength: 1, "data-atraso": (0.4 + i * 0.07).toFixed(2), "data-duracao": "0.7" }),
      s("circle", { r: r - 3.7, class: "traco borda", pathLength: 1, "data-atraso": (0.45 + i * 0.07).toFixed(2), "data-duracao": "0.7" }),
      valor,
      s("text", { x: -3.4, y: r2(-r + 2.3), class: "letra", "text-anchor": "end", "data-atraso": (1.1 + i * 0.1).toFixed(2) }, anel.letra),
    ];
  });
  const inicio = 76 - (aneis.length - 1) * 11 - 6;
  const svg = prepararTracos(s("svg", { class: "instrumento", viewBox: "-100 -100 200 200", role: "img", "aria-label": rotulo },
    s("defs", null, padroes),
    s("path", { class: "traco graduacao", d: graduacao, pathLength: 1, "data-atraso": "0", "data-duracao": "1.2" }),
    s("circle", { class: "traco", r: 93, pathLength: 1, "data-atraso": "0.1", "data-duracao": "1.1" }),
    s("path", { class: "traco indice", d: `M0 ${-inicio}V-97`, pathLength: 1, "data-atraso": "0.3", "data-duracao": "0.5" }),
    partes,
    s("path", { class: "traco estrela", d: centro, pathLength: 1, "data-atraso": "0.6", "data-duracao": "0.9" }),
    s("circle", { class: "ponto", r: 1.3, "data-atraso": "1.3" })));
  return svg;
}
