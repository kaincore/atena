// Painel de ponta a ponta, com um executor falso no socket unix.
import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { createServer, type IncomingMessage, type Server } from "node:http";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import type { AddressInfo } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Banco } from "../src/banco.ts";
import { criarServidor } from "../src/servidor.ts";
import { gerar } from "../src/senha.ts";

const pasta = mkdtempSync(join(tmpdir(), "painel-"));
const config = {
  publico: new URL("../public", import.meta.url).pathname,
  arquivoSenha: join(pasta, "senha"),
  arquivoToken: join(pasta, "executor.token"),
  socketExecutor: join(pasta, "executor.sock"),
};
const TOKEN = "atx-token-de-teste";
const recebidos: { metodo: string; caminho: string; token: string; corpo: any }[] = [];
let executor: Server;
let painel: Server;
let banco: Banco;
let base: string;

before(async () => {
  writeFileSync(config.arquivoSenha, await gerar("a senha certa", 2 ** 10));
  writeFileSync(config.arquivoToken, TOKEN + "\n");
  executor = createServer((req: IncomingMessage, res) => {
    const partes: Buffer[] = [];
    req.on("data", (p) => partes.push(p));
    req.on("end", () => {
      const corpo = partes.length ? JSON.parse(Buffer.concat(partes).toString()) : null;
      recebidos.push({ metodo: req.method!, caminho: req.url!, token: String(req.headers.authorization), corpo });
      const responder = (status: number, dados: unknown) => {
        res.writeHead(status, { "Content-Type": "application/json" });
        res.end(JSON.stringify(dados));
      };
      if (req.headers.authorization !== `Bearer ${TOKEN}`) return responder(401, { ok: false, erro: "token inválido" });
      if (req.url === "/acao/servico.reiniciar") return responder(202, { ok: true, pedido: "abcd1234", estado: "executando" });
      if (req.url?.startsWith("/pedido/abcd1234"))
        return responder(200, { ok: true, pedido: { id: "abcd1234", estado: "concluido", resultado: { reiniciados: ["arca"] } } });
      if (req.url === "/acao/pc.ligar") return responder(500, { ok: false, erro: "falhou de propósito" });
      responder(200, { ok: true, acao: req.url, resultado: { eco: corpo } });
    });
  });
  await new Promise<void>((r) => executor.listen(config.socketExecutor, r));
  banco = new Banco(":memory:");
  painel = criarServidor(config, banco);
  await new Promise<void>((r) => painel.listen(0, "127.0.0.1", r));
  base = `http://127.0.0.1:${(painel.address() as AddressInfo).port}`;
});

after(() => {
  painel.close();
  executor.close();
  rmSync(pasta, { recursive: true, force: true });
});

async function pedir(metodo: string, caminho: string, corpo?: unknown, cookie?: string, cabecalhos: Record<string, string> = {}) {
  const r = await fetch(base + caminho, {
    method: metodo,
    headers: {
      ...(corpo !== undefined ? { "Content-Type": "application/json", "X-Atena": "1" } : {}),
      ...(cookie ? { Cookie: cookie } : {}),
      ...cabecalhos,
    },
    body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
  });
  return { status: r.status, cabecalhos: r.headers, corpo: await r.json().catch(() => null) };
}

async function entrar(): Promise<string> {
  const r = await pedir("POST", "/api/entrar", { senha: "a senha certa" });
  assert.equal(r.status, 200);
  const setCookie = r.cabecalhos.get("set-cookie")!;
  assert.match(setCookie, /HttpOnly/);
  assert.match(setCookie, /Secure/);
  assert.match(setCookie, /SameSite=Strict/);
  return setCookie.split(";")[0];
}

test("saúde responde sem login", async () => {
  assert.equal((await pedir("GET", "/saude")).status, 200);
});

test("a interface sai com a CSP e o resto da API pede login", async () => {
  const r = await fetch(base + "/");
  assert.equal(r.status, 200);
  assert.match(r.headers.get("content-security-policy")!, /default-src 'self'/);
  assert.match(await r.text(), /<title>Atena<\/title>/);
  assert.equal((await pedir("GET", "/api/eu")).status, 401);
  assert.equal((await pedir("POST", "/api/acao/status.servicos", { params: {} })).status, 401);
  assert.equal((await pedir("GET", "/api/historico")).status, 401);
});

test("caminhos fora da pasta da interface não existem", async () => {
  for (const caminho of ["/../src/servidor.ts", "/%2e%2e/package.json", "/senha", "/executor.token"])
    assert.equal((await fetch(base + caminho)).status, 404, caminho);
});

test("sem o cabeçalho do painel, POST é recusado (CSRF)", async () => {
  const r = await fetch(base + "/api/entrar", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ senha: "a senha certa" }),
  });
  assert.equal(r.status, 403);
  const formulario = await fetch(base + "/api/entrar", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded", "X-Atena": "1" }, body: "senha=x",
  });
  assert.equal(formulario.status, 415);
});

test("login certo dá sessão; sair encerra", async () => {
  const cookie = await entrar();
  const eu = await pedir("GET", "/api/eu", undefined, cookie);
  assert.equal(eu.status, 200);
  assert.ok(eu.corpo.acoes["pc.ligar"]);
  assert.equal((await pedir("POST", "/api/sair", {}, cookie)).status, 200);
  assert.equal((await pedir("GET", "/api/eu", undefined, cookie)).status, 401);
});

test("consulta vai ao executor com o token do painel e não entra no histórico", async () => {
  const cookie = await entrar();
  recebidos.length = 0;
  const r = await pedir("POST", "/api/acao/servico.logs", { params: { stack: "arca", linhas: 10 } }, cookie);
  assert.equal(r.status, 200);
  assert.equal(recebidos[0].caminho, "/acao/servico.logs");
  assert.equal(recebidos[0].token, `Bearer ${TOKEN}`);
  assert.deepEqual(recebidos[0].corpo, { params: { stack: "arca", linhas: 10 }, origem: "painel" });
  assert.equal(banco.historico().filter((x) => x.acao === "servico.logs").length, 0);
});

test("ação fora da lista do painel nem chega ao executor", async () => {
  const cookie = await entrar();
  recebidos.length = 0;
  for (const nome of ["app.apagar", "claude.tarefa", "stack.editar", "arquivo.ler"]) {
    const r = await pedir("POST", `/api/acao/${nome}`, { params: {} }, cookie);
    assert.equal(r.status, 403, nome);
  }
  assert.equal(recebidos.length, 0);
  assert.equal((await pedir("POST", "/api/acao/status.servicos", { params: [1] }, cookie)).status, 400);
});

test("ação que muda algo entra no histórico, com o pedido acompanhado até o fim", async () => {
  const cookie = await entrar();
  const r = await pedir("POST", "/api/acao/servico.reiniciar", { params: { stack: "arca" } }, cookie);
  assert.equal(r.status, 202);
  assert.equal(banco.historico()[0].estado, "executando");
  const p = await pedir("GET", "/api/pedido/abcd1234?esperar=5", undefined, cookie);
  assert.equal(p.corpo.pedido.estado, "concluido");
  assert.equal(recebidos.at(-1)!.caminho, "/pedido/abcd1234?esperar=5");
  const registro = banco.historico()[0];
  assert.equal(registro.estado, "concluido");
  assert.match(registro.resumo, /reiniciados/);
  await pedir("POST", "/api/acao/pc.ligar", { params: {} }, cookie);
  assert.equal(banco.historico()[0].estado, "falhou");
  assert.equal(banco.historico()[0].resumo, "falhou de propósito");
});

test("esperar do pedido tem teto de 60 s", async () => {
  const cookie = await entrar();
  await pedir("GET", "/api/pedido/abcd1234?esperar=999", undefined, cookie);
  assert.equal(recebidos.at(-1)!.caminho, "/pedido/abcd1234?esperar=60");
});

test("sessões: lista e desconecta outro aparelho", async () => {
  const a = await entrar();
  const b = await entrar();
  const lista = await pedir("GET", "/api/sessoes", undefined, a);
  const outra = lista.corpo.sessoes.find((s: { esta: boolean }) => !s.esta);
  assert.ok(lista.corpo.sessoes.some((s: { esta: boolean }) => s.esta));
  assert.equal(outra.id.length, 12);
  // b é uma das outras; desconecta todas as outras
  for (const s of lista.corpo.sessoes.filter((s: { esta: boolean }) => !s.esta))
    assert.equal((await pedir("POST", "/api/sessoes/encerrar", { id: s.id }, a)).status, 200);
  assert.equal((await pedir("GET", "/api/eu", undefined, b)).status, 401);
  assert.equal((await pedir("GET", "/api/eu", undefined, a)).status, 200);
  assert.equal((await pedir("POST", "/api/sessoes/encerrar", { id: "000000000000" }, a)).status, 404);
});

test("trocar a senha derruba as sessões", async () => {
  const cookie = await entrar();
  writeFileSync(config.arquivoSenha, await gerar("a senha certa", 2 ** 10));
  assert.equal((await pedir("GET", "/api/eu", undefined, cookie)).status, 401);
});

test("sem token ou sem executor, o erro diz o que fazer", async () => {
  const cookie = await entrar();
  rmSync(config.arquivoToken);
  const semToken = await pedir("POST", "/api/acao/status.servicos", { params: {} }, cookie);
  assert.equal(semToken.status, 503);
  assert.match(semToken.corpo.erro, /instalador/);
  writeFileSync(config.arquivoToken, TOKEN);
  const socket = config.socketExecutor;
  config.socketExecutor = join(pasta, "nao-existe.sock");
  const painel2 = criarServidor(config, banco);
  await new Promise<void>((r) => painel2.listen(0, "127.0.0.1", r));
  const r = await fetch(`http://127.0.0.1:${(painel2.address() as AddressInfo).port}/api/acao/status.servicos`, {
    method: "POST", headers: { "Content-Type": "application/json", "X-Atena": "1", Cookie: cookie }, body: "{}",
  });
  assert.equal(r.status, 502);
  painel2.close();
  config.socketExecutor = socket;
});

test("senha errada 5 vezes bloqueia, até a certa", async () => {
  banco.acertou();
  for (let i = 0; i < 5; i++) {
    const r = await pedir("POST", "/api/entrar", { senha: "errada" });
    assert.equal(r.status, 401);
  }
  const bloqueado = await pedir("POST", "/api/entrar", { senha: "a senha certa" });
  assert.equal(bloqueado.status, 429);
  assert.match(bloqueado.corpo.erro, /15 min/);
  banco.acertou();
});

test("sem senha definida, o login explica como definir", async () => {
  rmSync(config.arquivoSenha);
  const r = await pedir("POST", "/api/entrar", { senha: "x" });
  assert.equal(r.status, 503);
  assert.match(r.corpo.erro, /atena-painel-senha/);
});
