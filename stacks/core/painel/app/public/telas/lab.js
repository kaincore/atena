// Lab: os apps que o Claude Code fez e os trabalhos dele.
import { $, abrirJanela, atualizar, botaoAtualizar, campo, cartao, consultar, estadoTexto, falha, h, item, itens, ledEstado, linha,
  mudar, semAcao, statusDocker, carregando } from "../comum.js";

const NOME_PROJETO = "[a-z0-9][a-z0-9\\-]{0,39}";
const rascunho = { projeto: "", pedido: "", conta: "", modelo: "", esforco: "", minutos: "60", somente_plano: false, publicar: false,
  skill: "", continuar: null };

// as teclas de um app; cada uma confirma, pede e recarrega a tela
function botoesApp(p) {
  const publicado = p.app !== "não publicado";
  const noAr = /^Up/.test(p.app);
  const fazer = (nome, pergunta, params = {}) => async () => {
    if (await mudar(nome, { projeto: p.projeto, ...params }, pergunta)) atualizar();
  };
  return [
    p.em_andamento && h("button", { type: "button", class: "discreto", onclick: fazer("app.cancelar",
      `Parar o que está em andamento em ${p.projeto} (trabalho do Claude Code, construção ou pedido esperando o celular)?`) }, "Cancelar"),
    p.codigo && !p.em_andamento && h("button", { type: "button", onclick: fazer("app.publicar",
      `${publicado ? "Publicar de novo" : "Publicar"} ${p.projeto} na rede de casa? Constrói pelo Dockerfile; pode levar alguns minutos.`) },
      publicado ? "Publicar de novo" : "Publicar"),
    publicado && h("button", { type: "button", class: "discreto", onclick: fazer("app.reiniciar", `Reiniciar o app ${p.projeto}?`) }, "Reiniciar"),
    noAr && h("button", { type: "button", class: "discreto", onclick: fazer("app.parar", `Tirar o app ${p.projeto} do ar? Os dados ficam.`) }, "Parar"),
    noAr && h("button", { type: "button", class: "discreto", onclick: () => janelaComando(p.projeto) }, "Comando"),
    !p.em_andamento && h("button", { type: "button", class: "discreto perigo", onclick: () => janelaApagar(p) }, "Apagar"),
  ];
}

function janelaComando(projeto) {
  const saida = h("div");
  const campo = h("input", { name: "comando", required: true, placeholder: "ex.: ls -la /data", autocomplete: "off" });
  abrirJanela(`Comando em ${projeto}`,
    h("p", { class: "fraco" }, "Roda dentro do container do app, como o usuário dele (sh -c), por até 30 s. Fica no histórico."),
    h("form", { class: "resposta", onsubmit: async (evento) => {
      evento.preventDefault();
      const botao = evento.currentTarget.querySelector("button");
      botao.disabled = true;
      saida.replaceChildren(carregando("Rodando…"));
      const r = await consultar("app.comando", { projeto, comando: campo.value });
      botao.disabled = false;
      saida.replaceChildren(...(r.ok === false ? [falha(r)] : [
        linha("Código de saída", h("span", { class: `selo ${r.resultado.codigo === 0 ? "ok" : "ruim"}` }, String(r.resultado.codigo))),
        h("pre", { class: "log" }, r.resultado.saida || "(sem saída)"),
        r.resultado.dica && h("p", { class: "fraco" }, r.resultado.dica),
      ].filter(Boolean)));
    } }, campo, h("button", { type: "submit", class: "principal" }, "Rodar")),
    saida);
  campo.focus();
}

function janelaApagar(p) {
  const publicado = p.app !== "não publicado";
  const opcao = (valor, texto, marcado) => h("label", { class: "opcao" },
    h("input", { type: "checkbox", name: "partes", value: valor, checked: marcado }), ` ${texto}`);
  const confirmacao = h("input", { name: "nome", autocomplete: "off", placeholder: p.projeto });
  const aviso = h("p", { class: "erro" });
  const form = h("form", { class: "resposta", onsubmit: async (evento) => {
    evento.preventDefault();
    const partes = [...form.querySelectorAll("input[name=partes]:checked")].map((x) => x.value);
    if (!partes.length) return void (aviso.textContent = "Escolha o que apagar.");
    if (partes.includes("dados") && confirmacao.value.trim() !== p.projeto)
      return void (aviso.textContent = `Para apagar os dados, digite ${p.projeto}.`);
    $("#janela").close();
    if (await mudar("app.apagar", { projeto: p.projeto, partes })) atualizar();
  } },
    publicado && opcao("docker", "Tirar do Docker: o container e a imagem (publicar de novo reconstrói)", true),
    p.codigo && opcao("codigo", "Código: vai para a lixeira, onde dá para restaurar por 30 dias", !publicado),
    p.dados_guardados && [opcao("dados", "Dados do app (sai do Docker junto): NÃO TEM VOLTA", false),
      h("label", null, `Para apagar os dados, digite ${p.projeto}: `, confirmacao)],
    aviso,
    h("button", { type: "submit", class: "perigo" }, "Apagar"));
  abrirJanela(`Apagar ${p.projeto}`, form);
}

const ESTADOS_TRABALHO = { planejando: "planejando", executando: "rodando", aguardando: "esperando o celular" };

function itemTrabalho(t) {
  const rodando = t.estado === "planejando" || t.estado === "executando";
  const quem = t.cliente && t.cliente !== "painel" ? (t.cliente === "hermes" ? "pela Atena" : `por ${t.cliente}`) : null;
  return item({
    led: ESTADOS_TRABALHO[t.estado] ? "info" : ledEstado(t.estado), nome: h("strong", null, t.projeto ?? "?"),
    detalhe: [ESTADOS_TRABALHO[t.estado] ?? estadoTexto(t.estado), quem, t.conta, t.modelo, t.esforco, t.criado, `trabalho ${t.id}`,
      t.commits ? `${t.commits} commits` : null].filter(Boolean).join(" · "),
    acoes: [
      rodando && h("button", { type: "button", class: "discreto", onclick: async () => {
        if (await mudar("claude.cancelar", { pedido: t.id }, `Interromper o trabalho ${t.id} em ${t.projeto}? A conversa fica guardada.`)) atualizar();
      } }, "Cancelar"),
      t.continuavel && h("button", { type: "button", class: "discreto", onclick: () => {
        Object.assign(rascunho, { continuar: t.id, projeto: t.projeto, conta: t.conta ?? rascunho.conta, pedido: "", publicar: false });
        atualizar();
        scrollTo({ top: 0, behavior: "smooth" });
      } }, "Continuar"),
    ],
    extra: [
      h("p", { class: "pedido-trabalho" }, t.pedido),
      t.esperando_permissao_no_celular && h("p", null, h("a", { href: "#aprovacoes" }, "Esperando a sua permissão: ver em Aprovações")),
      t.resumo && h("details", null, h("summary", null, "Resumo"), h("pre", { class: "texto-pedido" }, t.resumo)),
    ],
  });
}

function cartaoNovoTrabalho(trabalhos, projetos) {
  const contas = trabalhos.contas_com_login ?? [];
  if (!rascunho.conta || !contas.includes(rascunho.conta)) rascunho.conta = contas[0] ?? "";
  const guardar = (evento) => {
    const f = evento.currentTarget;
    Object.assign(rascunho, {
      projeto: f.projeto.value, pedido: f.pedido.value, conta: f.conta.value, modelo: f.modelo.value, esforco: f.esforco.value,
      minutos: f.minutos.value, somente_plano: f.somente_plano.checked, publicar: f.publicar.checked, skill: f.skill?.value ?? "",
    });
  };
  const continuando = rascunho.continuar;
  const opcoes = (nome, lista) => h("select", { name: nome }, lista.map(([v, t]) => h("option", { value: v, selected: v === rascunho[nome] }, t)));
  const marcar = (nome, texto) => h("label", { class: "opcao" }, h("input", { type: "checkbox", name: nome, checked: rascunho[nome] }), ` ${texto}`);
  const c = cartao(continuando ? "Continuar trabalho do Claude Code" : "Novo trabalho do Claude Code",
    contas.length ? null : h("p", { class: "erro" }, "Nenhuma conta do Claude Code com login no servidor (sudo atena-claude-conta entrar <conta>)."),
    continuando && h("div", { class: "stack-topo" },
      h("p", { class: "fraco" }, `Continuando o trabalho ${continuando} em ${rascunho.projeto}: a conversa vem junto.`),
      h("button", { type: "button", class: "discreto", onclick: () => {
        Object.assign(rascunho, { continuar: null, projeto: "" });
        c.replaceWith(cartaoNovoTrabalho(trabalhos, projetos));
      } }, "Começar um novo")),
    h("form", { class: "resposta", oninput: guardar, onchange: guardar, onsubmit: async (evento) => {
      evento.preventDefault();
      guardar(evento);
      const params = { projeto: rascunho.projeto.trim(), pedido: rascunho.pedido.trim(), conta: rascunho.conta, minutos: Number(rascunho.minutos),
        ...(rascunho.modelo ? { modelo: rascunho.modelo } : {}), ...(rascunho.esforco ? { esforco: rascunho.esforco } : {}),
        ...(rascunho.somente_plano ? { somente_plano: true } : {}), ...(rascunho.publicar ? { publicar: true } : {}),
        ...(rascunho.skill ? { skill: rascunho.skill } : {}), ...(continuando ? { continuar: continuando } : {}) };
      const r = await mudar("claude.tarefa", params, null, false);
      if (r && r.ok !== false) {
        Object.assign(rascunho, { projeto: "", pedido: "", somente_plano: false, publicar: false, skill: "", continuar: null });
        atualizar();
      }
    } },
      h("div", { class: "campos" },
        campo("Projeto", h("input", { name: "projeto", list: "projetos-lab", required: true, pattern: NOME_PROJETO,
          value: rascunho.projeto, placeholder: "lista-compras", autocomplete: "off", title: "minúsculas, números e hífen", readonly: Boolean(continuando) }), true),
        h("datalist", { id: "projetos-lab" }, projetos.map((p) => h("option", { value: p.projeto }))),
        campo("Pedido", h("textarea", { name: "pedido", rows: "4", minlength: "3", maxlength: "4000", required: true,
          placeholder: continuando ? "O que ele deve fazer agora" : "O que o Claude Code deve fazer (um nome de projeto novo cria a pasta)" }, rascunho.pedido), true),
        campo("Conta", opcoes("conta", contas.map((c) => [c, c]))),
        campo("Modelo", opcoes("modelo", [["", "padrão"], ["fable", "fable"], ["opus", "opus"], ["sonnet", "sonnet"], ["haiku", "haiku"]])),
        campo("Esforço", opcoes("esforco", [["", "padrão"], ...["low", "medium", "high", "xhigh", "max"].map((e) => [e, e])])),
        campo("Tempo", opcoes("minutos", [["15", "15 min"], ["30", "30 min"], ["60", "1 h"], ["120", "2 h"], ["240", "4 h"], ["600", "10 h"]])),
        // só o executor do servidor de origem tem skills do Claude Code; nos outros, o campo não aparece
        trabalhos.skills && campo("Skill", opcoes("skill", [["", "nenhuma"], ...trabalhos.skills.map((s) => [s, s])]))),
      h("div", { class: "filtros" },
        marcar("somente_plano", "só planejar (não muda nada)"),
        marcar("publicar", "publicar quando terminar bem")),
      h("button", { type: "submit", class: "principal", disabled: !contas.length }, continuando ? "Continuar" : "Mandar")),
    h("p", { class: "fraco" }, "O Claude Code trabalha sozinho na pasta do projeto, sem sudo e sem Docker. As permissões e perguntas dele aparecem em Aprovações e no celular."));
  return c;
}

async function cartaoTrabalhos(trabalhos) {
  const c = trabalhos.ok === false ? cartao("Trabalhos do Claude Code", falha(trabalhos), semAcao(trabalhos, "claude.trabalhos"))
    : cartao("Trabalhos do Claude Code", itens(trabalhos.resultado.trabalhos.map(itemTrabalho), "Nenhum trabalho ainda."));
  c.append(botaoAtualizar(async () => c.replaceWith(await cartaoTrabalhos(await consultar("claude.trabalhos")))));
  return c;
}

export async function telaLab() {
  const [r, trabalhos] = await Promise.all([consultar("app.lista"), consultar("claude.trabalhos")]);
  if (r.ok === false) return [cartao("Lab", falha(r))];
  const { projetos, lixeira } = r.resultado;
  const apps = cartao("Apps do lab", itens(projetos.map((p) => item({
    led: p.em_andamento ? "info" : /^Up/.test(p.app) ? (/unhealthy/.test(p.app) ? "ruim" : "ok") : "apagado",
    nome: h("strong", null, p.projeto),
    detalhe: [p.em_andamento ? `em andamento: pedido ${p.em_andamento}` : statusDocker(p.app),
      p.codigo ? "código" : "sem código", p.dados_guardados ? "dados guardados" : "sem dados"].join(" · "),
    acoes: botoesApp(p),
    extra: [
      p.fora_de_casa && linha("Endereço", h("a", { href: p.fora_de_casa, target: "_blank", rel: "noopener" }, p.fora_de_casa)),
      p.endereco && linha("Na rede de casa", h("a", { href: p.endereco, target: "_blank", rel: "noopener" }, p.endereco)),
    ],
  })), "Nenhum projeto no lab ainda. Mande um trabalho ao Claude Code para começar."));
  return [
    trabalhos.ok === false ? null : cartaoNovoTrabalho(trabalhos.resultado, projetos),
    await cartaoTrabalhos(trabalhos),
    apps,
    lixeira.length ? cartao("Lixeira", itens(lixeira.map((l) => item({
      nome: l.projeto, detalhe: `apagado em ${l.apagado_em} · some de vez em ${l.some_de_vez_em}`,
      acoes: h("button", { type: "button", class: "discreto", onclick: async () => {
        if (await mudar("app.restaurar", { projeto: l.projeto }, `Trazer o código de ${l.projeto} de volta da lixeira?`)) atualizar();
      } }, "Restaurar"),
    })))) : null,
  ];
}
