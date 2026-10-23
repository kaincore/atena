// Arquivos: o servidor inteiro, menos os segredos (o executor decide o que sai).
import { abrirJanela, atualizar, campo, cartao, carregando, consultar, falha, h, item, itens, num, semAcao } from "../comum.js";
import { picto } from "../pictos.js";

const arquivos = { caminho: "/srv" };

function baixar(nome, texto) {
  const url = URL.createObjectURL(new Blob([texto], { type: "text/plain;charset=utf-8" }));
  const link = h("a", { href: url, download: nome });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

async function abrirArquivo(caminho) {
  abrirJanela(caminho, carregando("Carregando…"));
  const r = await consultar("arquivo.ler", { caminho });
  if (r.ok === false) return abrirJanela(caminho, falha(r));
  const x = r.resultado;
  if (x.binario) return abrirJanela(caminho, h("p", { class: "fraco" }, `Arquivo binário (${Math.round(x.tamanho / 1024)} KB): o painel só mostra e baixa texto.`));
  abrirJanela(caminho,
    x.cortado && h("p", { class: "fraco" }, "Mostrando só os primeiros 64 KB."),
    h("pre", { class: "log" }, x.texto || "(vazio)"),
    h("div", { class: "botoes" }, h("button", { type: "button", onclick: () => baixar(caminho.split("/").pop() || "arquivo.txt", x.texto) }, "Baixar")),
    h("p", { class: "fraco" }, "Os segredos aparecem como *** aqui e no que você baixar."));
}

function resultados(r, montar) {
  if (r.ok === false) return [falha(r)];
  const achados = r.resultado.achados;
  return [
    itens(achados.map((a) => item({
      nome: h("a", { href: "#arquivos", class: "arquivo", onclick: (e) => { e.preventDefault(); abrirArquivo(a.arquivo); } }, a.arquivo),
      detalhe: montar(a),
    })), "Nada encontrado."),
    r.resultado.incompleta && h("p", { class: "fraco" }, "A busca parou no limite (tempo ou quantidade): procure numa pasta menor."),
  ].filter(Boolean);
}

function cartaoProcurar(pasta) {
  const saida = h("div");
  const buscar = (acao, params, montar) => async (evento) => {
    evento.preventDefault();
    saida.replaceChildren(carregando("Procurando…"));
    const r = await consultar(acao, { pasta, ...params(evento.currentTarget) });
    saida.replaceChildren(...resultados(r, montar));
  };
  return cartao(`Procurar em ${pasta}`,
    h("form", { class: "filtros", onsubmit: buscar("arquivo.procurar", (f) => ({
      ...(f.nome.value.trim() ? { nome: f.nome.value.trim() } : {}), ...(f.tipo.value ? { tipo: f.tipo.value } : {}),
      ...(f.dias.value ? { dias: Number(f.dias.value) } : {}),
    }), (a) => `${num(a.tamanho_kb)} KB · ${a.modificado}`) },
      h("label", { class: "campo cresce" }, h("span", { class: "rotulo" }, "Nome"),
        h("input", { name: "nome", placeholder: "pedaço do nome ou *.pdf", autocomplete: "off" })),
      campo("Tipo", h("select", { name: "tipo" }, [["", "qualquer tipo"], ["documento", "documento"], ["planilha", "planilha"], ["foto", "foto"], ["video", "vídeo"], ["audio", "áudio"]].map(([v, t]) => h("option", { value: v }, t)))),
      campo("Data", h("select", { name: "dias" }, [["", "qualquer data"], ["1", "último dia"], ["7", "última semana"], ["30", "último mês"], ["365", "último ano"]].map(([v, t]) => h("option", { value: v }, t)))),
      h("button", { type: "submit" }, "Procurar pelo nome")),
    h("form", { class: "filtros", onsubmit: buscar("arquivo.buscar", (f) => ({ texto: f.texto.value }), (a) =>
      h("span", { class: "resumo" }, `linha ${a.linha}: ${a.trecho}`)) },
      h("label", { class: "campo cresce" }, h("span", { class: "rotulo" }, "Texto dentro dos arquivos"),
        h("input", { name: "texto", minlength: "2", required: true, autocomplete: "off" })),
      h("button", { type: "submit" }, "Procurar o texto")),
    saida);
}

export async function telaArquivos() {
  const r = await consultar("arquivo.ler", { caminho: arquivos.caminho });
  const navegar = (caminho) => { arquivos.caminho = caminho; atualizar(); };
  const barra = h("form", { class: "nova", onsubmit: (evento) => { evento.preventDefault(); navegar(evento.currentTarget.caminho.value.trim() || "/"); } },
    h("input", { name: "caminho", value: arquivos.caminho, autocomplete: "off", spellcheck: "false", "aria-label": "Caminho" }),
    h("button", { type: "submit", class: "discreto" }, "Abrir"));
  if (r.ok === false) return [cartao("Arquivos", barra, falha(r), semAcao(r, "arquivo.ler"))];
  if (!r.resultado.pasta) { // um arquivo: mostra e volta para a pasta dele
    abrirArquivo(r.resultado.arquivo);
    arquivos.caminho = r.resultado.arquivo.replace(/\/[^/]+$/, "") || "/";
    return telaArquivos();
  }
  const pasta = r.resultado.pasta;
  const pai = pasta === "/" ? null : pasta.replace(/\/[^/]+$/, "") || "/";
  const link = (desenho, texto, classe, clique) => h("a", { href: "#arquivos", class: classe, onclick: (e) => { e.preventDefault(); clique(); } },
    picto(desenho), h("span", null, texto));
  // a trilha do caminho: cada pasta dele é um link
  const partes = pasta.split("/").filter(Boolean);
  const trilha = h("nav", { class: "trilha-caminho", "aria-label": "Pasta aberta" },
    h("a", { href: "#arquivos", onclick: (e) => { e.preventDefault(); navegar("/"); } }, "/"),
    partes.map((p, i) => [i > 0 && h("span", { "aria-hidden": "true" }, "/"),
      i === partes.length - 1 ? h("span", { "aria-current": "page" }, p)
        : h("a", { href: "#arquivos", onclick: (e) => { e.preventDefault(); navegar("/" + partes.slice(0, i + 1).join("/")); } }, p)]));
  const lista = cartao("Arquivos", barra, trilha,
    itens([
      pai && item({ classe: "arquivo", nome: link("subir", "Pasta de cima", "pasta", () => navegar(pai)) }),
      r.resultado.itens.map((n) => {
        const ehPasta = n.endsWith("/");
        const caminho = `${pasta === "/" ? "" : pasta}/${n.replace(/\/$/, "")}`;
        return item({ classe: "arquivo", nome: ehPasta ? link("pasta", n.slice(0, -1), "pasta", () => navegar(caminho))
          : link("documento", n, null, () => abrirArquivo(caminho)) });
      }),
    ], "Pasta vazia."),
    r.resultado.total > r.resultado.itens.length && h("p", { class: "fraco" }, `Mostrando ${r.resultado.itens.length} de ${r.resultado.total}.`),
    h("p", { class: "fraco" }, "Os segredos (.env, chaves, tokens) não saem do servidor, e o que é lido sai com as senhas ocultas."));
  return [lista, cartaoProcurar(pasta)];
}
