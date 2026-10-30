// Receitas: o estilo de um site que você gostou, estudado pelo Claude Code e guardado para os seus projetos.
// O coletor abre o site (só pela internet, sem IA) e o Claude Code escreve a receita; aqui você pede, vê as
// receitas (paleta, fontes, prints e o texto) e manda um projeto do lab seguir uma delas.
import { abrirJanela, atualizar, botaoAtualizar, campo, carregando, cartao, consultar, data, falha, h, item, itens, linha,
  mudar, semAcao, vazio } from "../comum.js";
import { usarReceita } from "./lab.js";

const NOME = "[a-z0-9][a-z0-9\\-]{0,30}";
const rascunho = { url: "", nome: "", foco: "", conta: "", modelo: "", esforco: "", refazer: false };
let busca = "";
const ESTADOS = { pronta: ["ok", "pronta"], estudando: ["info", "estudando"], falhou: ["ruim", "falhou"], parou: ["ruim", "parou"] };
const PRINTS = [["pc.jpg", "PC"], ["pc-escuro.jpg", "Escuro"], ["tablet.jpg", "Tablet"], ["celular.jpg", "Celular"],
  ["pc-inteira.jpg", "Página inteira"], ["celular-inteira.jpg", "Celular inteira"]];

const site = (url) => { try { return new URL(url).host; } catch { return url ?? ""; } };

// as amostras da paleta: a cor vem do servidor e entra pelo CSSOM (a CSP não deixa style no HTML); um valor
// que o navegador não entende só fica sem cor
function paleta(cores) {
  if (!cores?.length) return null;
  return h("ul", { class: "paleta-receita", "aria-label": "Paleta" }, cores.map((c) => {
    const amostra = h("span", { class: "amostra", "aria-hidden": "true" });
    amostra.style.setProperty("--amostra", c.valor);
    return h("li", { title: [c.nome, c.valor, c.uso].filter(Boolean).join(" · ") }, amostra,
      h("span", { class: "amostra-nome" }, c.nome || c.valor), h("span", { class: "amostra-valor" }, c.valor));
  }));
}

function janelaReceita(r) {
  const figura = h("figure", { class: "print-receita" }, carregando("Carregando o print…"));
  const mostrar = async (arquivo, rotulo) => {
    for (const b of abas.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.print === arquivo));
    figura.replaceChildren(carregando("Carregando o print…"));
    const p = await consultar("receita.print", { nome: r.nome, print: arquivo });
    figura.replaceChildren(p.ok === false ? falha(p) : h("img", {
      src: `data:${p.resultado.tipo};base64,${p.resultado.base64}`, alt: `${r.titulo}: ${rotulo} (o site de origem)`, loading: "lazy" }),
    h("figcaption", null, `${rotulo} · ${site(r.origem)}`));
  };
  const disponiveis = PRINTS.filter(([a]) => r.prints.includes(a));
  const abas = h("div", { class: "abas-print", role: "group", "aria-label": "Prints" }, disponiveis.map(([a, rotulo]) =>
    h("button", { type: "button", class: "discreto", "data-print": a, "aria-pressed": "false", onclick: () => mostrar(a, rotulo) }, rotulo)));
  const texto = h("div", null, carregando("Carregando a receita…"));
  abrirJanela(r.titulo,
    linha("Origem", h("a", { href: r.origem, target: "_blank", rel: "noopener noreferrer" }, r.origem)),
    paleta(r.paleta),
    disponiveis.length ? [abas, figura] : h("p", { class: "fraco" }, "Esta receita não tem prints."),
    texto);
  if (disponiveis.length) mostrar(...disponiveis[0]);
  consultar("receita.ver", { nome: r.nome }).then((v) => texto.replaceChildren(...(v.ok === false ? [falha(v)] : [
    h("details", { open: true }, h("summary", null, "A receita (RECEITA.md)"), h("pre", { class: "texto-receita" }, v.resultado.texto)),
    v.resultado.design && h("details", null, h("summary", null, "O documento de design (DESIGN.md)"),
      h("pre", { class: "texto-receita" }, v.resultado.design)),
    h("p", { class: "fraco" }, `Fica em ${v.resultado.pasta}; o estudo, com a coleta do site, em ${v.resultado.estudo}.`),
  ].filter(Boolean))));
}

function botoes(r) {
  const refazer = async () => {
    if (await mudar("receita.estudar", { url: r.origem, nome: r.nome, refazer: true },
      `Estudar ${site(r.origem)} de novo? A receita atual vale até a nova ficar pronta.`)) atualizar();
  };
  return [
    r.estado === "pronta" && h("button", { type: "button", onclick: () => janelaReceita(r) }, "Ver"),
    r.estado === "pronta" && h("button", { type: "button", class: "discreto", onclick: () => usarReceita(r.nome) }, "Usar num projeto"),
    r.estado !== "estudando" && !r.refazendo && r.origem && h("button", { type: "button", class: "discreto", onclick: refazer },
      r.estado === "pronta" ? "Refazer" : "Tentar de novo"),
    r.estado !== "estudando" && !r.refazendo && h("button", { type: "button", class: "discreto perigo", onclick: async () => {
      if (await mudar("receita.apagar", { nome: r.nome }, `Apagar a receita ${r.nome}? Sem volta; o estudo no lab fica.`)) atualizar();
    } }, "Apagar"),
  ];
}

function itemReceita(r) {
  const [led, estado] = ESTADOS[r.estado] ?? ["apagado", r.estado];
  return item({
    chave: `receita:${r.nome}`,
    led: r.refazendo ? "info" : led,
    nome: h("strong", null, r.titulo || r.nome),
    detalhe: [r.refazendo ? "pronta · estudando de novo" : estado, site(r.origem), r.nome,
      r.atualizada ? data(r.atualizada * 1000) : null, r.trabalho && r.estado === "estudando" ? `trabalho ${r.trabalho}` : null]
      .filter(Boolean).join(" · "),
    acoes: botoes(r),
    rachado: (r.estado === "falhou" || r.estado === "parou") && r.nome,
    extra: [
      r.resumo && h("p", { class: "resumo-receita" }, r.trecho ? r.trecho : r.resumo),
      paleta(r.paleta),
      r.fontes?.length && linha("Fontes", r.fontes.map((f) => [f.familia, f.licenca && `(${f.licenca})`].filter(Boolean).join(" ")).join(", ")),
      r.tags?.length && h("p", { class: "tags-receita" }, r.tags.map((t) => h("span", { class: "selo neutro" }, t))),
      r.estado === "estudando" && h("p", { class: "fraco" }, "O Claude Code está escrevendo a receita; o celular avisa quando ficar pronta. ",
        h("a", { href: "#lab" }, "Ver no Lab")),
      r.erro && h("p", { class: r.estado === "pronta" ? "fraco" : "erro" }, (r.estado === "pronta" ? "A última tentativa falhou: " : "") + r.erro),
    ],
  });
}

function cartaoEstudar(contas) {
  if (!rascunho.conta || !contas.includes(rascunho.conta)) rascunho.conta = "";
  const guardar = (evento) => {
    const f = evento.currentTarget;
    Object.assign(rascunho, { url: f.url.value, nome: f.nome.value, foco: f.foco.value, conta: f.conta.value, modelo: f.modelo.value,
      esforco: f.esforco.value, refazer: f.refazer.checked });
  };
  const opcoes = (nome, lista) => h("select", { name: nome }, lista.map(([v, t]) => h("option", { value: v, selected: v === rascunho[nome] }, t)));
  return cartao("Estudar um site",
    h("form", { class: "resposta", oninput: guardar, onchange: guardar, onsubmit: async (evento) => {
      evento.preventDefault();
      guardar(evento);
      const params = { url: rascunho.url.trim(), ...(rascunho.nome.trim() ? { nome: rascunho.nome.trim() } : {}),
        ...(rascunho.foco.trim() ? { foco: rascunho.foco.trim() } : {}), ...(rascunho.conta ? { conta: rascunho.conta } : {}),
        ...(rascunho.modelo ? { modelo: rascunho.modelo } : {}), ...(rascunho.esforco ? { esforco: rascunho.esforco } : {}),
        ...(rascunho.refazer ? { refazer: true } : {}) };
      const r = await mudar("receita.estudar", params);
      if (r && r.ok !== false) {
        Object.assign(rascunho, { url: "", nome: "", foco: "", refazer: false });
        atualizar();
      }
    } },
      h("div", { class: "campos" },
        campo("Endereço do site", h("input", { name: "url", required: true, value: rascunho.url, placeholder: "https://exemplo.com",
          autocomplete: "off", inputmode: "url", spellcheck: "false" }), true),
        campo("Foco", h("input", { name: "foco", maxlength: "500", value: rascunho.foco, autocomplete: "off",
          placeholder: "opcional: o menu, as animações do topo…" }), true),
        campo("Nome", h("input", { name: "nome", pattern: NOME, value: rascunho.nome, autocomplete: "off",
          placeholder: "vem do site", title: "minúsculas, números e hífen" })),
        campo("Conta", opcoes("conta", [["", "padrão"], ...contas.map((c) => [c, c])])),
        campo("Modelo", opcoes("modelo", [["", "padrão"], ["fable", "fable"], ["opus", "opus"], ["sonnet", "sonnet"], ["haiku", "haiku"]])),
        campo("Esforço", opcoes("esforco", [["", "padrão"], ...["low", "medium", "high", "xhigh", "max"].map((e) => [e, e])]))),
      h("div", { class: "filtros" },
        h("label", { class: "opcao" }, h("input", { type: "checkbox", name: "refazer", checked: rascunho.refazer }), " refazer, se já existir")),
      h("button", { type: "submit", class: "principal" }, "Estudar")),
    h("p", { class: "fraco" }, "O coletor abre o site num navegador sem tela, só pela internet (nunca a rede de casa), e grava prints, "
      + "CSS e medidas, em até 2 minutos. Depois o Claude Code escreve a receita: o que faz aquele visual e como chegar nele do zero, sem copiar."));
}

async function cartaoLista() {
  const r = await consultar(busca ? "receita.procurar" : "receita.lista", busca ? { texto: busca } : {});
  const procurar = h("form", { class: "filtros", role: "search", onsubmit: async (evento) => {
    evento.preventDefault();
    busca = evento.currentTarget.texto.value.trim();
    c.replaceWith(await cartaoLista());
  } },
    campo("Procurar", h("input", { name: "texto", type: "search", value: busca, minlength: "2", maxlength: "200", autocomplete: "off",
      placeholder: "escuro minimalista, serifa…" }), false),
    h("button", { type: "submit", class: "discreto" }, "Procurar"),
    busca && h("button", { type: "button", class: "discreto", onclick: async () => { busca = ""; c.replaceWith(await cartaoLista()); } }, "Todas"));
  procurar.querySelector(".campo")?.classList.add("cresce");
  const lista = r.ok === false ? null : r.resultado.receitas;
  const c = cartao(busca ? `Receitas com “${busca}”` : "Receitas",
    procurar,
    r.ok === false ? [falha(r), semAcao(r, "receita.lista")]
      : itens(lista.map(itemReceita), busca ? vazio("Nenhuma receita combina com isso.", "coruja")
        : vazio("Nenhuma receita ainda. Estude um site que você gostou para começar.", "pega")));
  c.classList.add("largo");   // a lista é o que importa aqui: a largura toda, com o pedido de estudo em cima
  c.append(botaoAtualizar(async () => c.replaceWith(await cartaoLista())));
  return c;
}

export async function telaReceitas() {
  const trabalhos = await consultar("claude.trabalhos");
  const semReceitas = trabalhos.ok !== false && !(trabalhos.resultado.skills ?? []).includes("receita");
  return [
    semReceitas ? cartao("Receitas", h("p", { class: "fraco" },
      "As receitas precisam das skills do Claude Code ligadas no servidor (ATENA_CLAUDE_SKILLS=sim e sudo ./install.sh --lab)."))
      : cartaoEstudar(trabalhos.ok === false ? [] : trabalhos.resultado.contas_com_login ?? []),
    await cartaoLista(),
  ];
}
