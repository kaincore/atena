// Agenda: o agendador do painel roda as ações na hora marcada.
import { api, atualizar, avisar, campo, cartao, consultar, data, estadoTexto, falha, h, item, itens, ledEstado, modulo, num,
  numeroGrande, plural } from "../comum.js";
import { relogioDeSol } from "../desenhos.js";

const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
const NOMES_AGENDAVEIS = {
  "pc.ligar": "Ligar o PC", "pc.desligar": "Desligar o PC", "pc.reiniciar": "Reiniciar o PC",
  "servico.reiniciar": "Reiniciar um serviço", "app.reiniciar": "Reiniciar um app do lab",
  "app.parar": "Parar um app do lab", "app.publicar": "Publicar um app do lab",
};
const NOMES_AVISO = { falha: "só se falhar", sempre: "sempre", nunca: "nunca" };

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

const agendaVazia = () => ({ id: null, nome: "", acao: "pc.ligar", alvo: "", tipo: "semana", dias: [1, 2, 3, 4, 5], hora: "19:00",
  em: "", dia: 1, aviso: "falha", tolerancia: 15 });
let agenda = agendaVazia();

function cartaoNovoAgendamento(agendaveis, stacks, projetos) {
  const a = agenda;
  const alvo = agendaveis[a.acao];
  const guardar = (evento) => {
    const f = evento.currentTarget;
    Object.assign(a, {
      nome: f.nome.value, acao: f.acao.value, alvo: f.alvo?.value ?? "", tipo: f.tipo.value, aviso: f.aviso.value,
      tolerancia: Number(f.tolerancia.value), hora: f.hora?.value ?? a.hora, em: f.em?.value ?? a.em, dia: Number(f.dia?.value ?? a.dia),
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
        campo("Fazer", opcoes("acao", Object.keys(agendaveis).map((n) => [n, NOMES_AGENDAVEIS[n] ?? n]), { onchange: muda })),
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
      h("div", { class: "campos" },
        campo("Aviso no celular", opcoes("aviso", Object.entries(NOMES_AVISO))),
        campo("Tolerância", opcoes("tolerancia", [[5, "5 min"], [15, "15 min"], [60, "1 h"], [240, "4 h"]])),
        campo("Nome", h("input", { name: "nome", value: a.nome, maxlength: "80", placeholder: "automático", autocomplete: "off" }))),
      h("div", { class: "botoes" },
        h("button", { type: "submit", class: "principal" }, a.id ? "Gravar" : "Agendar"),
        a.id && h("button", { type: "button", class: "discreto", onclick: () => { agenda = agendaVazia(); refazer(); } }, "Cancelar edição"))),
    h("p", { class: "fraco" }, "Se o painel estiver fora do ar na hora, ele roda até a tolerância depois. Passou dela, a vez fica perdida e o celular fica sabendo: um \"ligar o PC às 19h\" não roda às 3h da manhã."));
  return c;
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
    led: a.ativo ? "ok" : "apagado", nome: h("strong", null, a.nome),
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
  const [r, servicos, apps] = await Promise.all([api("GET", "/api/agendamentos"), consultar("status.servicos"), consultar("app.lista")]);
  if (r.ok === false) return [cartao("Agenda", falha(r))];
  // reiniciar o próprio painel no meio de um agendamento cortaria o agendador
  const stacks = servicos.ok === false ? [] : [...new Set(servicos.resultado.map((c) => c.stack))].filter((s) => s !== "painel").sort();
  const projetos = apps.ok === false ? [] : apps.resultado.projetos.map((p) => p.projeto);
  const rodando = Date.now() - agendaRodouEm < 8000 || r.agendamentos.some((a) => a.execucoes[0]?.estado === "executando");
  const mostradorAgenda = modulo("Agenda", `${plural(r.agendamentos.filter((a) => a.ativo).length, "ativo", "ativos")}`, relogioAgenda(r.agendamentos, rodando));
  mostradorAgenda.classList.add("largo");
  return [
    mostradorAgenda,
    cartaoNovoAgendamento(r.agendaveis, stacks, projetos),
    cartao("Agendamentos", itens(r.agendamentos.map(itemAgendamento), "Nada agendado ainda.")),
  ];
}
