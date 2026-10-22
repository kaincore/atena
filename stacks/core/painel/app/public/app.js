// Interface do painel: telas montadas com elementos (nunca innerHTML com dados do servidor).
// O visual é o de um aparelho (estilo.css); os desenhos do visor ficam em visor.js.
import { $, TIQUE, api, cartao, consultar, esqueleto, falha, h, ligarCasca, mudar } from "./comum.js";
import { telaAgenda } from "./telas/agenda.js";
import { telaAjustes } from "./telas/ajustes.js";
import { contarPendentes, faixaAprovacoes, telaAprovacoes } from "./telas/aprovacoes.js";
import { telaArquivos } from "./telas/arquivos.js";
import { telaAtividade } from "./telas/atividade.js";
import { telaHistorico } from "./telas/historico.js";
import { telaInicio } from "./telas/inicio.js";
import { telaLab } from "./telas/lab.js";
import { marcarPcLigado, telaPC } from "./telas/pc.js";
import { janelaEditor, telaServicos, verLogs } from "./telas/servicos.js";
import { telaSistema } from "./telas/sistema.js";
import { marcarZonas, resumirZonas, stacksVistas } from "./zonas.js";
import { iniciarPaleta } from "./paleta.js";
import { picto } from "./pictos.js";

// as telas e a api() chamam estas três pelo comum.js
ligarCasca({ atualizar, telaAtual, mostrarEntrada });

const TELAS = {
  inicio: telaInicio, aprovacoes: telaAprovacoes, servicos: telaServicos, sistema: telaSistema, pc: telaPC, lab: telaLab,
  agenda: telaAgenda, arquivos: telaArquivos, atividade: telaAtividade, historico: telaHistorico, ajustes: telaAjustes,
};
// de quantos em quantos tiques (10 s) cada tela se atualiza sozinha
const ATUALIZAM_SOZINHAS = { aprovacoes: 1, inicio: 3, servicos: 3, pc: 3 };

// --- navegação: uma lista só para o trilho (PC), a barra e o "Mais" (celular) e a paleta -----------

const NAV = [
  { tela: "inicio", nome: "Início", grupo: "hoje", barra: true },
  { tela: "aprovacoes", nome: "Aprovações", grupo: "hoje" },
  { tela: "agenda", nome: "Agenda", grupo: "hoje", barra: true },
  { tela: "servicos", nome: "Serviços", grupo: "servidor", barra: true },
  { tela: "sistema", nome: "Sistema", grupo: "servidor" },
  { tela: "arquivos", nome: "Arquivos", grupo: "servidor" },
  { tela: "pc", nome: "PC", grupo: "máquina", barra: true },
  { tela: "lab", nome: "Lab", grupo: "máquina" },
  { tela: "atividade", nome: "Atividade", grupo: "registro" },
  { tela: "historico", nome: "Histórico", grupo: "registro" },
  { tela: "ajustes", nome: "Ajustes", grupo: "conta" },
];
const ORDEM_BARRA = ["inicio", "pc", "agenda", "servicos"];

const tecla = (n, classe) => h("a", { href: `#${n.tela}`, "data-tela": n.tela, class: classe }, picto(n.tela), h("span", null, n.nome));

function montarNavegacao() {
  const grupos = [...new Set(NAV.map((n) => n.grupo))];
  $("#trilho-grupos").replaceChildren(...grupos.map((g) => h("div", { class: "trilho-grupo" },
    h("h2", null, g), NAV.filter((n) => n.grupo === g).map((n) => tecla(n)))));
  $("#barra").replaceChildren(
    ...ORDEM_BARRA.map((t) => tecla(NAV.find((n) => n.tela === t))),
    h("button", { type: "button", "data-tela": "mais", onclick: () => $("#mais").showModal() }, picto("mais"), h("span", null, "Mais")));
  $("#mais-teclas").replaceChildren(
    ...NAV.filter((n) => !n.barra).map((n) => tecla(n)),
    h("a", { href: "#", onclick: (e) => { e.preventDefault(); $("#mais").close(); abrirPaleta(); } }, picto("buscar"), h("span", null, "Buscar")));
  $("#mais-teclas").addEventListener("click", (e) => { if (e.target.closest("a[data-tela]")) $("#mais").close(); });
  $("#mais-fechar").addEventListener("click", () => $("#mais").close());
}

function marcarAtiva(nome) {
  for (const el of document.querySelectorAll("[data-tela]")) el.classList.toggle("ativa", el.dataset.tela === nome);
  const naBarra = ORDEM_BARRA.includes(nome);
  document.querySelector('#barra [data-tela="mais"]')?.classList.toggle("ativa", !naBarra);
}

// Ctrl+K: as telas, as ações do PC e, por stack que o painel já viu, logs e reiniciar
const abrirPaleta = iniciarPaleta($("#paleta"), () => [
  ...NAV.map((n) => ({ titulo: n.nome, grupo: "tela", picto: n.tela, acao: () => { location.hash = `#${n.tela}`; } })),
  { titulo: "Ligar o PC", grupo: "pc", picto: "pc", acao: () => mudar("pc.ligar", {}).then((x) => { if (x && x.ok !== false) marcarPcLigado(); }) },
  { titulo: "Desligar o PC", grupo: "pc", picto: "pc", acao: () => mudar("pc.desligar", {}, "Desligar o PC gamer? Ele desliga em 60 s.") },
  { titulo: "Reiniciar o PC", grupo: "pc", picto: "pc", acao: () => mudar("pc.reiniciar", {}, "Reiniciar o PC gamer? Ele reinicia em 60 s.") },
  { titulo: "Novo agendamento", grupo: "agenda", picto: "agenda", acao: () => { location.hash = "#agenda"; } },
  { titulo: "Novo trabalho do Claude Code", grupo: "lab", picto: "lab", acao: () => { location.hash = "#lab"; } },
  ...stacksVistas.flatMap((zs) => {
    const [zona, stack] = zs.split("/");
    return [
      { titulo: `Logs de ${stack}`, grupo: zona, picto: "servicos", acao: () => verLogs(stack) },
      { titulo: `Reiniciar ${stack}`, grupo: zona, picto: "servicos", acao: () => mudar("servico.reiniciar", { stack }, `Reiniciar ${stack}?`) },
      zona === "apps" && { titulo: `Editar a stack ${stack}`, grupo: zona, picto: "servicos", acao: () => janelaEditor(stack) },
    ].filter(Boolean);
  }),
  { titulo: "Sair deste aparelho", grupo: "conta", picto: "sair", acao: async () => { await api("POST", "/api/sair", {}); mostrarEntrada(); } },
]);

let geracao = 0;

function telaAtual() {
  const nome = location.hash.slice(1);
  return TELAS[nome] ? nome : "inicio";
}

// Cada tela guarda os módulos da última vez: voltar a ela mostra na hora o que você viu (na mesma
// altura da rolagem), e o dado novo entra por cima assim que chega. Tela nunca vista abre com o esqueleto.
const vistas = new Map();
const rolagens = new Map();

// o que estava aberto (os "detalhes") continua aberto quando a tela se refaz
function chavesDetalhes(raizes) {
  const vistos = new Map();
  return raizes.flatMap((r) => (r instanceof Element ? [...r.querySelectorAll("details")] : [])).map((d) => {
    const base = `${d.closest(".modulo")?.querySelector(".modulo-topo h2")?.textContent}|${d.querySelector("summary")?.textContent}`;
    vistos.set(base, (vistos.get(base) ?? 0) + 1);
    return [`${base}|${vistos.get(base)}`, d];
  });
}
function manterAbertos(antes, depois) {
  const abertos = new Set(chavesDetalhes(antes).filter(([, d]) => d.open).map(([k]) => k));
  if (abertos.size) for (const [k, d] of chavesDetalhes(depois)) if (abertos.has(k)) d.open = true;
}

const montar = async (nome) => [await TELAS[nome]()].flat(Infinity).filter(Boolean);

async function atualizar() {
  const nome = telaAtual();
  const minha = ++geracao;
  marcarAtiva(nome);
  const tela = $("#tela");
  if (tela.dataset.tela !== nome) {
    const saindo = [...tela.children].filter((el) => !el.matches(".faixa"));
    if (tela.dataset.tela && !saindo.some((el) => el.matches(".esqueleto"))) {
      vistas.set(tela.dataset.tela, saindo); // como ficou: inclusive os módulos que se refizeram sozinhos
      rolagens.set(tela.dataset.tela, scrollY);
    }
    tela.dataset.tela = nome;
    tela.replaceChildren(...[faixaAprovacoes(), vistas.get(nome) ?? esqueleto()].flat().filter(Boolean));
    scrollTo(0, vistas.has(nome) ? rolagens.get(nome) ?? 0 : 0);
  }
  tela.setAttribute("aria-busy", "true");
  const conteudo = await montar(nome);
  if (minha !== geracao || !$("#entrada").hidden) return; // outra tela foi aberta enquanto esta carregava
  manterAbertos([...tela.children], conteudo);
  vistas.set(nome, conteudo);
  tela.replaceChildren(...[faixaAprovacoes(), conteudo].flat().filter(Boolean));
  tela.removeAttribute("aria-busy");
}

function mostrarEntrada() {
  $(".aparelho").hidden = true;
  $("#tela").replaceChildren();
  delete $("#tela").dataset.tela;
  vistas.clear();
  $("#entrada").hidden = false;
  $("#senha").focus();
}

// ao entrar, os LEDs das zonas varrem uma vez: o único momento de abertura
async function mostrarPainel() {
  $("#entrada").hidden = true;
  $(".aparelho").hidden = false;
  atualizar();
  if (telaAtual() !== "aprovacoes") contarPendentes();
  const servicos = await consultar("status.servicos");
  if (servicos.ok !== false) marcarZonas(resumirZonas(servicos.resultado));
  $(".aparelho").classList.add("ligando");
  setTimeout(() => $(".aparelho").classList.remove("ligando"), 1400);
}

$("#form-entrada").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const botao = evento.target.querySelector("button");
  botao.disabled = true;
  const r = await api("POST", "/api/entrar", { senha: $("#senha").value });
  botao.disabled = false;
  if (r.ok === false) {
    $("#msg-entrada").textContent = r.erro;
    return;
  }
  $("#senha").value = "";
  $("#msg-entrada").textContent = "";
  mostrarPainel();
});

$("#janela-fechar").addEventListener("click", () => $("#janela").close());
$("#abrir-paleta").addEventListener("click", () => abrirPaleta());
montarNavegacao();
addEventListener("hashchange", atualizar);
// não apaga uma resposta que você está escrevendo, nem um campo em que você está
function escrevendo() {
  const campo = document.activeElement;
  return [...document.querySelectorAll("#tela textarea")].some((t) => t.value || t === campo)
    || (campo && $("#tela").contains(campo) && /^(INPUT|SELECT|TEXTAREA)$/.test(campo.tagName));
}

let tiques = 0;
setInterval(() => {
  if (document.visibilityState !== "visible" || !$("#entrada").hidden) return;
  tiques++;
  const cada = ATUALIZAM_SOZINHAS[telaAtual()];
  if (cada && tiques % cada === 0 && !$("#janela").open && !escrevendo()) atualizar();
  else if (telaAtual() !== "aprovacoes" && tiques % 3 === 0) contarPendentes();
}, TIQUE);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible") return;
  if ($("#entrada").hidden) atualizar();
  navigator.serviceWorker?.getRegistration().then((r) => r?.update()).catch(() => {}); // o app aberto há dias também vê a versão nova
});

// a casca abre do cache; quando o painel muda no servidor, o sw.js novo instala a versão nova inteira
// e assume a página: recarrega uma vez (se você não estiver escrevendo; senão fica para a próxima)
if ("serviceWorker" in navigator) {
  let controlada = Boolean(navigator.serviceWorker.controller); // a primeira instalação não recarrega
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (controlada && !escrevendo() && !$("#janela").open) location.reload();
    controlada = true;
  });
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

const eu = await api("GET", "/api/eu");
if (eu.ok === false && eu.status !== 401) {
  $("#tela").replaceChildren(cartao("Atena", falha(eu)));
} else if (eu.ok !== false) mostrarPainel();
