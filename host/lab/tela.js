// atena-tela: tira um print de uma página local, para o Claude Code do lab conferir o visual.
// Uso: atena-tela <url> <saida.png> [--celular] [--largura N] [--altura N] [--inteira]
"use strict";
const { chromium } = require("playwright-core");

function opcoes(argv) {
  const o = { largura: 1280, altura: 800, inteira: false, celular: false, posicionais: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--celular") o.celular = true;
    else if (a === "--inteira") o.inteira = true;
    else if (a === "--largura") o.largura = parseInt(argv[++i], 10);
    else if (a === "--altura") o.altura = parseInt(argv[++i], 10);
    else o.posicionais.push(a);
  }
  if (o.celular) { o.largura = 390; o.altura = 844; }
  return o;
}

(async () => {
  const o = opcoes(process.argv.slice(2));
  const [url, saida] = o.posicionais;
  if (!url || !saida || !/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?(\/|$)/.test(url)) {
    console.error("uso: atena-tela http://127.0.0.1:<porta>/<caminho> <saida.png> [--celular] [--largura N] [--altura N] [--inteira]");
    console.error("(só endereços locais: 127.0.0.1 ou localhost)");
    process.exit(2);
  }
  const navegador = await chromium.launch({ headless: true });
  try {
    const pagina = await navegador.newPage({
      viewport: { width: o.largura, height: o.altura },
      deviceScaleFactor: o.celular ? 2 : 1,
      isMobile: o.celular, hasTouch: o.celular,
    });
    const erros = [];
    pagina.on("console", (m) => { if (m.type() === "error") erros.push(m.text()); });
    pagina.on("pageerror", (e) => erros.push(String(e)));
    const resposta = await pagina.goto(url, { waitUntil: "networkidle", timeout: 20000 });
    await pagina.screenshot({ path: saida, fullPage: o.inteira });
    console.log(`print salvo em ${saida} (${o.largura}x${o.altura}${o.inteira ? ", página inteira" : ""})`);
    console.log(`HTTP ${resposta ? resposta.status() : "?"} · título: ${await pagina.title()}`);
    console.log(erros.length ? `erros no console (${erros.length}):\n- ` + erros.slice(0, 10).join("\n- ") : "sem erros no console");
  } finally {
    await navegador.close();
  }
})().catch((e) => { console.error("falhou: " + String(e.message || e).split("\n")[0]); process.exit(1); });
