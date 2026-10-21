// Agendador: a próxima vez, a validação da tela e o tique (rodar, perder, avisar), com relógio falso.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Agendador, ler, proxima, validar, type Quando } from "../src/agendador.ts";
import { Banco } from "../src/banco.ts";

const em = (...partes: number[]) => new Date(partes[0], partes[1], partes[2], partes[3] ?? 0, partes[4] ?? 0).getTime();
const UTEIS = [1, 2, 3, 4, 5];

test("toda semana: mais tarde no mesmo dia, ou o próximo dia escolhido", () => {
  const quarta = new Date(2026, 9, 21);
  assert.equal(quarta.getDay(), 3);
  const q: Quando = { tipo: "semana", dias: UTEIS, hora: "19:00" };
  assert.equal(proxima(q, em(2026, 9, 21, 18, 0)), em(2026, 9, 21, 19, 0));
  assert.equal(proxima(q, em(2026, 9, 21, 19, 0)), em(2026, 9, 22, 19, 0), "na hora exata, já é a próxima");
  assert.equal(proxima(q, em(2026, 9, 23, 20, 0)), em(2026, 9, 26, 19, 0), "sexta à noite: segunda");
  assert.equal(proxima({ tipo: "semana", dias: [3], hora: "08:30" }, em(2026, 9, 21, 9, 0)), em(2026, 9, 28, 8, 30), "a mesma quarta, uma semana depois");
});

test("todo mês: dia 31 cai no último dia dos meses mais curtos", () => {
  const q: Quando = { tipo: "mes", dia: 31, hora: "03:00" };
  assert.equal(proxima(q, em(2027, 1, 1)), em(2027, 1, 28, 3, 0));
  assert.equal(proxima(q, em(2027, 1, 28, 4, 0)), em(2027, 2, 31, 3, 0));
  assert.equal(proxima({ tipo: "mes", dia: 1, hora: "08:00" }, em(2026, 11, 15)), em(2027, 0, 1, 8, 0), "vira o ano");
});

test("uma vez: só se ainda não passou", () => {
  assert.equal(proxima({ tipo: "uma_vez", em: 2000 }, 1000), 2000);
  assert.equal(proxima({ tipo: "uma_vez", em: 1000 }, 1000), null);
});

test("validar: só ações da lista, com o alvo, e um nome automático", () => {
  const ok = validar({ acao: "servico.reiniciar", params: { stack: "arca" }, quando: { tipo: "semana", dias: [0, 6, 6], hora: "03:00" } });
  assert.equal(ok.nome, "Reiniciar arca");
  assert.deepEqual(ok.quando, { tipo: "semana", dias: [0, 6], hora: "03:00" });
  assert.equal(ok.aviso, "falha");
  assert.equal(ok.tolerancia, 15);
  const erros: [Record<string, unknown>, RegExp][] = [
    [{ acao: "app.apagar", params: { projeto: "x" } }, /não dá para agendar/],
    [{ acao: "servico.reiniciar", params: {} }, /escolha o stack/],
    [{ acao: "servico.reiniciar", params: { stack: "../etc" } }, /escolha o stack/],
    [{ acao: "pc.ligar", quando: { tipo: "semana", dias: [], hora: "19:00" } }, /pelo menos um dia/],
    [{ acao: "pc.ligar", quando: { tipo: "semana", dias: [1], hora: "25:00" } }, /hora/],
    [{ acao: "pc.ligar", quando: { tipo: "mes", dia: 32, hora: "10:00" } }, /dia do mês/],
    [{ acao: "pc.ligar", quando: { tipo: "uma_vez", em: 1 }, aviso: "talvez" }, /aviso/],
    [{ acao: "pc.ligar", quando: { tipo: "toda hora" } }, /quando/],
  ];
  for (const [entrada, erro] of erros) assert.throws(() => validar(entrada), erro, JSON.stringify(entrada));
});

// executor falso: devolve o que estiver em respostas[caminho] e guarda as chamadas
function montar(respostas: Record<string, { status: number; corpo: Record<string, unknown> }>) {
  const banco = new Banco(":memory:");
  const chamadas: { metodo: string; caminho: string; corpo: any }[] = [];
  let agora = em(2026, 9, 21, 19, 1);
  const agendador = new Agendador(banco, async (metodo, caminho, corpo) => {
    chamadas.push({ metodo, caminho, corpo });
    const chave = caminho.split("?")[0];
    return respostas[chave] ?? { status: 200, corpo: { ok: true, resultado: { eco: true } } };
  }, () => agora, 0);
  const criar = (acao: string, quando: Quando, extra: Record<string, unknown> = {}) => {
    const e = validar({ acao, quando, ...extra });
    return banco.salvarAgendamento({ ...e, ativo: true, proxima: proxima(e.quando, em(2026, 9, 21, 18, 0)) });
  };
  return { banco, chamadas, agendador, criar, relogio: (t: number) => { agora = t; } };
}

test("na hora: roda com origem agendamento, guarda no histórico e marca a próxima", async () => {
  const { banco, chamadas, agendador, criar } = montar({});
  const id = criar("pc.ligar", { tipo: "semana", dias: UTEIS, hora: "19:00" });
  await Promise.all(await agendador.tique());
  assert.deepEqual(chamadas[0], { metodo: "POST", caminho: "/acao/pc.ligar", corpo: { params: {}, origem: "agendamento" } });
  assert.equal(chamadas.length, 1, "deu certo e o aviso é só para falha");
  const [registro] = banco.historico(5, id);
  assert.equal(registro.estado, "concluido");
  const a = ler(banco.agendamento(id)!);
  assert.equal(a.proxima, em(2026, 9, 22, 19, 0));
  assert.equal(a.ultimo_estado, "concluido");
  assert.equal((await agendador.tique()).length, 0, "não roda de novo no mesmo dia");
});

test("pedido demorado (202): acompanha até o fim e liga o histórico ao pedido", async () => {
  const { banco, chamadas, agendador, criar } = montar({
    "/acao/app.publicar": { status: 202, corpo: { ok: true, pedido: "abcd1234", estado: "executando" } },
    "/pedido/abcd1234": { status: 200, corpo: { ok: true, pedido: { estado: "concluido", resultado: { endereco: "http://x:8001" } } } },
  });
  const id = criar("app.publicar", { tipo: "semana", dias: [3], hora: "19:00" }, { params: { projeto: "loja" }, aviso: "sempre" });
  await Promise.all(await agendador.tique());
  const [registro] = banco.historico(5, id);
  assert.equal(registro.pedido, "abcd1234");
  assert.equal(registro.estado, "concluido");
  assert.match(registro.resumo, /8001/);
  const aviso = chamadas.find((c) => c.caminho === "/acao/aviso.celular");
  assert.equal(aviso?.corpo.params.titulo, "Feito: Publicar o app loja", "aviso sempre: avisa também quando dá certo");
});

test("falhou: avisa no celular", async () => {
  const { banco, chamadas, agendador, criar } = montar({ "/acao/pc.ligar": { status: 500, corpo: { ok: false, erro: "PC sem rede" } } });
  const id = criar("pc.ligar", { tipo: "semana", dias: [3], hora: "19:00" });
  await Promise.all(await agendador.tique());
  assert.equal(banco.historico(5, id)[0].estado, "falhou");
  const aviso = chamadas.find((c) => c.caminho === "/acao/aviso.celular");
  assert.deepEqual(aviso?.corpo.params, { titulo: "Agendamento falhou: Ligar o PC", texto: "PC sem rede" });
});

test("painel fora do ar além da tolerância: não roda, vira perdida e avisa", async () => {
  const { banco, chamadas, agendador, criar, relogio } = montar({});
  const id = criar("pc.ligar", { tipo: "semana", dias: [3], hora: "19:00" }, { tolerancia: 15 });
  relogio(em(2026, 9, 21, 19, 40));
  await Promise.all(await agendador.tique());
  assert.ok(!chamadas.some((c) => c.caminho === "/acao/pc.ligar"), "um ligar o PC das 19h não roda às 19h40");
  assert.equal(banco.historico(5, id)[0].estado, "perdida");
  assert.match(chamadas[0].corpo.params.titulo, /Agendamento perdido/);
  assert.equal(ler(banco.agendamento(id)!).proxima, em(2026, 9, 28, 19, 0));
});

test("dentro da tolerância, o atrasado roda ao voltar", async () => {
  const { banco, agendador, criar, relogio } = montar({});
  const id = criar("pc.ligar", { tipo: "semana", dias: [3], hora: "19:00" }, { tolerancia: 15, aviso: "nunca" });
  relogio(em(2026, 9, 21, 19, 14));
  await Promise.all(await agendador.tique());
  assert.equal(banco.historico(5, id)[0].estado, "concluido");
});

test("uma vez: depois de rodar, fica desligado", async () => {
  const { banco, agendador, criar } = montar({});
  const id = criar("pc.ligar", { tipo: "uma_vez", em: em(2026, 9, 21, 19, 0) });
  await Promise.all(await agendador.tique());
  const a = ler(banco.agendamento(id)!);
  assert.equal(a.ativo, false);
  assert.equal(a.proxima, null);
});

test("pausado não roda; e nunca duas execuções do mesmo ao mesmo tempo", async () => {
  const { banco, chamadas, agendador, criar } = montar({});
  const id = criar("pc.ligar", { tipo: "semana", dias: [3], hora: "19:00" });
  banco.marcarAgendamento(id, { ativo: false });
  assert.equal((await agendador.tique()).length, 0);
  const a = ler(banco.agendamento(id)!);
  const [primeira, segunda] = [agendador.rodar(a), agendador.rodar(a)];
  assert.equal(await segunda, "já rodando");
  assert.equal(await primeira, "concluido");
  assert.equal(chamadas.length, 1);
});

test("executor fora do ar: falhou, com o motivo", async () => {
  const banco = new Banco(":memory:");
  const agendador = new Agendador(banco, async () => { throw new Error("connect ENOENT"); }, () => em(2026, 9, 21, 19, 1), 0);
  const e = validar({ acao: "pc.ligar", quando: { tipo: "semana", dias: [3], hora: "19:00" } });
  const id = banco.salvarAgendamento({ ...e, ativo: true, proxima: em(2026, 9, 21, 19, 0) });
  await Promise.all(await agendador.tique());
  const [registro] = banco.historico(5, id);
  assert.equal(registro.estado, "falhou");
  assert.match(registro.resumo, /executor não respondeu/);
});
