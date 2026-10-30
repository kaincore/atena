import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Banco, DURACAO_SESSAO, JANELA_TENTATIVAS } from "../src/banco.ts";

const novo = () => new Banco(":memory:");

test("sessão vale com o token certo e a mesma senha", () => {
  const b = novo();
  const token = b.criarSessao("senha1", "Android · Chrome");
  assert.ok(b.sessao(token, "senha1"));
  assert.equal(b.sessao(token + "x", "senha1"), null);
  assert.equal(b.sessao(token, "senha2"), null, "trocar a senha derruba as sessões");
});

test("o banco guarda o hash do token, não o token", () => {
  const b = novo();
  const token = b.criarSessao("s", "");
  const linhas = b.db.prepare("SELECT id FROM sessoes").all() as { id: string }[];
  assert.equal(linhas.length, 1);
  assert.notEqual(linhas[0].id, token);
});

test("sessão vence 30 dias depois do último uso, e o uso renova", () => {
  const b = novo();
  const t0 = 1_000_000_000_000;
  const token = b.criarSessao("s", "", t0);
  assert.ok(b.sessao(token, "s", t0 + DURACAO_SESSAO - 1000), "usada no dia 29");
  assert.ok(b.sessao(token, "s", t0 + DURACAO_SESSAO + 20 * 24 * 3600 * 1000), "renovou no uso anterior");
  assert.equal(b.sessao(token, "s", t0 + 3 * DURACAO_SESSAO), null);
});

test("encerrar e listar sessões", () => {
  const b = novo();
  const a = b.criarSessao("s", "PC");
  b.criarSessao("s", "Celular");
  b.criarSessao("outra", "Velha");
  assert.equal(b.sessoes("s").length, 2);
  b.encerrarToken(a);
  assert.equal(b.sessao(a, "s"), null);
  assert.deepEqual(b.sessoes("s").map((s) => s.aparelho), ["Celular"]);
});

test("5 erros em 15 minutos bloqueiam; depois libera", () => {
  const b = novo();
  const t0 = 2_000_000_000_000;
  for (let i = 0; i < 4; i++) assert.equal(b.errou("tailscale", t0 + i), 4 - i);
  assert.equal(b.bloqueadoAte("tailscale", t0 + 10), null);
  assert.equal(b.errou("tailscale", t0 + 4), 0);
  assert.equal(b.bloqueadoAte("tailscale", t0 + 10), t0 + JANELA_TENTATIVAS);
  assert.equal(b.bloqueadoAte("tailscale", t0 + JANELA_TENTATIVAS + 5), null);
});

test("acertar zera as tentativas", () => {
  const b = novo();
  b.errou("tailscale");
  b.errou("tailscale");
  b.acertou("tailscale");
  assert.equal(b.errou("tailscale"), 4);
});

test("cada entrada conta as próprias tentativas: errar no Wi-Fi não trava o Tailscale", () => {
  const b = novo();
  const t0 = 2_000_000_000_000;
  for (let i = 0; i < 5; i++) b.errou("casa", t0 + i);
  assert.equal(b.bloqueadoAte("casa", t0 + 10), t0 + JANELA_TENTATIVAS);
  assert.equal(b.bloqueadoAte("tailscale", t0 + 10), null);
  assert.equal(b.errou("tailscale", t0 + 10), 4);
  b.acertou("tailscale");
  assert.equal(b.bloqueadoAte("casa", t0 + 20), t0 + JANELA_TENTATIVAS, "acertar numa entrada não destrava a outra");
});

test("histórico registra e atualiza o pedido", () => {
  const b = novo();
  b.registrar("pc.ligar", {}, "concluido", '{"ok":1}');
  b.registrar("servico.reiniciar", { stack: "arca" }, "executando", "", "abcd1234");
  b.atualizarPedido("abcd1234", "concluido", "reiniciado");
  const [ultimo, primeiro] = b.historico();
  assert.equal(ultimo.acao, "servico.reiniciar");
  assert.equal(ultimo.estado, "concluido");
  assert.equal(ultimo.resumo, "reiniciado");
  assert.deepEqual(JSON.parse(ultimo.params), { stack: "arca" });
  assert.equal(primeiro.acao, "pc.ligar");
});

test("limpar apaga o que venceu", () => {
  const b = novo();
  const velho = Date.now() - 100 * 24 * 3600 * 1000;
  b.criarSessao("s", "", velho);
  b.errou("casa", velho);
  b.db.prepare("INSERT INTO historico (quando, acao, params, estado) VALUES (?, 'x', '{}', 'concluido')").run(velho);
  b.limpar();
  for (const tabela of ["sessoes", "tentativas", "historico"])
    assert.equal((b.db.prepare(`SELECT count(*) AS n FROM ${tabela}`).get() as { n: number }).n, 0, tabela);
});

test("banco da versão 0.4: o histórico ganha a coluna do agendamento e continua com o que tinha", () => {
  const pasta = mkdtempSync(join(tmpdir(), "painel-banco-"));
  const arquivo = join(pasta, "painel.db");
  const velho = new DatabaseSync(arquivo);
  velho.exec(`CREATE TABLE historico (id INTEGER PRIMARY KEY, quando INTEGER NOT NULL, acao TEXT NOT NULL, params TEXT NOT NULL,
    estado TEXT NOT NULL, resumo TEXT NOT NULL DEFAULT '', pedido TEXT);
    INSERT INTO historico (quando, acao, params, estado) VALUES (1, 'pc.ligar', '{}', 'concluido');`);
  velho.close();
  const b = new Banco(arquivo);
  assert.equal(b.historico()[0].agendamento, null);
  const id = b.registrar("pc.ligar", {}, "executando", "", null, 7);
  b.atualizarRegistro(id, { estado: "concluido", pedido: "abcd1234" });
  assert.deepEqual(b.historico(5, 7).map((r) => [r.estado, r.pedido]), [["concluido", "abcd1234"]]);
  b.db.close();
  rmSync(pasta, { recursive: true, force: true });
});

test("banco da versão 0.14: as tentativas ganham a entrada, e as de antes continuam valendo nas duas", () => {
  const pasta = mkdtempSync(join(tmpdir(), "painel-banco-"));
  const arquivo = join(pasta, "painel.db");
  const agora = Date.now();
  const velho = new DatabaseSync(arquivo);
  velho.exec("CREATE TABLE tentativas (quando INTEGER NOT NULL)");
  const inserir = velho.prepare("INSERT INTO tentativas (quando) VALUES (?)");
  for (let i = 0; i < 3; i++) inserir.run(agora - 1000 + i);
  velho.close();
  const b = new Banco(arquivo);
  assert.equal(b.errou("casa", agora), 1, "as 3 de antes contam na rede de casa");
  assert.equal(b.errou("tailscale", agora), 1, "e no Tailscale");
  b.acertou("tailscale");
  assert.equal(b.errou("tailscale", agora), 4);
  assert.equal(b.errou("casa", agora), 0);
  b.db.close();
  const deNovo = new Banco(arquivo);
  assert.equal(deNovo.errou("tailscale", agora), 3, "abrir de novo não copia as tentativas outra vez");
  deNovo.db.close();
  rmSync(pasta, { recursive: true, force: true });
});
