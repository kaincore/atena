// Agenda: uma só, com a do painel (o agendador dele roda as ações na hora marcada) e a da Atena (os
// lembretes e pedidos que ela faz na hora, a ronda e o bom-dia, que o executor lê da API dela). O que você
// pede à Atena pelo Telegram aparece aqui, e o que você marca aqui para ela chega pelo Telegram.
import { api, atualizar, avisar, campo, cartao, consultar, data, estadoTexto, falha, h, item, itens, ledEstado, modulo, mudar,
  num, numeroGrande, plural, vazio } from "../comum.js";
import { relogioDeSol } from "../desenhos.js";

const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
const NOMES_AGENDAVEIS = {
  "pc.ligar": "Ligar o PC", "pc.desligar": "Desligar o PC", "pc.reiniciar": "Reiniciar o PC",
  "servico.reiniciar": "Reiniciar um serviço", "app.reiniciar": "Reiniciar um app do lab",
  "app.parar": "Parar um app do lab", "app.publicar": "Publicar um app do lab",
};
const NOMES_AVISO = { falha: "só se falhar", sempre: "sempre", nunca: "nunca" };
// o que a Atena faz na hora: lembrar você (só a mensagem) ou um pedido (ela trabalha, como numa conversa)
const DA_ATENA = { "atena.lembrar": "Lembrar você", "atena.pedir": "Um pedido à Atena" };
const ENTREGAS = { telegram: "pelo Telegram", ntfy: "no celular (ntfy)" };

// a agenda da Atena (atena.agenda) com as horas em ms, como a do painel; sem a Atena, vazia
export function daAtena(r) {
  if (!r || r.ok === false) return [];
  return r.resultado.agendamentos.map((a) => ({ ...a, de: "atena", proxima: a.proxima ? a.proxima * 1000 : null,
    ultima: a.ultima ? a.ultima * 1000 : null }));
}

// o que roda de minutos em minutos (a ronda) fica fora do relógio e dos próximos: seria sempre o próximo
const frequente = (a) => a.de === "atena" && a.intervalo && a.intervalo < 60;

// as próximas vezes das duas agendas, da mais perto para a mais longe
export function proximosDeTodos(painel, atena) {
  const lista = [...(painel?.ok === false || !painel ? [] : painel.agendamentos), ...atena];
  return lista.filter((a) => a.ativo && a.proxima && !frequente(a)).sort((a, b) => a.proxima - b.proxima);
}

export function quandoTexto(ms) {
  const d = new Date(ms);
  const hoje = new Date();
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const dias = Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()) - new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate())) / 86_400_000);
  if (dias === 0) return `hoje às ${hora}`;
  if (dias === 1) return `amanhã às ${hora}`;
  return `${d.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit" })} às ${hora}`;
}

function descreverQuando(q) {
  if (q.tipo === "uma_vez") return `uma vez, ${data(q.em)}`;
  if (q.tipo === "mes") return `todo dia ${q.dia} do mês às ${q.hora}`;
  const dias = [...q.dias].sort().join(",");
  if (dias === "0,1,2,3,4,5,6") return `todo dia às ${q.hora}`;
  if (dias === "1,2,3,4,5") return `dias úteis às ${q.hora}`;
  if (dias === "0,6") return `fins de semana às ${q.hora}`;
  return `${q.dias.map((d) => DIAS[d]).join(", ")} às ${q.hora}`;
}

// "2026-10-21T19:00" no fuso do aparelho, para o campo de data e hora
function paraCampo(ms) {
  const d = new Date(ms);
  const dois = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${dois(d.getMonth() + 1)}-${dois(d.getDate())}T${dois(d.getHours())}:${dois(d.getMinutes())}`;
}

// os dias "1-5" ou "1,3,5" do cron, como lista; null se não for assim
function diasDoCron(campo) {
  const dias = new Set();
  for (const parte of campo.split(",")) {
    const m = parte.match(/^([0-6])(?:-([0-6]))?$/);
    if (!m) return null;
    for (let d = Number(m[1]); d <= Number(m[2] ?? m[1]); d++) dias.add(d);
  }
  return [...dias];
}

// o "quando" da Atena em português: uma vez, a cada tanto, ou o cron de todo dia, da semana ou do mês
function descreverAtena(a) {
  if (a.tipo === "once") return "uma vez";   // a hora vem na próxima
  if (a.tipo === "interval" && a.intervalo) {
    const m = a.intervalo;
    return m % 1440 === 0 ? `a cada ${plural(m / 1440, "dia", "dias")}` : m % 60 === 0 ? `a cada ${m / 60} h` : `a cada ${m} min`;
  }
  const c = (a.quando ?? "").trim().split(/\s+/);
  if (a.tipo === "cron" && c.length === 5 && /^\d+$/.test(c[0]) && /^\d+$/.test(c[1]) && c[3] === "*") {
    const hora = `${c[1].padStart(2, "0")}:${c[0].padStart(2, "0")}`;
    const dias = c[4] === "*" ? [0, 1, 2, 3, 4, 5, 6] : diasDoCron(c[4]);
    if (c[2] === "*" && dias) return descreverQuando({ tipo: "semana", dias, hora });
    if (/^\d+$/.test(c[2]) && c[4] === "*") return `todo dia ${c[2]} do mês às ${hora}`;
  }
  return a.quando ?? "";
}

const agendaVazia = () => ({ id: null, nome: "", acao: "pc.ligar", alvo: "", tipo: "semana", dias: [1, 2, 3, 4, 5], hora: "19:00",
  em: "", dia: 1, aviso: "falha", tolerancia: 15, texto: "", entrega: "telegram" });
let agenda = agendaVazia();

// um agendamento novo da Atena: o quando vira o do Hermes (a data e a hora no fuso do servidor, ou um cron), e
// o texto, o que ela faz na hora
async function agendarParaAtena(a) {
  const [hh, mm] = a.hora.split(":").map(Number);
  let quando;
  if (a.tipo === "uma_vez") {
    if (!a.em || new Date(a.em).getTime() <= Date.now()) return avisar("Escolha um dia e hora no futuro.", "erro");
    quando = a.em;
  } else if (a.tipo === "semana") {
    if (!a.dias.length) return avisar("Escolha ao menos um dia da semana.", "erro");
    quando = `${mm} ${hh} * * ${a.dias.length === 7 ? "*" : [...a.dias].sort().join(",")}`;
  } else quando = `${mm} ${hh} ${a.dia} * *`;
  const texto = a.texto.trim();
  const lembrar = a.acao === "atena.lembrar";
  const prompt = lembrar
    ? `Lembrete que o dono marcou no painel para agora: ${texto}\nMande só o lembrete, curto, no seu tom; não faça mais nada.`
    : `Pedido do dono, agendado no painel: ${texto}`;
  const nome = (a.nome.trim() || `${lembrar ? "lembrete" : "pedido"}: ${texto}`).slice(0, 64);
  const r = await api("POST", "/api/acao/atena.agendar", { params: { nome, quando, texto: prompt, entrega: a.entrega } });
  if (r.ok === false) return avisar(r.erro, "erro");
  const novo = daAtena({ resultado: { agendamentos: [r.resultado.agendamento] } })[0];
  avisar(`Agendado para a Atena: ${novo.nome}${novo.proxima ? `, ${quandoTexto(novo.proxima)}` : ""}`, "ok");
  agenda = agendaVazia();
  atualizar();
}

function cartaoNovoAgendamento(agendaveis, stacks, projetos) {
  const a = agenda;
  const atena = a.acao in DA_ATENA;
  const alvo = atena ? null : agendaveis[a.acao];
  const guardar = (evento) => {
    const f = evento.currentTarget;
    Object.assign(a, {
      nome: f.nome.value, acao: f.acao.value, alvo: f.alvo?.value ?? "", tipo: f.tipo.value, aviso: f.aviso?.value ?? a.aviso,
      tolerancia: Number(f.tolerancia?.value ?? a.tolerancia), hora: f.hora?.value ?? a.hora, em: f.em?.value ?? a.em,
      dia: Number(f.dia?.value ?? a.dia), texto: f.texto?.value ?? a.texto, entrega: f.entrega?.value ?? a.entrega,
      dias: f.querySelector("input[name=dias]") ? [...f.querySelectorAll("input[name=dias]:checked")].map((x) => Number(x.value)) : a.dias,
    });
  };
  const refazer = () => c.replaceWith(cartaoNovoAgendamento(agendaveis, stacks, projetos));
  // mudar a ação ou o tipo troca os campos do formulário
  const muda = (evento) => { guardar({ currentTarget: evento.currentTarget.form }); refazer(); };
  const opcoes = (nome, lista, extra = {}) => h("select", { name: nome, ...extra }, lista.map(([v, t]) =>
    h("option", { value: String(v), selected: String(v) === String(a[nome]) }, t)));
  const alvos = alvo === "stack" ? stacks : alvo === "projeto" ? projetos : [];
  if (alvo && !alvos.includes(a.alvo)) a.alvo = alvos[0] ?? "";
  const dias = (lista) => () => { a.dias = lista; refazer(); };
  const c = cartao(a.id ? `Editar agendamento` : "Novo agendamento",
    h("form", { class: "resposta", oninput: guardar, onchange: guardar, onsubmit: async (evento) => {
      evento.preventDefault();
      guardar(evento);
      if (atena) return agendarParaAtena(a);
      const quando = a.tipo === "uma_vez" ? { tipo: "uma_vez", em: new Date(a.em).getTime() }
        : a.tipo === "semana" ? { tipo: "semana", dias: a.dias, hora: a.hora } : { tipo: "mes", dia: a.dia, hora: a.hora };
      const r = await api("POST", "/api/agendamentos/salvar", {
        ...(a.id ? { id: a.id } : {}), nome: a.nome, acao: a.acao, params: alvo ? { [alvo]: a.alvo } : {}, quando,
        aviso: a.aviso, tolerancia: a.tolerancia,
      });
      if (r.ok === false) return avisar(r.erro, "erro");
      avisar(`Agendado: ${r.agendamento.nome}, ${quandoTexto(r.agendamento.proxima)}`, "ok");
      agenda = agendaVazia();
      atualizar();
    } },
      h("div", { class: "campos" },
        // editando um do painel, ele continua do painel
        campo("Fazer", h("select", { name: "acao", onchange: muda },
          h("optgroup", { label: "O painel faz" }, Object.keys(agendaveis).map((n) =>
            h("option", { value: n, selected: n === a.acao }, NOMES_AGENDAVEIS[n] ?? n))),
          !a.id && h("optgroup", { label: "A Atena faz" }, Object.entries(DA_ATENA).map(([n, t]) =>
            h("option", { value: n, selected: n === a.acao }, t))))),
        alvo && campo(alvo === "stack" ? "Serviço" : "App", alvos.length ? opcoes("alvo", alvos.map((x) => [x, x]))
          : h("input", { name: "alvo", value: a.alvo, required: true, autocomplete: "off" })),
        campo("Quando", opcoes("tipo", [["semana", "toda semana"], ["mes", "todo mês"], ["uma_vez", "uma vez"]], { onchange: muda })),
        a.tipo === "uma_vez" && campo("Dia e hora", h("input", { type: "datetime-local", name: "em", value: a.em, required: true })),
        a.tipo === "mes" && campo("Dia do mês", h("input", { type: "number", name: "dia", min: "1", max: "31", value: String(a.dia), required: true })),
        a.tipo !== "uma_vez" && campo("Às", h("input", { type: "time", name: "hora", value: a.hora, required: true }))),
      a.tipo === "semana" && h("div", { class: "campo largo", role: "group", "aria-label": "Dias da semana" },
        h("span", { class: "rotulo" }, "Dias"),
        h("div", { class: "travas" },
          DIAS.map((d, i) => h("label", { class: "trava" },
            h("input", { type: "checkbox", name: "dias", value: String(i), checked: a.dias.includes(i) }), h("span", null, d))),
          h("button", { type: "button", class: "discreto", onclick: dias([1, 2, 3, 4, 5]) }, "Dias úteis"),
          h("button", { type: "button", class: "discreto", onclick: dias([0, 1, 2, 3, 4, 5, 6]) }, "Todo dia"))),
      atena && campo(a.acao === "atena.lembrar" ? "O lembrete" : "O pedido", h("textarea", { name: "texto", rows: "3",
        maxlength: "3000", required: true, placeholder: a.acao === "atena.lembrar"
          ? "tomar o remédio, pagar a luz, ligar para alguém…" : "confira os discos e me diga se algo preocupa…" }, a.texto), true),
      h("div", { class: "campos" },
        atena ? campo("Entrega", opcoes("entrega", Object.entries(ENTREGAS)))
          : [campo("Aviso no celular", opcoes("aviso", Object.entries(NOMES_AVISO))),
            campo("Tolerância", opcoes("tolerancia", [[5, "5 min"], [15, "15 min"], [60, "1 h"], [240, "4 h"]]))],
        campo("Nome", h("input", { name: "nome", value: a.nome, maxlength: atena ? "64" : "80", placeholder: "automático", autocomplete: "off" }))),
      h("div", { class: "botoes" },
        h("button", { type: "submit", class: "principal" }, a.id ? "Gravar" : "Agendar"),
        a.id && h("button", { type: "button", class: "discreto", onclick: () => { agenda = agendaVazia(); refazer(); } }, "Cancelar edição"))),
    h("p", { class: "fraco" }, atena
      ? "Na hora, a Atena manda a mensagem. Um lembrete de uma vez some da lista uma hora depois de avisar; os de toda semana ou todo mês continuam."
      : "Se o painel estiver fora do ar na hora, ele roda até a tolerância depois. Passou dela, a vez fica perdida e o celular fica sabendo: um \"ligar o PC às 19h\" não roda às 3h da manhã."));
  return c;
}

// um agendamento da Atena: o que ela faz, quando, a última vez e como você recebe; a ronda e o bom-dia são do
// instalador e não se apagam (dá para pausar)
function itemAtena(a) {
  const fazer = (oque, pergunta) => async () => {
    const r = await mudar("atena.agendamento", { id: a.id, fazer: oque }, pergunta);
    if (!r || r.ok === false) return;
    if (oque === "rodar") agendaRodouEm = Date.now();
    atualizar();
  };
  const falhou = a.resultado && a.resultado !== "ok";
  return item({
    led: !a.ativo ? "apagado" : falhou ? "ruim" : "ok", chave: `atena:${a.id}`,
    nome: [h("strong", null, a.nome), h("span", { class: "selo neutro" }, "Atena")],
    detalhe: [
      h("div", null, [!a.ativo && "pausado", descreverAtena(a), a.sem_ia ? "sem IA" : null, ENTREGAS[a.entrega] ?? a.entrega]
        .filter(Boolean).join(" · ")),
      h("div", null, [a.ativo && a.proxima && `próxima: ${quandoTexto(a.proxima)}`,
        a.ultima && `última: ${data(a.ultima)} (${a.resultado === "ok" ? "deu certo" : a.resultado ?? "—"})`,
        a.feitas ? `${plural(a.feitas, "vez", "vezes")} até agora` : null].filter(Boolean).join(" · ")),
    ],
    acoes: [
      h("button", { type: "button", class: "discreto", onclick: fazer("rodar", `A Atena faz "${a.nome}" agora?`) }, "Rodar agora"),
      h("button", { type: "button", class: "discreto", onclick: fazer(a.ativo ? "pausar" : "retomar") }, a.ativo ? "Pausar" : "Retomar"),
      !a.protegido && h("button", { type: "button", class: "discreto perigo",
        onclick: fazer("apagar", `Apagar "${a.nome}" da agenda da Atena?`) }, "Apagar"),
    ],
    extra: (a.texto || a.script || a.erro) && h("details", null, h("summary", null, a.texto ? "O que ela faz" : "Detalhes"),
      a.texto && h("p", { class: "fraco resumo" }, a.texto),
      a.script && h("p", { class: "fraco" }, `${a.sem_ia ? "Só o script" : "Antes, o script"} ${a.script}`),
      a.erro && h("p", { class: "erro" }, a.erro)),
  });
}

function itemAgendamento(a) {
  const feito = !a.ativo && a.proxima === null && a.quando.tipo === "uma_vez";
  const fazer = (caminho, corpo, pergunta) => async () => {
    if (pergunta && !confirm(pergunta)) return;
    const r = await api("POST", caminho, corpo);
    if (r.ok === false) return avisar(r.erro, "erro");
    if (caminho.endsWith("/rodar")) {
      agendaRodouEm = Date.now();
      avisar(`${a.nome}: começou`, "ok");
      setTimeout(atualizar, 3000);
    } else atualizar();
  };
  return item({
    led: a.ativo ? "ok" : "apagado", nome: [h("strong", null, a.nome), h("span", { class: "selo" }, "painel")], chave: `painel:${a.id}`,
    detalhe: [
      h("div", null, `${a.ativo ? "" : feito ? "feito · " : "pausado · "}${descreverQuando(a.quando)} · aviso ${NOMES_AVISO[a.aviso]} · tolerância ${a.tolerancia} min`),
      h("div", null, [a.ativo && a.proxima && `próxima: ${quandoTexto(a.proxima)}`, a.ultima && `última: ${data(a.ultima)} (${estadoTexto(a.ultimo_estado)})`].filter(Boolean).join(" · ")),
    ],
    acoes: [
      h("button", { type: "button", class: "discreto", onclick: fazer("/api/agendamentos/rodar", { id: a.id }, `Rodar "${a.nome}" agora?`) }, "Rodar agora"),
      !feito && h("button", { type: "button", class: "discreto", onclick: fazer("/api/agendamentos/ativar", { id: a.id, ativo: !a.ativo }) }, a.ativo ? "Pausar" : "Retomar"),
      h("button", { type: "button", class: "discreto", onclick: () => {
        const q = a.quando;
        agenda = { ...agendaVazia(), id: a.id, nome: a.nome, acao: a.acao, alvo: Object.values(a.params)[0] ?? "", tipo: q.tipo,
          dias: q.dias ?? [1, 2, 3, 4, 5], hora: q.hora ?? "19:00", em: q.em ? paraCampo(q.em) : "", dia: q.dia ?? 1,
          aviso: a.aviso, tolerancia: a.tolerancia };
        atualizar();
        scrollTo({ top: 0, behavior: "smooth" });
      } }, "Editar"),
      h("button", { type: "button", class: "discreto perigo", onclick: fazer("/api/agendamentos/apagar", { id: a.id }, `Apagar "${a.nome}"?`) }, "Apagar"),
    ],
    extra: a.execucoes.length > 0 && h("details", null, h("summary", null, "Últimas execuções"),
      itens(a.execucoes.map((x) => item({
        led: ledEstado(x.estado), nome: data(x.quando), detalhe: estadoTexto(x.estado),
        extra: x.resumo && h("div", { class: "fraco resumo" }, x.resumo),
      })), null, "sub")),
  });
}

let agendaRodouEm = 0;

// o relógio de sol (a sombra gira uma volta quando um agendamento roda), a próxima vez e as das 24 h
function relogioAgenda(agendamentos, girando) {
  const proximos = agendamentos.filter((a) => a.ativo && a.proxima).sort((a, b) => a.proxima - b.proxima);
  const nas24h = proximos.filter((a) => a.proxima - Date.now() < 24 * 3600_000).length;
  const proxima = proximos[0];
  return h("div", { class: "agenda-mostrador" }, relogioDeSol(agendamentos, girando),
    h("div", { class: "agenda-leituras" },
      h("div", { class: "leitura" }, h("span", { class: "rotulo" }, "Próxima vez"),
        numeroGrande(proxima ? new Date(proxima.proxima).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "—"),
        h("span", { class: "fraco" }, proxima ? `${proxima.nome} · ${quandoTexto(proxima.proxima)}` : "nada agendado")),
      h("div", { class: "leitura" }, h("span", { class: "rotulo" }, "Nas próximas 24 h"),
        numeroGrande(num(nas24h), nas24h === 1 ? "agendamento" : "agendamentos"))));
}

export async function telaAgenda() {
  const [r, servicos, apps, ra] = await Promise.all([api("GET", "/api/agendamentos"), consultar("status.servicos"),
    consultar("app.lista"), consultar("atena.agenda")]);
  if (r.ok === false) return [cartao("Agenda", falha(r))];
  // reiniciar o próprio painel no meio de um agendamento cortaria o agendador
  const stacks = servicos.ok === false ? [] : [...new Set(servicos.resultado.map((c) => c.stack))].filter((s) => s !== "painel").sort();
  const projetos = apps.ok === false ? [] : apps.resultado.projetos.map((p) => p.projeto);
  const atena = daAtena(ra);
  const rodando = Date.now() - agendaRodouEm < 8000 || r.agendamentos.some((a) => a.execucoes[0]?.estado === "executando");
  const ativos = r.agendamentos.filter((a) => a.ativo).length + atena.filter((a) => a.ativo).length;
  const mostradorAgenda = modulo("Agenda", plural(ativos, "ativo", "ativos"), relogioAgenda(proximosDeTodos(r, atena), rodando));
  mostradorAgenda.classList.add("largo");
  // uma lista só: os ativos pela próxima vez, o que roda de minutos em minutos depois, os pausados no fim.
  // Sem a Atena (não instalada, ou o token antigo, sem a ação), só a do painel
  const todos = [...r.agendamentos.map((a) => ({ ...a, de: "painel" })), ...atena].sort((a, b) =>
    (b.ativo - a.ativo) || (frequente(a) - frequente(b)) || ((a.proxima ?? Infinity) - (b.proxima ?? Infinity)));
  const semAtena = ra.ok === false && ra.status !== 403 && ra.status !== 404
    && h("p", { class: "fraco" }, `A agenda da Atena não respondeu agora: ${ra.erro}`);
  return [
    mostradorAgenda,
    cartaoNovoAgendamento(r.agendaveis, stacks, projetos),
    cartao("Agendamentos", itens(todos.map((a) => (a.de === "atena" ? itemAtena(a) : itemAgendamento(a))),
      vazio("Nada agendado ainda.", "galo")), semAtena),
  ];
}
