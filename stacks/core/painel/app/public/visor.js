// O visor do aparelho e os desenhos técnicos: números em 7 segmentos, os visores vivos de cada tela
// (desenhados a partir dos dados de verdade) e a vista explodida das zonas.
// Tudo em SVG montado elemento a elemento; o movimento vem do CSS e para com prefers-reduced-motion.

const SVG = "http://www.w3.org/2000/svg";

function s(tag, atributos, ...filhos) {
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

// --- 7 segmentos (os apagados ficam visíveis por trás, como num visor de calculadora) ---------------

const SEGMENTOS = {
  0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abcdfg",
  "-": "g", " ": "", A: "abcefg", C: "adef", E: "adefg", F: "aefg", H: "bcefg", L: "def", P: "abefg",
  b: "cdefg", d: "bcdeg", h: "cefg", n: "ceg", o: "cdeg", r: "eg", t: "defg", u: "cde",
};
const L = 1.5, R = 10.5, T = 1.5, M = 11, B = 20.5, MEIO = 1.2, FOLGA = 0.55;

function horizontal(x1, x2, y) {
  const a = x1 + FOLGA, z = x2 - FOLGA;
  return `${a},${y} ${a + MEIO},${y - MEIO} ${z - MEIO},${y - MEIO} ${z},${y} ${z - MEIO},${y + MEIO} ${a + MEIO},${y + MEIO}`;
}
function vertical(x, y1, y2) {
  const a = y1 + FOLGA, z = y2 - FOLGA;
  return `${x},${a} ${x + MEIO},${a + MEIO} ${x + MEIO},${z - MEIO} ${x},${z} ${x - MEIO},${z - MEIO} ${x - MEIO},${a + MEIO}`;
}
const FORMAS = {
  a: horizontal(L, R, T), g: horizontal(L, R, M), d: horizontal(L, R, B),
  f: vertical(L, T, M), b: vertical(R, T, M), e: vertical(L, M, B), c: vertical(R, M, B),
};

// "47,9" → quatro posições com o ponto decimal na do 7; ":" vira os dois pontos de relógio
export function seteSegmentos(texto, classe = "") {
  const casas = [];
  for (const ch of String(texto)) {
    if ((ch === "," || ch === ".") && casas.length && casas.at(-1).tipo === "digito") casas.at(-1).ponto = true;
    else if (ch === ":") casas.push({ tipo: "dois" });
    else casas.push({ tipo: "digito", segmentos: SEGMENTOS[ch] ?? SEGMENTOS[ch.toUpperCase()] ?? "", ponto: false });
  }
  let x = 0;
  const grupos = casas.map((c) => {
    const g = s("g", { transform: `translate(${x} 0)` });
    if (c.tipo === "dois") {
      g.append(s("circle", { cx: 2.5, cy: 7, r: 1.2, class: "aceso" }), s("circle", { cx: 2.5, cy: 15, r: 1.2, class: "aceso" }));
      x += 5;
      return g;
    }
    for (const [nome, pontos] of Object.entries(FORMAS))
      g.append(s("polygon", { points: pontos, class: c.segmentos.includes(nome) ? "aceso" : "apagado" }));
    g.append(s("circle", { cx: 12.8, cy: B, r: 1.05, class: c.ponto ? "aceso" : "apagado" }));
    x += 14.5;
    return g;
  });
  return s("svg", { viewBox: `-1 0 ${x + 1} 22`, class: `sete ${classe}`.trim(), role: "img", "aria-label": String(texto) },
    s("g", { transform: "skewX(-7) translate(2 0)" }, grupos));
}

// --- o visor: um vidro preto com células (desenho + leitura) ------------------------------------------

export function celula(rotulo, desenho, leitura, unidade, extra) {
  return h("div", "celula",
    h("span", "celula-rotulo", rotulo),
    h("div", "celula-corpo", desenho, h("div", "celula-leitura", leitura, unidade && h("span", "celula-unidade", unidade))),
    extra && h("div", "celula-extra", extra));
}

export function visor(...celulas) {
  return h("div", "visor", h("div", "visor-vidro", celulas));
}

const numero = (n, casas = 0) => Number(n).toFixed(casas);
const cor = (fracao) => (fracao >= 1 ? "quente" : fracao >= 0.85 ? "morno" : "frio");

// dois carretéis de fita que giram na velocidade da carga da CPU
function carreteis(carga) {
  const roda = (cx) => s("g", { class: "carretel" },
    s("circle", { cx, cy: 26, r: 19, class: "traco" }),
    s("circle", { cx, cy: 26, r: 5, class: "traco" }),
    [0, 120, 240].map((a) => s("line", {
      x1: cx + 7 * Math.cos((a * Math.PI) / 180), y1: 26 + 7 * Math.sin((a * Math.PI) / 180),
      x2: cx + 16 * Math.cos((a * Math.PI) / 180), y2: 26 + 16 * Math.sin((a * Math.PI) / 180), class: "traco",
    })));
  const desenho = s("svg", { viewBox: "0 0 120 54", class: "desenho carreteis" },
    s("path", { d: "M23 45 L46 50 H74 L97 45", class: "fita" }),
    s("rect", { x: 52, y: 46, width: 16, height: 6, rx: 1, class: "traco" }),
    roda(23), roda(97));
  // de 9 s por volta (parado) a 0,7 s (CPU cheia)
  desenho.style.setProperty("--volta", `${(9 - 8.3 * limite(carga)).toFixed(2)}s`);
  return desenho;
}

function termometro(fracao) {
  const altura = 40 * limite(fracao);
  return s("svg", { viewBox: "0 0 24 60", class: `desenho termometro ${cor(fracao)}` },
    s("rect", { x: 8, y: 3, width: 8, height: 44, rx: 4, class: "traco" }),
    s("circle", { cx: 12, cy: 51, r: 6.5, class: "traco" }),
    s("circle", { cx: 12, cy: 51, r: 4, class: "nivel" }),
    s("rect", { x: 10.2, y: 47 - altura, width: 3.6, height: altura + 1, class: "nivel" }),
    [11, 21, 31, 41].map((y) => s("line", { x1: 18, y1: y, x2: 21, y2: y, class: "traco fino" })));
}

function tanque(fracao) {
  const nivel = 46 * limite(fracao);
  return s("svg", { viewBox: "0 0 34 54", class: `desenho tanque ${cor(fracao / 0.95)}` },
    s("rect", { x: 3, y: 3, width: 28, height: 48, rx: 2, class: "traco" }),
    s("rect", { x: 6, y: 48 - nivel, width: 22, height: nivel, class: "nivel" }),
    Array.from({ length: 11 }, (_, i) => s("line", { x1: 6, y1: 8 + i * 4, x2: 28, y2: 8 + i * 4, class: "risca" })));
}

function chip(fracao) {
  return s("svg", { viewBox: "0 0 54 54", class: "desenho chip" },
    [12, 20, 28, 36, 42].map((p) => [
      s("line", { x1: p, y1: 3, x2: p, y2: 9, class: "traco fino" }), s("line", { x1: p, y1: 45, x2: p, y2: 51, class: "traco fino" }),
      s("line", { x1: 3, y1: p, x2: 9, y2: p, class: "traco fino" }), s("line", { x1: 45, y1: p, x2: 51, y2: p, class: "traco fino" })]),
    s("rect", { x: 9, y: 9, width: 36, height: 36, rx: 3, class: "traco" }),
    s("rect", { x: 17, y: 17, width: 20, height: 20, rx: 1.5, class: "nucleo" }),
    s("rect", { x: 17, y: 37 - 20 * limite(fracao), width: 20, height: 20 * limite(fracao), class: "nivel" }));
}

export function visorInicio(r) {
  const carga = r.carga[0] / r.nucleos;
  const usada = (r.ram_total_mb - r.ram_disponivel_mb) / 1024;
  const total = r.ram_total_mb / 1024;
  const cpu = r.temperaturas.cpu_c;
  return visor(
    celula("cpu", carreteis(carga), seteSegmentos(numero(Math.min(99.9, carga * 100), carga < 0.1 ? 1 : 0)), "%",
      `carga ${r.carga[0].toFixed(2)} em ${r.nucleos} núcleos`),
    cpu != null && celula("temp cpu", termometro(cpu / 85), seteSegmentos(numero(cpu, 1)), "°C"),
    celula("ram", tanque(usada / total), seteSegmentos(numero(usada, 1)), "GB", `de ${numero(total, 1)} GB`),
    r.gpu && celula("gpu", chip(r.gpu.uso_pct / 100), seteSegmentos(numero(r.gpu.temperatura_c)), "°C",
      `uso ${r.gpu.uso_pct}% · vram ${numero(r.gpu.vram_usada_mb / 1024, 1)}/${numero(r.gpu.vram_total_mb / 1024, 1)} GB`),
  );
}

// --- PC: a torre acende e a ventoinha gira quando ele está ligado ---------------------------------------

function ventoinha(classe = "") {
  return s("g", { class: `ventoinha ${classe}`.trim() },
    s("circle", { cx: 0, cy: 0, r: 13, class: "traco" }),
    [0, 72, 144, 216, 288].map((a) => s("path", {
      d: "M0 0 C 3 -4, 8 -6, 11 -3 C 7 -1, 3 0, 0 0 Z", transform: `rotate(${a})`, class: "pa",
    })),
    s("circle", { cx: 0, cy: 0, r: 2.4, class: "nucleo" }));
}

// acelerando: logo depois de ligar, a ventoinha sobe de giro (a cena do PC ligando)
export function visorPC(estado, acelerando = false) {
  const torre = s("svg", { viewBox: "0 0 64 92", class: `desenho torre ${estado.ligado ? "ligado" : "desligado"}` },
    s("rect", { x: 6, y: 3, width: 52, height: 86, rx: 3, class: "traco" }),
    s("line", { x1: 12, y1: 12, x2: 52, y2: 12, class: "traco fino" }),
    s("line", { x1: 12, y1: 17, x2: 52, y2: 17, class: "traco fino" }),
    s("circle", { cx: 32, cy: 32, r: 5, class: "botao-energia" }),
    s("g", { transform: "translate(32 64)" }, ventoinha(estado.ligado ? (acelerando ? "gira acelerando" : "gira") : "")));
  return visor(
    celula("pc gamer", torre, seteSegmentos(estado.ligado ? " on" : "oFF"), null,
      estado.ligado ? "ligado na rede de casa" : "desligado"),
    celula("lm studio", null, seteSegmentos(estado.lm_studio ? " on" : "oFF"), null,
      estado.lm_studio ? "respondendo" : "fora do ar"),
  );
}

// --- agenda: um mostrador de 24 h com a hora de agora e as próximas vezes ----------------------------------

function angulo(data) {
  return ((data.getHours() + data.getMinutes() / 60) / 24) * 360 - 90;
}
function ponto(a, raio) {
  return [50 + raio * Math.cos((a * Math.PI) / 180), 50 + raio * Math.sin((a * Math.PI) / 180)];
}

export function visorAgenda(agendamentos, girando) {
  const agora = new Date();
  const proximos = agendamentos.filter((a) => a.ativo && a.proxima).sort((a, b) => a.proxima - b.proxima);
  const nas24h = proximos.filter((a) => a.proxima - agora.getTime() < 24 * 3600_000);
  const [ax, ay] = ponto(angulo(agora), 30);
  const mostrador = s("svg", { viewBox: "0 0 100 100", class: "desenho mostrador" },
    s("circle", { cx: 50, cy: 50, r: 44, class: "traco" }),
    Array.from({ length: 24 }, (_, i) => {
      const a = (i / 24) * 360 - 90;
      const [x1, y1] = ponto(a, i % 6 === 0 ? 35 : 39);
      const [x2, y2] = ponto(a, 43);
      return s("line", { x1, y1, x2, y2, class: i % 6 === 0 ? "traco" : "traco fino" });
    }),
    [["0", 0], ["6", 6], ["12", 12], ["18", 18]].map(([t, hh]) => {
      const [x, y] = ponto((hh / 24) * 360 - 90, 27);
      return s("text", { x, y: y + 2.6, class: "hora", "text-anchor": "middle" }, t);
    }),
    nas24h.map((a, i) => {
      const [x, y] = ponto(angulo(new Date(a.proxima)), 43);
      return s("circle", { cx: x, cy: y, r: i === 0 ? 3.6 : 2.4, class: i === 0 ? "marcador proxima" : "marcador" });
    }),
    s("g", { class: girando ? "ponteiro girando" : "ponteiro" },
      s("line", { x1: 50, y1: 50, x2: ax, y2: ay, class: "traco" }),
      s("circle", { cx: 50, cy: 50, r: 2.6, class: "nucleo" })));
  const proxima = proximos[0];
  const hora = proxima ? new Date(proxima.proxima).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "--:--";
  return visor(
    celula("próxima vez", mostrador, seteSegmentos(hora), null,
      proxima ? proxima.nome : "nada agendado"),
    celula("nas próximas 24 h", null, seteSegmentos(String(nas24h.length).padStart(2, " ")), null,
      nas24h.length === 1 ? "agendamento" : "agendamentos"),
  );
}

// --- sistema: os três termômetros, a ventoinha da placa e o consumo da GPU ----------------------------------

export function visorSistema(sens) {
  const celulas = [];
  if (sens.cpu.temperatura_c != null)
    celulas.push(celula("cpu", termometro(sens.cpu.temperatura_c / sens.cpu.quente_a_partir_de_c), seteSegmentos(numero(sens.cpu.temperatura_c, 1)), "°C"));
  if (sens.nvme.temperatura_c != null)
    celulas.push(celula("nvme", termometro(sens.nvme.temperatura_c / sens.nvme.alerta_c), seteSegmentos(numero(sens.nvme.temperatura_c, 1)), "°C"));
  if (sens.gpu?.temperatura_c != null)
    celulas.push(celula("gpu", termometro(sens.gpu.temperatura_c / sens.gpu.quente_a_partir_de_c), seteSegmentos(numero(sens.gpu.temperatura_c)), "°C",
      sens.gpu.consumo_w != null ? `${numero(sens.gpu.consumo_w, 1)} W · ventoinha ${sens.gpu.ventoinha_pct ?? "?"}%` : null));
  const [fan, rpm] = Object.entries(sens.placa?.ventoinhas_rpm ?? {})[0] ?? [];
  if (rpm) {
    const desenho = s("svg", { viewBox: "-16 -16 32 32", class: "desenho ventoinha-placa" }, ventoinha("gira"));
    // 2000 rpm → uma volta em 0,4 s; devagar, até 4 s
    desenho.style.setProperty("--volta", `${Math.max(0.4, Math.min(4, 800 / rpm)).toFixed(2)}s`);
    celulas.push(celula(`ventoinha ${fan}`, desenho, seteSegmentos(String(rpm)), "rpm"));
  }
  return visor(...celulas);
}
