// Arquivos: o servidor inteiro, menos os segredos (o executor decide o que sai).
import { abrirJanela, atualizar, cartao, consultar, falha, h, semAcao } from "../comum.js";

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
  abrirJanela(caminho, h("p", { class: "fraco" }, "Carregando…"));
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
    achados.length ? h("ul", { class: "lista" }, achados.map((a) => h("li", null,
      h("a", { href: "#arquivos", onclick: (e) => { e.preventDefault(); abrirArquivo(a.arquivo); } }, a.arquivo), montar(a))))
      : h("p", { class: "fraco" }, "Nada encontrado."),
    r.resultado.incompleta && h("p", { class: "fraco" }, "A busca parou no limite (tempo ou quantidade): procure numa pasta menor."),
  ].filter(Boolean);
}

function cartaoProcurar(pasta) {
  const saida = h("div");
  const buscar = (acao, params, montar) => async (evento) => {
    evento.preventDefault();
    saida.replaceChildren(h("p", { class: "fraco" }, "Procurando…"));
    const r = await consultar(acao, { pasta, ...params(evento.currentTarget) });
    saida.replaceChildren(...resultados(r, montar));
  };
  return cartao(`Procurar em ${pasta}`,
    h("form", { class: "filtros", onsubmit: buscar("arquivo.procurar", (f) => ({
      ...(f.nome.value.trim() ? { nome: f.nome.value.trim() } : {}), ...(f.tipo.value ? { tipo: f.tipo.value } : {}),
      ...(f.dias.value ? { dias: Number(f.dias.value) } : {}),
    }), (a) => h("small", null, ` ${a.tamanho_kb} KB · ${a.modificado}`)) },
      h("input", { name: "nome", placeholder: "pedaço do nome ou *.pdf", autocomplete: "off" }),
      h("select", { name: "tipo" }, [["", "qualquer tipo"], ["documento", "documento"], ["planilha", "planilha"], ["foto", "foto"], ["video", "vídeo"], ["audio", "áudio"]].map(([v, t]) => h("option", { value: v }, t))),
      h("select", { name: "dias" }, [["", "qualquer data"], ["1", "último dia"], ["7", "última semana"], ["30", "último mês"], ["365", "último ano"]].map(([v, t]) => h("option", { value: v }, t))),
      h("button", { type: "submit" }, "Procurar pelo nome")),
    h("form", { class: "filtros", onsubmit: buscar("arquivo.buscar", (f) => ({ texto: f.texto.value }), (a) =>
      h("div", { class: "fraco resumo" }, `linha ${a.linha}: ${a.trecho}`)) },
      h("input", { name: "texto", placeholder: "texto dentro dos arquivos", minlength: "2", required: true, autocomplete: "off" }),
      h("button", { type: "submit" }, "Procurar o texto")),
    saida);
}

export async function telaArquivos() {
  const r = await consultar("arquivo.ler", { caminho: arquivos.caminho });
  const navegar = (caminho) => { arquivos.caminho = caminho; atualizar(); };
  const barra = h("form", { class: "filtros", onsubmit: (evento) => { evento.preventDefault(); navegar(evento.currentTarget.caminho.value.trim() || "/"); } },
    h("input", { name: "caminho", value: arquivos.caminho, size: "36", autocomplete: "off", spellcheck: "false" }),
    h("button", { type: "submit" }, "Abrir"));
  if (r.ok === false) return [cartao("Arquivos", barra, falha(r), semAcao(r, "arquivo.ler"))];
  if (!r.resultado.pasta) { // um arquivo: mostra e volta para a pasta dele
    abrirArquivo(r.resultado.arquivo);
    arquivos.caminho = r.resultado.arquivo.replace(/\/[^/]+$/, "") || "/";
    return telaArquivos();
  }
  const pasta = r.resultado.pasta;
  const pai = pasta === "/" ? null : pasta.replace(/\/[^/]+$/, "") || "/";
  const lista = cartao("Arquivos", barra,
    h("ul", { class: "lista arquivos" },
      pai && h("li", null, h("a", { href: "#arquivos", onclick: (e) => { e.preventDefault(); navegar(pai); } }, "Pasta de cima")),
      r.resultado.itens.map((n) => {
        const ehPasta = n.endsWith("/");
        const caminho = `${pasta === "/" ? "" : pasta}/${n.replace(/\/$/, "")}`;
        return h("li", null, h("a", { href: "#arquivos", class: ehPasta ? "pasta" : null, onclick: (e) => {
          e.preventDefault();
          if (ehPasta) navegar(caminho);
          else abrirArquivo(caminho);
        } }, n));
      })),
    r.resultado.total > r.resultado.itens.length && h("p", { class: "fraco" }, `Mostrando ${r.resultado.itens.length} de ${r.resultado.total}.`),
    h("p", { class: "fraco" }, "Os segredos (.env, chaves, tokens) não saem do servidor, e o que é lido sai com as senhas ocultas."));
  return [lista, cartaoProcurar(pasta)];
}
