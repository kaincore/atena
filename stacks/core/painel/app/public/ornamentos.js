// O traço do sistema: o que se desenha quando algo acontece, no lugar onde acontece. A lista vazia ganha
// uma vinheta de gravura antiga, gravada a buril, e a lista longa termina com um fecho de livro, que se
// desenha quando você chega ao fim; o que caiu ganha uma rachadura, como o reboco do afresco; e o gesto que
// você faz deixa um traço em volta do que você tocou (o louro ao aprovar, o círculo de pena ao reiniciar,
// os raios ao ligar o PC). A hachura de quem carrega fica no CSS (o esqueleto e o .carregando).
//
// Cada desenho tem uma chave com o estado dele e corre uma vez por sessão; depois aparece pronto, porque as
// telas se refazem a cada atualização. A cópia que chega enquanto ele ainda se desenha (a tela se refez no
// meio) continua de onde ele estava. A decisão sai quando o desenho entra na página (um MutationObserver),
// antes de o navegador pintar: não pisca, e vale para qualquer caminho que o ponha lá. Com
// prefers-reduced-motion, tudo aparece pronto, e os gestos não se desenham.
import { gravura, prepararTracos, s } from "./desenhos.js";

const reduzido = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function h(tag, classe, ...filhos) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  for (const f of filhos.flat(Infinity)) if (f != null && f !== false) el.append(f instanceof Node ? f : String(f));
  return el;
}

// --- quando desenhar --------------------------------------------------------------------------------

const desenhados = new Map(); // a chave e a hora em que o desenho começou
const DURA = 2600; // o desenho mais longo (o fecho, a esfera); passado isso, a cópia nova vem pronta

function correr(el, passou = 0) {
  if (!passou) desenhados.set(el.dataset.desenho, performance.now());
  el.classList.remove("a-desenhar");
  el.style.setProperty("--passou", `${Math.round(passou)}ms`);
  if (el.imprimir) el.imprimir(1700, passou);
  else el.classList.add("desenhando");
}

// pronto, ou continuando: o que já começou há pouco segue do mesmo ponto
function retomar(el) {
  const passou = performance.now() - desenhados.get(el.dataset.desenho);
  if (passou < DURA && !reduzido()) correr(el, passou);
  else {
    el.classList.remove("a-desenhar");
    el.mostrar?.();
  }
}

const aoVer = new IntersectionObserver((entradas) => {
  for (const e of entradas) {
    if (!e.isIntersecting) continue;
    aoVer.unobserve(e.target);
    if (desenhados.has(e.target.dataset.desenho)) retomar(e.target);
    else correr(e.target);
  }
}, { rootMargin: "0px 0px -6% 0px" });

function decidir(el) {
  el.dataset.decidido = "";
  if (reduzido()) el.mostrar?.();
  else if (desenhados.has(el.dataset.desenho)) retomar(el);
  else if (el.dataset.quando === "visivel") {
    el.classList.add("a-desenhar");
    aoVer.observe(el);
  } else correr(el);
}

// cada desenho é decidido na primeira vez que entra na página, seja na tela nova, seja na tela que foi
// montada antes por trás e guardada (as da barra)
new MutationObserver((mudancas) => {
  for (const m of mudancas) for (const n of m.addedNodes) {
    if (!(n instanceof Element)) continue;
    if (n.matches("[data-desenho]:not([data-decidido])")) decidir(n);
    for (const el of n.querySelectorAll("[data-desenho]:not([data-decidido])")) decidir(el);
  }
}).observe(document.documentElement, { childList: true, subtree: true });

// marca um desenho: ele corre na primeira vez que a chave aparece (ou que ele aparece na tela, com
// quando = "visivel") e, nas outras, já vem pronto
export function desenhavel(el, chave, quando) {
  el.dataset.desenho = chave;
  if (quando) el.dataset.quando = quando;
  if (el.isConnected) queueMicrotask(() => { if (!("decidido" in el.dataset)) decidir(el); });
  return el;
}

// --- o vazio: uma vinheta de gravura antiga, as aves do livro de Pierre Belon de 1555 (gravuras/vinhetas,
// a origem em gravuras/ORIGEM.txt): a coruja vigia, o galo canta as horas, a andorinha constrói e a pega guarda

// largura sobre altura de cada vinheta: o lugar dela fica reservado antes de a imagem chegar
const PROPORCOES = { coruja: 330 / 504, galo: 330 / 299, andorinha: 330 / 215, pega: 330 / 197 };

export function vazio(texto, figura) {
  const vinheta = gravura(`/gravuras/vinhetas/${figura}.webp`, "", { modo: "buril" });
  vinheta.classList.add("vinheta");
  vinheta.style.setProperty("--proporcao", PROPORCOES[figura] ?? 1);
  vinheta.removeAttribute("role");
  vinheta.removeAttribute("aria-label");
  vinheta.setAttribute("aria-hidden", "true");
  desenhavel(vinheta, `vazio|${figura}|${texto}`);
  return h("div", "vazio", vinheta, h("p", "fraco", texto));
}

// --- o fecho de livro: o enfeite de fim de capítulo, no fim de uma lista longa ------------------------

const FECHO_LADO = [
  ["M4.6 0C11 -5 18 -5.5 23 -1.5C27 1.5 32 4 37 2.4C40.6 1.2 42.4 -1.8 40.8 -3.8C39.5 -5.3 37 -4.2 37.6 -2.5", 0.3, 1.0],
  ["M13.5 -3.6C15 -7.6 19 -9 22 -7.6C19.6 -5.6 16.6 -4 13.5 -3.6Z", 0.85, 0.45],
  ["M28.5 3C30 6.2 33.6 7.4 36 6.2C34 4.6 31.4 3.4 28.5 3Z", 1.05, 0.45],
  ["M46 0H57", 1.2, 0.4],
];

export function fecho(chave) {
  const lado = (espelho) => s("g", espelho ? { transform: "scale(-1 1)" } : null,
    FECHO_LADO.map(([d, atraso, duracao]) => s("path", { class: "traco", d, pathLength: 1, "data-atraso": atraso, "data-duracao": duracao })));
  const svg = prepararTracos(s("svg", { class: "fecho", viewBox: "-60 -10 120 20", "aria-hidden": "true" },
    s("path", { class: "traco", d: "M0 -4.6L4 0L0 4.6L-4 0Z", pathLength: 1, "data-atraso": 0, "data-duracao": 0.5 }),
    s("circle", { class: "ponto", r: 1.1, "data-atraso": 0.35 }),
    lado(false), lado(true)));
  return desenhavel(h("li", "fecho-item", svg), `fecho|${chave}`, "visivel");
}

// --- a rachadura: o que caiu racha como o reboco do afresco, a partir da borda de cima da linha dele; a
// forma vem do nome (é sempre a mesma) ---

function sorteador(texto) {
  let x = 2166136261;
  for (const c of texto) x = Math.imul(x ^ c.codePointAt(0), 16777619);
  return () => {
    x = (Math.imul(x, 1664525) + 1013904223) >>> 0;
    return x / 4294967296;
  };
}

function veio(sorte, x, y, angulo, passos, tamanho) {
  let d = `M${x.toFixed(1)} ${y.toFixed(1)}`;
  const curva = [];
  for (let i = 0; i < passos; i++) {
    angulo = Math.max(-1.1, Math.min(1.1, angulo + (sorte() - 0.5) * 0.9));
    const passo = tamanho * (0.7 + sorte() * 0.9);
    x += Math.cos(angulo) * passo;
    y += Math.sin(angulo) * passo * 0.75;
    if (y < 2 || y > 46) {
      y = Math.max(2, Math.min(46, y));
      angulo = -angulo;
    }
    d += ` L${x.toFixed(1)} ${y.toFixed(1)}`;
    curva.push([x, y, angulo]);
  }
  return [d, curva];
}

export function rachadura(nome) {
  const sorte = sorteador(nome);
  const [tronco, curva] = veio(sorte, 4 + sorte() * 30, 1, 0.55, 14, 11);
  const galhos = [4, 9].map((i) => {
    const [x, y, a] = curva[i];
    return veio(sorte, x, y, a + (sorte() < 0.5 ? 1 : -1) * 0.9, 3, 7)[0];
  });
  const svg = prepararTracos(s("svg", { class: "rachadura", viewBox: "0 0 240 48", preserveAspectRatio: "xMinYMid meet", "aria-hidden": "true" },
    s("path", { class: "traco", d: tronco, pathLength: 1, "data-atraso": 0.1, "data-duracao": 0.9 }),
    galhos.map((d, i) => s("path", { class: "traco", d, pathLength: 1, "data-atraso": 0.45 + i * 0.3, "data-duracao": 0.35 }))));
  return desenhavel(svg, `racha|${nome}`);
}

// --- o gesto: o traço em volta do que você tocou, quando a ação dá certo ----------------------------------

const GESTOS = {
  "aprovacoes.decidir": (p) => (p.decisao === "aprovar" ? "louro" : null),
  "app.publicar": () => "louro",
  "servico.reiniciar": () => "circulo",
  "app.reiniciar": () => "circulo",
  "pc.reiniciar": () => "circulo",
  "pc.ligar": () => "raios",
};

// o último toque: a ação sai dele (o confirm() no meio não conta como toque)
let tocado = null;
addEventListener("click", (e) => { tocado = e.target instanceof Element ? e.target.closest("button, a, li") : null; }, true);
export function origemDoGesto() {
  const t = tocado;
  tocado = null;
  return t;
}

const MARGEM = 12;

// um ramo de louro em "(": a haste sobe por fora da borda e as folhas nascem nela, alternando os lados
function ramo(w, h, espelho) {
  const x = (v) => (espelho ? w + 2 * MARGEM - v : v);
  const base = [MARGEM + h * 0.32, MARGEM + h + 5], fora = MARGEM - 9, topo = [MARGEM + h * 0.32, MARGEM - 5];
  const c1 = [fora, MARGEM + h * 0.9], c2 = [fora, MARGEM + h * 0.1];
  const ponto = (t) => [0, 1].map((k) => (1 - t) ** 3 * base[k] + 3 * (1 - t) ** 2 * t * c1[k] + 3 * (1 - t) * t ** 2 * c2[k] + t ** 3 * topo[k]);
  const caminhos = [[`M${x(base[0])} ${base[1]}C${x(c1[0])} ${c1[1]} ${x(c2[0])} ${c2[1]} ${x(topo[0])} ${topo[1]}`, 0, 0.55]];
  const folhas = Math.max(5, Math.min(12, Math.round(h / 9)));
  const folha = Math.max(7, Math.min(12, h / 6));
  for (let i = 0; i < folhas; i++) {
    const t = 0.1 + (i / (folhas - 1)) * 0.82;
    const [px, py] = ponto(t), [qx, qy] = ponto(t + 0.02);
    const tangente = Math.atan2(qy - py, qx - px) + (i % 2 ? 0.75 : -0.75);
    const [tx, ty] = [px + Math.cos(tangente) * folha, py + Math.sin(tangente) * folha];
    const [nx, ny] = [-Math.sin(tangente) * folha * 0.3, Math.cos(tangente) * folha * 0.3];
    const [mx, my] = [(px + tx) / 2, (py + ty) / 2];
    caminhos.push([`M${x(px)} ${py}Q${x(mx + nx)} ${my + ny} ${x(tx)} ${ty}Q${x(mx - nx)} ${my - ny} ${x(px)} ${py}Z`, 0.3 + i * 0.07, 0.3]);
  }
  return caminhos;
}

// o círculo de pena: uma volta e um pouco, fechando para dentro (a mão não fecha o círculo no mesmo ponto)
function circulo(w, h) {
  const [cx, cy, rx, ry] = [w / 2 + MARGEM, h / 2 + MARGEM, w / 2 + 8, h / 2 + 7];
  const pontos = [];
  for (let k = 0; k <= 96; k++) {
    const t = k / 96, a = -2.5 + t * 2 * Math.PI * 1.07, f = 1.04 - t * 0.07;
    pontos.push(`${(cx + rx * f * Math.cos(a)).toFixed(1)} ${(cy + ry * f * Math.sin(a)).toFixed(1)}`);
  }
  return [[`M${pontos.join("L")}`, 0, 0.7]];
}

// os raios: vinte e quatro, longos e curtos, saindo da borda do alvo, um depois do outro em volta
function raios(w, h) {
  const [cx, cy, rx, ry] = [w / 2 + MARGEM, h / 2 + MARGEM, w / 2 + 3, h / 2 + 3];
  return Array.from({ length: 24 }, (_, k) => {
    const a = (k / 24) * 2 * Math.PI - Math.PI / 2, l = k % 2 ? 5 : 9;
    const [x0, y0, x1, y1] = [cx + rx * Math.cos(a), cy + ry * Math.sin(a), cx + (rx + l) * Math.cos(a), cy + (ry + l) * Math.sin(a)];
    return [`M${x0.toFixed(1)} ${y0.toFixed(1)}L${x1.toFixed(1)} ${y1.toFixed(1)}`, k * 0.02, 0.3];
  });
}

const FORMAS = { louro: (w, h) => [...ramo(w, h, false), ...ramo(w, h, true)], circulo, raios };
const SEGURA = { louro: 1100, circulo: 1800, raios: 1500 }; // o louro some logo depois de o pedido sair

function camada() {
  let c = document.getElementById("tracos");
  if (!c) {
    c = h("div");
    c.id = "tracos";
    c.setAttribute("aria-hidden", "true");
    document.body.append(c);
  }
  return c;
}

// o louro coroa algo que vai sair da tela (o pedido aprovado): a promessa só se cumpre quando ele termina de
// se desenhar, e quem chamou espera para refazer a tela; os outros não mudam o lugar de nada
export async function tracarGesto(nome, params, origem) {
  const tipo = GESTOS[nome]?.(params ?? {});
  if (!tipo || !origem?.isConnected || reduzido()) return;
  const alvo = tipo === "circulo" ? origem.closest(".item")?.querySelector(".item-nome") ?? origem
    : tipo === "raios" ? origem.closest(".modulo")?.querySelector(".medalhao-disco") ?? origem : origem;
  // o círculo vai em volta das letras do nome, não da coluna inteira
  const faixa = document.createRange();
  faixa.selectNodeContents(alvo);
  const caixa = tipo === "circulo" && alvo !== origem ? faixa.getBoundingClientRect() : alvo.getBoundingClientRect();
  if (!caixa.width || caixa.bottom < 0 || caixa.top > innerHeight) return;
  const [w, h] = [caixa.width, caixa.height];
  const svg = prepararTracos(s("svg", { class: `gesto ${tipo}`, width: w + 2 * MARGEM, height: h + 2 * MARGEM, viewBox: `0 0 ${w + 2 * MARGEM} ${h + 2 * MARGEM}` },
    FORMAS[tipo](w, h).map(([d, atraso, duracao]) => s("path", { class: "traco", d, pathLength: 1, "data-atraso": atraso, "data-duracao": duracao }))));
  svg.style.left = `${caixa.left + scrollX - MARGEM}px`;
  svg.style.top = `${caixa.top + scrollY - MARGEM}px`;
  camada().append(svg);
  requestAnimationFrame(() => svg.classList.add("desenhando"));
  setTimeout(() => svg.classList.add("some"), SEGURA[tipo]);
  setTimeout(() => svg.remove(), SEGURA[tipo] + 700);
  if (tipo === "louro") await new Promise((pronto) => setTimeout(pronto, 1000));
}
