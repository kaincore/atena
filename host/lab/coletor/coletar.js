// Coletor das receitas: abre um site num Chromium sem tela e grava, numa pasta, o que o Claude Code
// precisa para descrever o estilo dele: prints, o HTML, o CSS e os scripts que o site carregou, as
// variáveis de cor e de tamanho, os estilos de verdade dos elementos, as fontes, as cores mais usadas,
// os espaçamentos e o movimento. Não roda IA nenhuma. O executor (receita.estudar) o roda num container
// de uma vez, na rede lab-coletor: internet sim; rede de casa, Tailscale e servidor não.
// Uso: node coletar.js <url> <pasta>
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright-core");

const LIMITE_ARQUIVO = 3 * 1024 * 1024;   // um CSS ou um script
const LIMITE_CSS = 8 * 1024 * 1024;       // todos os CSS juntos
const LIMITE_JS = 25 * 1024 * 1024;       // todos os scripts juntos
const LIMITE_HTML = 5 * 1024 * 1024;
const ALTURA_INTEIRA = 6000;              // a página inteira, cortada aqui (px)
const TELAS = {
  pc: { width: 1440, height: 900 },
  tablet: { width: 820, height: 1180 },
  celular: { width: 390, height: 844 },
};

const [url, pasta] = process.argv.slice(2);
if (!/^https?:\/\//.test(url || "") || !pasta) {
  console.error("uso: node coletar.js <http(s)://endereço> <pasta>");
  process.exit(2);
}

const coleta = { url, inicio: new Date().toISOString(), arquivos: {}, avisos: [], erros_console: [], falhas_rede: [] };
const gravar = (nome, conteudo) => {
  const destino = path.join(pasta, nome);
  fs.mkdirSync(path.dirname(destino), { recursive: true });
  fs.writeFileSync(destino, conteudo);
  coleta.arquivos[nome] = Buffer.byteLength(conteudo);
};
const gravarJson = (nome, dados) => gravar(nome, JSON.stringify(dados, null, 1) + "\n");
const aviso = (texto) => coleta.avisos.push(String(texto).split("\n")[0].slice(0, 300));
async function tentar(o_que, passo) {
  try {
    return await passo();
  } catch (e) {
    aviso(`${o_que}: ${e.message || e}`);
    return null;
  }
}

// nome de arquivo a partir do endereço: só letras, números, ponto e hífen
function nomeDoArquivo(endereco, n, extensao) {
  let base = "arquivo";
  try {
    base = path.basename(new URL(endereco).pathname) || "index";
  } catch {}
  base = base.replace(/\.(css|js|mjs)$/i, "").replace(/[^A-Za-z0-9.-]+/g, "-").slice(0, 60) || "arquivo";
  return `${String(n).padStart(3, "0")}-${base}.${extensao}`;
}

// o que roda dentro da página: lê os estilos de verdade (computados) e resume
function lerPagina(alturaInteira) {
  const visivel = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none" && Number(s.opacity) > 0;
  };
  const conta = (mapa, chave, peso = 1) => {
    if (chave && chave !== "none" && chave !== "normal" && chave !== "auto") mapa.set(chave, (mapa.get(chave) || 0) + peso);
  };
  const topo = (mapa, n) => [...mapa.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([valor, vezes]) => ({ valor, vezes: Math.round(vezes) }));
  const props = (el, nomes) => {
    const s = getComputedStyle(el);
    return Object.fromEntries(nomes.map((n) => [n, s.getPropertyValue(n)]).filter(([, v]) => v && v !== "none" && v !== "normal" && v !== "0px" && v !== "auto"));
  };
  const texto = (el) => (el.innerText || el.getAttribute("aria-label") || el.getAttribute("alt") || "").trim().replace(/\s+/g, " ").slice(0, 60);
  const classes = (el) => (typeof el.className === "string" ? el.className.trim().split(/\s+/).slice(0, 6).join(" ") : "");

  // as regras de CSS que dão para ler (as de outro domínio sem CORS não dão: o CSS delas está em estilos/)
  const regras = [];
  const percorrer = (lista, midia) => {
    for (const r of lista) {
      if (r.cssRules && r.media) percorrer(r.cssRules, r.media.mediaText);
      else if (r.cssRules && r.conditionText !== undefined) percorrer(r.cssRules, r.conditionText);
      else regras.push({ r, midia });
    }
  };
  let folhas_ilegiveis = 0;
  for (const folha of document.styleSheets) {
    try {
      percorrer(folha.cssRules, "");
    } catch {
      folhas_ilegiveis++;
    }
  }

  // variáveis (custom properties) declaradas em :root, html, body e [data-theme]
  const variaveis = [];
  for (const { r, midia } of regras) {
    if (!r.style || !/^(:root|html|body|\[data-theme|\.dark|\.light|:host)/.test(r.selectorText || "")) continue;
    for (const nome of r.style) if (nome.startsWith("--")) variaveis.push({ nome, valor: r.style.getPropertyValue(nome).trim(), seletor: r.selectorText, midia });
  }
  const raiz = getComputedStyle(document.documentElement);
  const computadas = {};
  for (const nome of raiz) if (nome.startsWith("--")) computadas[nome] = raiz.getPropertyValue(nome).trim();

  // breakpoints, @font-face, @keyframes e se o site respeita reduzir movimento
  const quebras = new Map();
  const faces = [];
  const quadros = [];
  let reduz_movimento = false;
  for (const { r, midia } of regras) {
    for (const m of (midia || "").matchAll(/(min|max)-width:\s*([\d.]+)(px|em|rem)/g)) conta(quebras, `${m[1]}-width: ${m[2]}${m[3]}`);
    if (/prefers-reduced-motion/.test(midia || "")) reduz_movimento = true;
    if (r.constructor.name === "CSSFontFaceRule") {
      faces.push({ familia: r.style.getPropertyValue("font-family").replace(/["']/g, ""), peso: r.style.getPropertyValue("font-weight"), estilo: r.style.getPropertyValue("font-style"), display: r.style.getPropertyValue("font-display"), src: r.style.getPropertyValue("src").slice(0, 300) });
    } else if (r.constructor.name === "CSSKeyframesRule") quadros.push(r.name);
  }

  // tipografia: até 3 elementos visíveis de cada tipo
  const TIPOS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "a", "button", "li", "label", "input", "small", "blockquote", "code", "figcaption", "nav a", "header", "footer"];
  const tipografia = {};
  for (const sel of TIPOS) {
    const achados = [...document.querySelectorAll(sel)].filter(visivel).slice(0, 3);
    if (achados.length) tipografia[sel] = achados.map((el) => ({ texto: texto(el), ...props(el, ["font-family", "font-size", "font-weight", "line-height", "letter-spacing", "text-transform", "font-style", "color", "text-decoration-line"]) }));
  }

  // componentes: botões, links com cara de botão, campos, cartões, menus
  const COMPONENTES = {
    botao: "button, [role=button], a[class*=btn], a[class*=button], input[type=submit]",
    campo: "input:not([type=hidden]):not([type=submit]):not([type=checkbox]):not([type=radio]), select, textarea",
    cartao: "[class*=card], [class*=Card], article, [class*=tile]",
    menu: "nav, [role=navigation]",
    topo: "header, [role=banner]",
    rodape: "footer, [role=contentinfo]",
    selo: "[class*=badge], [class*=tag], [class*=chip], [class*=pill]",
    janela: "dialog, [role=dialog], [class*=modal]",
    imagem: "img, picture, svg[class], video",
  };
  const VISUAL = ["background-color", "background-image", "color", "border", "border-radius", "box-shadow", "padding", "gap", "display", "font-size", "font-weight", "transition", "backdrop-filter", "outline", "opacity", "max-width"];
  const componentes = {};
  for (const [nome, sel] of Object.entries(COMPONENTES)) {
    const achados = [...document.querySelectorAll(sel)].filter(visivel).slice(0, 4);
    if (achados.length) componentes[nome] = achados.map((el) => {
      const r = el.getBoundingClientRect();
      return { tag: el.tagName.toLowerCase(), classes: classes(el), texto: texto(el), tamanho: `${Math.round(r.width)}x${Math.round(r.height)}`, ...props(el, VISUAL) };
    });
  }

  // cores, espaçamentos, cantos, sombras, tamanhos de letra e movimento: o que mais aparece na página
  const cores = new Map(), fundos = new Map(), bordas = new Map(), espacos = new Map(), cantos = new Map();
  const sombras = new Map(), letras = new Map(), alturas = new Map(), familias = new Map(), transicoes = new Map();
  const grades = new Map(), larguras = new Map();
  let flex = 0, grid = 0, vistos = 0;
  for (const el of document.querySelectorAll("body *")) {
    if (vistos >= 5000) break;
    if (!visivel(el)) continue;
    vistos++;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const area = Math.min(r.width * r.height, 1440 * 900) / 1000;
    if (el.childNodes.length && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) {
      conta(cores, s.color, 1);
      conta(letras, s.fontSize);
      conta(alturas, s.lineHeight);
      conta(familias, s.fontFamily);
    }
    if (s.backgroundColor !== "rgba(0, 0, 0, 0)") conta(fundos, s.backgroundColor, area);
    if (parseFloat(s.borderTopWidth) > 0 && s.borderTopStyle !== "none") conta(bordas, `${s.borderTopWidth} ${s.borderTopStyle} ${s.borderTopColor}`);
    for (const p of ["paddingTop", "paddingLeft", "marginTop", "marginBottom", "rowGap", "columnGap"]) if (parseFloat(s[p]) > 0) conta(espacos, s[p]);
    if (parseFloat(s.borderTopLeftRadius) > 0) conta(cantos, s.borderRadius);
    if (s.boxShadow !== "none") conta(sombras, s.boxShadow);
    if (s.transitionDuration !== "0s") conta(transicoes, `${s.transitionProperty} ${s.transitionDuration} ${s.transitionTimingFunction}`);
    if (s.display.includes("flex")) flex++;
    if (s.display.includes("grid")) {
      grid++;
      conta(grades, s.gridTemplateColumns.split(" ").length > 12 ? `${s.gridTemplateColumns.split(" ").length} colunas` : s.gridTemplateColumns);
    }
    if (s.maxWidth !== "none" && s.marginLeft === s.marginRight && parseFloat(s.marginLeft) > 0) conta(larguras, s.maxWidth);
  }
  const animacoes = document.getAnimations().slice(0, 40).map((a) => {
    const t = a.effect && a.effect.getTiming ? a.effect.getTiming() : {};
    return { tipo: a.constructor.name, nome: a.animationName || a.transitionProperty || "", duracao: t.duration, atraso: t.delay, curva: t.easing, vezes: t.iterations, alvo: a.effect && a.effect.target ? a.effect.target.tagName.toLowerCase() + (classes(a.effect.target) ? "." + classes(a.effect.target).split(" ")[0] : "") : "" };
  });

  // o esqueleto da página: as faixas de cima para baixo (os blocos largos mais de fora, sem os
  // embrulhos que ocupam a página toda)
  const alturaPagina = document.documentElement.scrollHeight;
  const faixa = (el) => {
    const r = el.getBoundingClientRect();
    return r.width >= innerWidth * 0.6 && r.height >= 80 && r.height <= alturaPagina * 0.6 && visivel(el);
  };
  const blocos = [];
  const escolhidos = [];
  for (const el of [...document.querySelectorAll("body *")].slice(0, 6000)) {
    if (blocos.length >= 40) break;
    if (escolhidos.some((e) => e.contains(el)) || !faixa(el)) continue;
    escolhidos.push(el);
    const r = el.getBoundingClientRect();
    const titulo = el.querySelector("h1, h2, h3");
    blocos.push({ tag: el.tagName.toLowerCase(), classes: classes(el), y: Math.round(r.top + scrollY), altura: Math.round(r.height), titulo: titulo ? texto(titulo) : "", fundo: getComputedStyle(el).backgroundColor });
  }
  blocos.sort((a, b) => a.y - b.y);

  // o que dá pistas da pilha: frameworks e bibliotecas
  const pistas = [];
  if (window.__NEXT_DATA__ || document.querySelector("#__next")) pistas.push("Next.js");
  if (window.__NUXT__ || document.querySelector("#__nuxt")) pistas.push("Nuxt");
  if (document.querySelector("[data-reactroot], #root")) pistas.push("React (provável)");
  if (document.querySelector("[ng-version]")) pistas.push("Angular");
  if (document.querySelector("[class*=svelte-]")) pistas.push("Svelte");
  if (document.querySelector("[data-astro-cid], astro-island")) pistas.push("Astro");
  if (document.querySelector("[data-framer-name], [class*=framer-]")) pistas.push("Framer");
  if (document.querySelector("[data-wf-page], .w-nav")) pistas.push("Webflow");
  if ([...document.querySelectorAll("[class]")].slice(0, 400).some((e) => /\b(flex|grid|px-\d|py-\d|text-(sm|lg|xl)|rounded-(md|lg|xl))\b/.test(classes(e)))) pistas.push("Tailwind (provável)");
  const gerador = document.querySelector("meta[name=generator]");
  if (gerador) pistas.push(`gerador: ${gerador.content.slice(0, 60)}`);

  const meta = (n) => (document.querySelector(`meta[name="${n}"], meta[property="${n}"]`) || {}).content || "";
  return {
    pagina: { titulo: document.title, idioma: document.documentElement.lang, descricao: meta("description").slice(0, 300), cor_tema: meta("theme-color"), altura: document.documentElement.scrollHeight, largura: document.documentElement.scrollWidth, elementos_vistos: vistos, folhas_ilegiveis, pistas },
    variaveis: { declaradas: variaveis.slice(0, 600), computadas_na_raiz: computadas },
    tipografia,
    componentes,
    medidas: {
      cores_de_texto: topo(cores, 24), fundos_por_area: topo(fundos, 24), bordas: topo(bordas, 12),
      espacos: topo(espacos, 24), cantos: topo(cantos, 12), sombras: topo(sombras, 12),
      tamanhos_de_letra: topo(letras, 16), alturas_de_linha: topo(alturas, 12), familias: topo(familias, 8),
      larguras_maximas: topo(larguras, 8), grades: topo(grades, 10), quebras: topo(quebras, 16), flex, grid,
    },
    fontes: { faces: faces.slice(0, 40), carregadas: [...document.fonts].filter((f) => f.status === "loaded").slice(0, 40).map((f) => ({ familia: f.family.replace(/["']/g, ""), peso: f.weight, estilo: f.style })) },
    movimento: { transicoes: topo(transicoes, 16), animacoes, keyframes: [...new Set(quadros)].slice(0, 40), respeita_reduzir_movimento: reduz_movimento },
    esqueleto: blocos,
    altura_inteira: Math.min(document.documentElement.scrollHeight, alturaInteira),
  };
}

// o que muda quando o mouse passa: até 6 botões e links
async function estadosHover(pagina) {
  const alvos = await pagina.$$("button, [role=button], a[class*=btn], a[class*=button], nav a");
  const PROPS = ["color", "background-color", "border-color", "box-shadow", "transform", "opacity", "text-decoration-line", "outline", "filter"];
  const resultado = [];
  for (const alvo of alvos.slice(0, 12)) {
    if (resultado.length >= 6) break;
    if (!(await alvo.isVisible().catch(() => false))) continue;
    const ler = () => alvo.evaluate((el, ps) => {
      const s = getComputedStyle(el);
      return Object.fromEntries(ps.map((p) => [p, s.getPropertyValue(p)]));
    }, PROPS);
    const antes = await ler();
    await alvo.hover({ timeout: 2000 }).catch(() => null);
    await pagina.waitForTimeout(400);
    const depois = await ler();
    const mudou = Object.fromEntries(PROPS.filter((p) => antes[p] !== depois[p]).map((p) => [p, { antes: antes[p], depois: depois[p] }]));
    const texto = await alvo.evaluate((el) => (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 40));
    if (Object.keys(mudou).length) resultado.push({ texto, mudou });
  }
  await pagina.mouse.move(0, 0);
  return resultado;
}

// desce a página devagar, para o que só aparece ao rolar (imagens, animações) aparecer
async function rolar(pagina) {
  await pagina.evaluate(async () => {
    const passo = innerHeight * 0.8;
    for (let y = 0, n = 0; y < document.documentElement.scrollHeight && n < 20; y += passo, n++) {
      scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 250));
    }
    scrollTo(0, 0);
  });
  await pagina.waitForTimeout(600);
}

async function abrir(navegador, opcoes, comHar) {
  const contexto = await navegador.newContext({
    ...opcoes, serviceWorkers: "block", acceptDownloads: false, locale: "pt-BR", timezoneId: "America/Sao_Paulo",
    ...(comHar ? { recordHar: { path: path.join(pasta, "rede.har"), content: "omit" } } : {}),
  });
  const pagina = await contexto.newPage();
  pagina.setDefaultTimeout(15000);
  return { contexto, pagina };
}

async function irPara(pagina) {
  const resposta = await pagina.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
  await pagina.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => aviso("a rede não sossegou em 15 s; segui assim"));
  return resposta;
}

(async () => {
  fs.mkdirSync(pasta, { recursive: true });
  const navegador = await chromium.launch({ headless: true });
  coleta.navegador = navegador.version();
  let saida = 0;
  try {
    // 1. no PC: a coleta inteira (com o registro da rede), os prints e o que muda no hover
    const { contexto, pagina } = await abrir(navegador, { viewport: TELAS.pc }, true);
    let nCss = 0, nJs = 0, totalCss = 0, totalJs = 0;
    const recursos = [];
    const pendentes = new Set();   // corpos ainda chegando: espera antes de fechar
    pagina.on("console", (m) => { if (m.type() === "error" && coleta.erros_console.length < 30) coleta.erros_console.push(m.text().slice(0, 200)); });
    pagina.on("requestfailed", (r) => { if (coleta.falhas_rede.length < 30) coleta.falhas_rede.push(`${r.url().slice(0, 150)}: ${(r.failure() || {}).errorText || "?"}`); });
    pagina.on("response", (r) => {
      const tipo = r.request().resourceType();
      if (tipo !== "stylesheet" && tipo !== "script") return;
      const lendo = guardarRecurso(r, tipo).finally(() => pendentes.delete(lendo));
      pendentes.add(lendo);
    });
    async function guardarRecurso(r, tipo) {
      const item = { url: r.url().slice(0, 500), tipo, status: r.status() };
      recursos.push(item);
      try {
        const corpo = await r.body();
        if (corpo.length > LIMITE_ARQUIVO) return void (item.motivo = "grande demais");
        if (tipo === "stylesheet") {
          if (totalCss + corpo.length > LIMITE_CSS) return void (item.motivo = "passou do limite dos CSS");
          totalCss += corpo.length;
          item.arquivo = `estilos/${nomeDoArquivo(r.url(), ++nCss, "css")}`;
        } else {
          if (totalJs + corpo.length > LIMITE_JS) return void (item.motivo = "passou do limite dos scripts");
          totalJs += corpo.length;
          item.arquivo = `scripts/${nomeDoArquivo(r.url(), ++nJs, "js")}`;
        }
        gravar(item.arquivo, corpo);
      } catch {
        item.motivo = "sem corpo (redirecionamento ou bloqueio)";
      }
    }
    const resposta = await irPara(pagina);
    coleta.status = resposta ? resposta.status() : null;
    coleta.url_final = pagina.url();
    coleta.titulo = await pagina.title();
    if (!resposta || resposta.status() >= 400) aviso(`o site respondeu ${coleta.status}: a coleta pode ser de uma página de erro`);
    await gravar("prints/pc.jpg", await pagina.screenshot({ type: "jpeg", quality: 82 }));
    await tentar("rolar a página", () => rolar(pagina));
    const dados = await pagina.evaluate(lerPagina, ALTURA_INTEIRA);
    gravarJson("estilo.json", dados);
    await tentar("print da página inteira", async () => gravar("prints/pc-inteira.jpg", await pagina.screenshot({
      type: "jpeg", quality: 70, fullPage: true, clip: { x: 0, y: 0, width: TELAS.pc.width, height: dados.altura_inteira },
    })));
    const hover = await tentar("estados de hover", () => estadosHover(pagina));
    if (hover) gravarJson("hover.json", hover);
    await tentar("o HTML", async () => {
      const html = await pagina.content();
      gravar("pagina.html", html.length > LIMITE_HTML ? html.slice(0, LIMITE_HTML) : html);
    });
    await Promise.allSettled([...pendentes]);
    gravarJson("recursos.json", recursos);
    await contexto.close();   // fecha o registro da rede (rede.har)
    if (fs.existsSync(path.join(pasta, "rede.har"))) coleta.arquivos["rede.har"] = fs.statSync(path.join(pasta, "rede.har")).size;

    // 2. o tema escuro do PC, o tablet e o celular: só os prints
    const outras = [
      ["pc-escuro", { viewport: TELAS.pc, colorScheme: "dark" }],
      ["tablet", { viewport: TELAS.tablet, isMobile: true, hasTouch: true }],
      ["celular", { viewport: TELAS.celular, isMobile: true, hasTouch: true }],
    ];
    for (const [nome, opcoes] of outras) {
      await tentar(`print ${nome}`, async () => {
        const { contexto: c, pagina: p } = await abrir(navegador, opcoes, false);
        try {
          await irPara(p);
          await gravar(`prints/${nome}.jpg`, await p.screenshot({ type: "jpeg", quality: 82 }));
          if (nome === "celular") {
            const altura = await p.evaluate((max) => Math.min(document.documentElement.scrollHeight, max), ALTURA_INTEIRA);
            await gravar("prints/celular-inteira.jpg", await p.screenshot({
              type: "jpeg", quality: 70, fullPage: true, clip: { x: 0, y: 0, width: TELAS.celular.width, height: altura },
            }));
          }
        } finally {
          await c.close();
        }
      });
    }
  } catch (e) {
    aviso(`a coleta parou: ${e.message || e}`);
    saida = 1;
  } finally {
    await navegador.close();
  }
  coleta.fim = new Date().toISOString();
  if (!coleta.arquivos["prints/pc.jpg"]) saida = 1;
  gravarJson("coleta.json", coleta);
  console.log(saida === 0
    ? `coleta pronta: ${Object.keys(coleta.arquivos).length} arquivos (${coleta.titulo || "sem título"})`
    : `a coleta falhou: ${coleta.avisos.slice(-1)[0] || "sem detalhe"}`);
  process.exit(saida);
})().catch((e) => {
  console.error("falhou: " + String(e.message || e).split("\n")[0]);
  process.exit(1);
});
