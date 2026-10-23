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
import { gravura } from "./desenhos.js";

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
