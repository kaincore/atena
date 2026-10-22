// Interface do painel: telas montadas com elementos (nunca innerHTML com dados do servidor).
// O visual é o da policromia (estilo.css); os desenhos (o meandro, o templo da entrada) ficam em desenhos.js.
import { $, TIQUE, api, consultar, esqueleto, h, ligarCasca, mudar } from "./comum.js";
import { faixa, prepararTracos, templo } from "./desenhos.js";
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
const reduzido = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const espera = (ms) => new Promise((ok) => setTimeout(ok, reduzido() ? 0 : ms));

function montarNavegacao() {
  const grupos = [...new Set(NAV.map((n) => n.grupo))];
  $("#trilho-grupos").replaceChildren(...grupos.map((g) => h("div", { class: "trilho-grupo" },
    h("h2", null, g), NAV.filter((n) => n.grupo === g).map((n) => tecla(n)))));
  $(".trilho").append(h("span", { class: "pincel", "aria-hidden": "true" }));
  $("#barra").replaceChildren(h("span", { class: "pincel", "aria-hidden": "true" }),
    ...ORDEM_BARRA.map((t) => tecla(NAV.find((n) => n.tela === t))),
    h("button", { type: "button", "data-tela": "mais", onclick: () => $("#mais").showModal() }, picto("mais"), h("span", null, "Mais")));
  $("#mais-teclas").replaceChildren(
    ...NAV.filter((n) => !n.barra).map((n) => tecla(n)),
    h("a", { href: "#", onclick: (e) => { e.preventDefault(); $("#mais").close(); abrirPaleta(); } }, picto("buscar"), h("span", null, "Buscar")));
  $("#mais-teclas").addEventListener("click", (e) => { if (e.target.closest("a[data-tela]")) $("#mais").close(); });
  $("#mais-fechar").addEventListener("click", () => $("#mais").close());
}

function marcarAtiva(nome) {
  const naBarra = ORDEM_BARRA.includes(nome);
  for (const el of document.querySelectorAll("[data-tela]")) {
    const ativa = el.dataset.tela === nome || (el.dataset.tela === "mais" && !naBarra);
    // a tela que fica ativa redesenha o ícone dela
    if (ativa && !el.classList.contains("ativa")) {
      const desenho = el.querySelector(".picto");
      desenho?.classList.remove("redesenha");
      requestAnimationFrame(() => desenho?.classList.add("redesenha"));
      setTimeout(() => desenho?.classList.remove("redesenha"), 700); // o traço tracejado só vale enquanto se desenha
    }
    el.classList.toggle("ativa", ativa);
  }
  posicionarPinceis(true);
}

// o marcador da tela ativa (na barra e no trilho) desliza até ela numa mola suave (a transição está no
// CSS); na primeira vez e quando a janela muda de tamanho, ele só aparece no lugar
function posicionarPinceis(deslizar) {
  for (const [caixa, deitada] of [[$("#barra"), true], [$(".trilho"), false]]) {
    const pincel = caixa.querySelector(".pincel");
    const alvo = caixa.querySelector(".ativa");
    if (!pincel || !alvo || !alvo.offsetWidth) continue;
    const [x, y] = deitada ? [alvo.offsetLeft + 3, alvo.offsetTop + 4] : [alvo.offsetLeft - 4, alvo.offsetTop];
    const [w, hh] = deitada ? [alvo.offsetWidth - 6, alvo.offsetHeight - 8] : [alvo.offsetWidth + 8, alvo.offsetHeight];
    const parado = !deslizar || !pincel.classList.contains("posto");
    pincel.classList.toggle("parado", parado);
    for (const [k, v] of [["--x", x], ["--y", y], ["--largura", w], ["--altura", hh]]) pincel.style.setProperty(k, `${v}px`);
    if (parado) void pincel.offsetWidth; // aplica a posição sem transição antes de ligar a mola de novo
    pincel.classList.add("posto");
    pincel.classList.remove("parado");
  }
}
// o trilho e a barra mudam de tamanho quando os pontos das zonas chegam e quando a letra carrega
const reposicionar = new ResizeObserver(() => posicionarPinceis(false));
for (const el of [$(".trilho-marca"), $("#barra")]) reposicionar.observe(el);
document.fonts?.ready.then(() => posicionarPinceis(false));

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

// a faixa de aprovações que já está na tela fica (se ela acabou de chegar, a luz dela termina de passar);
// a contagem que muda troca a faixa pelo marcarPendentes
const faixaDaTela = () => (telaAtual() === "aprovacoes" ? null : $("#tela .faixa") ?? faixaAprovacoes());

// o cabeçalho de cada tela: o nome e a faixa de meandro, que se desenha ao entrar nela
const cabecalhos = new Map();
function cabecalho(nome, desenhar) {
  if (!cabecalhos.has(nome)) cabecalhos.set(nome, h("header", { class: "cabecalho-tela" }, h("h1", null, NAV.find((n) => n.tela === nome).nome), faixa()));
  const c = cabecalhos.get(nome);
  if (desenhar && !reduzido()) {
    const traco = c.querySelector(".faixa-meandro");
    traco.classList.remove("desenhando");
    traco.style.setProperty("--duracao", "1.1s");
    requestAnimationFrame(() => traco.classList.add("desenhando"));
    setTimeout(() => traco.classList.remove("desenhando"), 1300);
  }
  return c;
}

// o conteúdo que chega no lugar do esqueleto aparece de leve, todo junto (o anel se pinta e a escada se
// assenta); o que chega no meio dessa entrada continua de onde ela estava (ja = quanto já passou)
let entrouEm = 0;
let aberta = null; // a tela aberta (o data-tela do #tela só muda dentro da transição)
function surgir(elementos, ja = 0) {
  const lista = elementos.filter((el) => el instanceof Element);
  for (const el of lista) el.classList.remove("surge");
  if (!lista.length || reduzido()) return;
  void $("#tela").offsetWidth; // para a animação recomeçar nos módulos guardados
  lista.forEach((el, i) => {
    el.style.setProperty("--i", Math.min(i, 6));
    el.style.setProperty("--ja", `${ja}ms`);
    el.classList.add("surge");
  });
}

async function atualizar() {
  const nome = telaAtual();
  const minha = ++geracao;
  marcarAtiva(nome);
  const tela = $("#tela");
  let trocou = null;
  if (aberta !== nome) {
    const anterior = aberta;
    aberta = nome;
    const saindo = [...tela.children].filter((el) => !el.matches(".faixa, .cabecalho-tela"));
    if (anterior && !saindo.some((el) => el.matches(".esqueleto"))) {
      vistas.set(anterior, saindo); // como ficou: inclusive os módulos que se refizeram sozinhos
      rolagens.set(anterior, scrollY);
    }
    const guardada = vistas.get(nome);
    const trocar = () => {
      tela.dataset.tela = nome;
      document.title = `${document.title.match(/^\(\d+\) /)?.[0] ?? ""}${NAV.find((n) => n.tela === nome).nome} · Atena`;
      tela.replaceChildren(...[faixaDaTela(), cabecalho(nome, true), guardada ?? esqueleto()].flat().filter(Boolean));
      scrollTo(0, guardada ? rolagens.get(nome) ?? 0 : 0);
    };
    // trocar de tela é uma transição de vista: a tela velha se apaga e a nova chega de leve (onde o
    // navegador não tem a API, os módulos sobem um a um)
    if (anterior && document.startViewTransition && !reduzido()) trocou = document.startViewTransition(trocar).updateCallbackDone.catch(() => {});
    else {
      trocar();
      if (anterior) surgir(guardada ?? []);
    }
    entrouEm = performance.now();
  }
  tela.setAttribute("aria-busy", "true");
  const conteudo = await montar(nome);
  await trocou;
  if (minha !== geracao || !$("#entrada").hidden) return; // outra tela foi aberta enquanto esta carregava
  const decorrido = performance.now() - entrouEm;
  const eraEsqueleto = [...tela.children].some((el) => el.matches(".esqueleto"));
  manterAbertos([...tela.children], conteudo);
  vistas.set(nome, conteudo);
  tela.replaceChildren(...[faixaDaTela(), cabecalho(nome), conteudo].flat().filter(Boolean));
  if (eraEsqueleto) surgir(conteudo);
  else if (decorrido < 700 && !trocou) surgir(conteudo, Math.round(decorrido));
  tela.removeAttribute("aria-busy");
}

// a entrada: a construção do templo (a geometria, a obra a tinta e ΑΘΗΝΑ letra a letra); na senha
// errada a inscrição fica em cinábrio por um instante, e na certa o tímpano se pinta de azul egípcio
function prepararEntrada() {
  const cena = $(".cena-entrada");
  cena.replaceChildren(prepararTracos(templo()));
  cena.classList.remove("aceita", "recusa");
  if (reduzido()) return;
  $("#entrada").classList.add("construindo");
  setTimeout(() => $("#entrada").classList.remove("construindo"), 4300);
}

function mostrarEntrada() {
  $(".painel").hidden = true;
  $("#tela").replaceChildren();
  delete $("#tela").dataset.tela;
  aberta = null;
  vistas.clear();
  $("#senha").value = "";
  prepararEntrada();
  $("#entrada").hidden = false;
  $("#senha").focus();
}

// as telas da barra ficam prontas em segundo plano depois da primeira: tocar nelas abre na hora,
// mesmo as que esperam o executor (PC e Serviços levam uns 2 s)
async function prepararBarra() {
  for (const nome of ORDEM_BARRA) {
    if (vistas.has(nome) || telaAtual() === nome) continue;
    const conteudo = await montar(nome);
    if (!vistas.has(nome) && telaAtual() !== nome && $("#entrada").hidden) vistas.set(nome, conteudo);
  }
}

// ao chegar, os pontos das zonas se pintam um a um, e o meandro da tela se desenha
async function mostrarPainel(primeira = atualizar()) {
  $("#entrada").hidden = true;
  $(".painel").hidden = false;
  posicionarPinceis(false);
  cabecalho(telaAtual(), true);
  if (telaAtual() !== "aprovacoes") contarPendentes();
  const servicos = await consultar("status.servicos");
  if (servicos.ok !== false) marcarZonas(resumirZonas(servicos.resultado));
  $(".painel").classList.add("chegando");
  setTimeout(() => $(".painel").classList.remove("chegando"), 1600);
  await primeira;
  prepararBarra();
}

$("#form-entrada").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const botao = evento.target.querySelector("button");
  botao.disabled = true;
  const r = await api("POST", "/api/entrar", { senha: $("#senha").value });
  botao.disabled = false;
  if (r.ok === false) {
    $("#msg-entrada").textContent = r.erro;
    // errada: a inscrição fica em cinábrio por um instante
    const cena = $(".cena-entrada");
    cena.classList.remove("recusa");
    requestAnimationFrame(() => cena.classList.add("recusa"));
    setTimeout(() => cena.classList.remove("recusa"), 1600);
    $("#senha").select();
    return;
  }
  $("#senha").value = "";
  $("#msg-entrada").textContent = "";
  // certa: o tímpano se pinta de azul, e a entrada se desfaz para o painel chegar
  $(".cena-entrada").classList.add("aceita");
  await espera(950);
  $("#entrada").classList.add("saindo");
  await espera(420);
  $("#entrada").classList.remove("saindo");
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
  // a contagem das aprovações vale em toda tela (antes, nas que se atualizam sozinhas, ela nunca vinha)
  if (telaAtual() !== "aprovacoes" && tiques % 3 === 0) contarPendentes();
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

// a primeira tela já pede os dados dela junto com a sessão: uma ida a menos pelo Tailscale.
// Sem sessão (401), a api() mostra a entrada e a tela descarta o que chegar.
const eu = api("GET", "/api/eu");
const primeira = atualizar();
if ((await eu).status !== 401) mostrarPainel(primeira); // sem conexão, cada módulo diz o erro
