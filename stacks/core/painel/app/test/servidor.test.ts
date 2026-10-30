// Painel de ponta a ponta, com um executor falso no socket unix.
import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { createServer, type IncomingMessage, type Server } from "node:http";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import type { AddressInfo } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Agendador } from "../src/agendador.ts";
import { Banco } from "../src/banco.ts";
import { pedirExecutor } from "../src/executor.ts";
import { criarServidor, pendenciasDoReadme } from "../src/servidor.ts";
import { gerar } from "../src/senha.ts";

const pasta = mkdtempSync(join(tmpdir(), "painel-"));
const config = {
  publico: new URL("../public", import.meta.url).pathname,
  arquivoSenha: join(pasta, "senha"),
  arquivoToken: join(pasta, "executor.token"),
  socketExecutor: join(pasta, "executor.sock"),
};
const TOKEN = "atx-token-de-teste";
let README = "# Servidor\n\n## Pendências conhecidas\n\n- **Backup:** não existe.\n- **Diun:** não instalado,\n  falta a regra 4.\n\n## Outra seção\n\n- não é pendência\n";
const recebidos: { metodo: string; caminho: string; token: string; corpo: any }[] = [];
let executor: Server;
let painel: ReturnType<typeof criarServidor>;
let banco: Banco;
let agendador: Agendador;
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
      if (req.url === "/acao/claude.tarefa") return responder(202, { ok: true, pedido: "beef0001", estado: "executando" });
      if (req.url === "/acao/arquivo.ler" && corpo?.params?.caminho === "/opt/atena/README.md")
        return responder(200, { ok: true, resultado: { arquivo: "/opt/atena/README.md", texto: README, cortado: false } });
      if (req.url?.startsWith("/pedido/beef0001"))
        return responder(200, { ok: true, pedido: { id: "beef0001", estado: "concluido", resumo: "Fiz o app de lista de compras" } });
      responder(200, { ok: true, acao: req.url, resultado: { eco: corpo } });
    });
  });
  await new Promise<void>((r) => executor.listen(config.socketExecutor, r));
  banco = new Banco(":memory:");
  agendador = new Agendador(banco, (metodo, caminho, corpo) =>
    pedirExecutor(config.socketExecutor, config.arquivoToken, metodo, caminho, corpo), Date.now, 0);
  painel = criarServidor(config, banco, agendador);
  await new Promise<void>((r) => painel.listen(0, "127.0.0.1", r));
  base = `http://127.0.0.1:${(painel.address() as AddressInfo).port}`;
});

after(() => {
  agendador.parar();
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
  // o corpo muda de rota para rota; cada teste confere o que importa nele
  const dados: any = await r.json().catch(() => null);
  return { status: r.status, cabecalhos: r.headers, corpo: dados };
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

test("o sw.js sai com a versão dos arquivos e a lista inteira da casca", async () => {
  const texto = await (await fetch(base + "/sw.js")).text();
  const versao = texto.match(/const VERSAO = "([0-9a-f]{12})";/);
  assert.ok(versao, "a versão não foi trocada");
  const casca: string[] = JSON.parse(texto.match(/const CASCA = (\[.*\]);/)![1]);
  for (const caminho of ["/", "/app.js", "/comum.js", "/estilo.css", "/telas/inicio.js", "/fontes/commissioner-latin.woff2", "/icone-192.png"])
    assert.ok(casca.includes(caminho), caminho);
  assert.ok(!casca.includes("/sw.js") && !casca.includes("/index.html"));
  assert.equal((await (await fetch(base + "/sw.js")).text()).match(/const VERSAO = "(\w+)"/)![1], versao[1]);
});

test("a interface sai comprimida, e o que não mudou volta como 304", async () => {
  const r = await fetch(base + "/estilo.css", { headers: { "Accept-Encoding": "gzip" } });
  assert.equal(r.headers.get("content-encoding"), "gzip");
  assert.match(await r.text(), /--azul/);
  const etag = r.headers.get("etag")!;
  assert.match(etag, /^"[\w-]{22}"$/);
  const igual = await fetch(base + "/estilo.css", { headers: { "If-None-Match": etag } });
  assert.equal(igual.status, 304);
  assert.equal(await igual.text(), "");
  const fonte = await fetch(base + "/fontes/commissioner-latin.woff2", { headers: { "Accept-Encoding": "gzip" } });
  assert.equal(fonte.headers.get("content-encoding"), null); // woff2 já é comprimido
  const gravura = await fetch(base + "/gravuras/criacao-de-adao.webp", { headers: { "Accept-Encoding": "gzip" } });
  assert.equal(gravura.headers.get("content-type"), "image/webp");
  assert.equal(gravura.headers.get("content-encoding"), null);
});

test("respostas grandes da API saem comprimidas para quem aceita", async () => {
  const cookie = await entrar();
  const grande = { texto: "x".repeat(4000) };
  const r = await pedir("POST", "/api/acao/status.servicos", { params: grande }, cookie, { "Accept-Encoding": "gzip" });
  assert.equal(r.cabecalhos.get("content-encoding"), "gzip");
  assert.deepEqual(r.corpo.resultado.eco.params, grande);
  const pequena = await pedir("GET", "/saude", undefined, undefined, { "Accept-Encoding": "gzip" });
  assert.equal(pequena.cabecalhos.get("content-encoding"), null);
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

test("pela rede de casa, em HTTP, o cookie sai sem Secure; a senha errada conta só na entrada em que foi digitada", async () => {
  await new Promise<void>((r) => painel.casa.listen(0, "127.0.0.1", r));
  const casa = `http://127.0.0.1:${(painel.casa.address() as AddressInfo).port}`;
  const entrarEmCasa = (senha: string) => fetch(casa + "/api/entrar", {
    method: "POST", headers: { "Content-Type": "application/json", "X-Atena": "1" }, body: JSON.stringify({ senha }),
  });
  try {
    const r = await entrarEmCasa("a senha certa");
    assert.equal(r.status, 200);
    const setCookie = r.headers.get("set-cookie")!;
    assert.match(setCookie, /HttpOnly/);
    assert.match(setCookie, /SameSite=Strict/);
    assert.doesNotMatch(setCookie, /Secure/);
    const eu = await fetch(casa + "/api/eu", { headers: { Cookie: setCookie.split(";")[0] } });
    assert.equal(eu.status, 200);
    assert.doesNotMatch(eu.headers.get("set-cookie")!, /Secure/);
    // a mesma sessão vale pelo Tailscale, que continua mandando o cookie com Secure
    const tailnet = await pedir("GET", "/api/eu", undefined, setCookie.split(";")[0]);
    assert.equal(tailnet.status, 200);
    assert.match(tailnet.cabecalhos.get("set-cookie")!, /Secure/);

    assert.match(((await (await entrarEmCasa("errada")).json()) as { erro: string }).erro, /restam 4/);
    assert.match((await pedir("POST", "/api/entrar", { senha: "errada" })).corpo.erro, /restam 4/);
    assert.equal((await entrarEmCasa("a senha certa")).status, 200); // a certa zera a conta
    assert.equal((await pedir("POST", "/api/entrar", { senha: "a senha certa" })).status, 200);
  } finally {
    painel.casa.close();
  }
});

test("cinco senhas erradas pela rede de casa travam só a rede de casa, e o dono entra pelo Tailscale", async () => {
  await new Promise<void>((r) => painel.casa.listen(0, "127.0.0.1", r));
  const casa = `http://127.0.0.1:${(painel.casa.address() as AddressInfo).port}`;
  const entrarEmCasa = async (senha: string) => {
    const r = await fetch(casa + "/api/entrar", {
      method: "POST", headers: { "Content-Type": "application/json", "X-Atena": "1" }, body: JSON.stringify({ senha }),
    });
    return { status: r.status, erro: ((await r.json()) as { erro?: string }).erro };
  };
  try {
    for (let i = 0; i < 5; i++) assert.equal((await entrarEmCasa("errada")).status, 401);
    const travada = await entrarEmCasa("a senha certa");
    assert.equal(travada.status, 429);
    assert.match(travada.erro!, /rede de casa.*15 min/);
    assert.match((await pedir("POST", "/api/entrar", { senha: "errada" })).corpo.erro, /restam 4/, "o Tailscale conta as dele");
    await entrar();
    assert.equal((await entrarEmCasa("a senha certa")).status, 429, "entrar pelo Tailscale não destrava a rede de casa");
  } finally {
    painel.casa.close();
    banco.acertou("casa");
  }
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
  for (const nome of ["arquivo.entregar", "local.processar", "arca.guardar", "claude.responder", "aviso.celular"]) {
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

test("a central: consultas não entram no histórico, a decisão entra", async () => {
  const cookie = await entrar();
  for (const nome of ["aprovacoes.lista", "atividade.lista"])
    assert.equal((await pedir("POST", `/api/acao/${nome}`, { params: {} }, cookie)).status, 200, nome);
  const r = await pedir("POST", "/api/acao/aprovacoes.decidir", { params: { pedido: "abcd9999", decisao: "aprovar" } }, cookie);
  assert.equal(r.status, 200);
  assert.deepEqual(recebidos.at(-1)!.corpo, { params: { pedido: "abcd9999", decisao: "aprovar" }, origem: "painel" });
  const [ultimo] = banco.historico();
  assert.equal(ultimo.acao, "aprovacoes.decidir");
  assert.deepEqual(JSON.parse(ultimo.params), { pedido: "abcd9999", decisao: "aprovar" });
  assert.equal(banco.historico().filter((x) => x.acao === "aprovacoes.lista" || x.acao === "atividade.lista").length, 0);
});

test("a aba Sistema: sensores, processos, rede e journal vão ao executor e não entram no histórico", async () => {
  const cookie = await entrar();
  const antes = banco.historico().length;
  const pedidos = {
    "sistema.sensores": {},
    "sistema.processos": { ordem: "ram", quantos: 25 },
    "sistema.rede": {},
    "servico.journal": { linhas: 100, prioridade: "err", desde: "6h", unidade: "docker.service" },
  };
  for (const [nome, params] of Object.entries(pedidos)) {
    const r = await pedir("POST", `/api/acao/${nome}`, { params }, cookie);
    assert.equal(r.status, 200, nome);
    assert.deepEqual(recebidos.at(-1)!.corpo, { params, origem: "painel" });
  }
  assert.equal(banco.historico().length, antes);
});

test("o lab e o Claude Code: consultas fora do histórico; o resto entra, e o trabalho termina com o resumo", async () => {
  const cookie = await entrar();
  const antes = banco.historico().length;
  assert.equal((await pedir("POST", "/api/acao/claude.trabalhos", { params: {} }, cookie)).status, 200);
  assert.equal(banco.historico().length, antes);
  const mudam = {
    "app.publicar": { projeto: "loja" }, "app.cancelar": { projeto: "loja" }, "app.restaurar": { projeto: "loja" },
    "app.apagar": { projeto: "loja", partes: ["docker", "codigo"] }, "app.comando": { projeto: "loja", comando: "ls /data" },
    "claude.cancelar": { pedido: "beef0002" },
  };
  for (const [nome, params] of Object.entries(mudam)) {
    assert.equal((await pedir("POST", `/api/acao/${nome}`, { params }, cookie)).status, 200, nome);
    assert.equal(banco.historico()[0].acao, nome);
    assert.deepEqual(JSON.parse(banco.historico()[0].params), params);
  }
  const r = await pedir("POST", "/api/acao/claude.tarefa", { params: { projeto: "loja", pedido: "faz um app", conta: "pessoal" } }, cookie);
  assert.equal(r.status, 202);
  assert.equal(banco.historico()[0].estado, "executando");
  await pedir("GET", "/api/pedido/beef0001", undefined, cookie);
  assert.equal(banco.historico()[0].estado, "concluido");
  assert.match(banco.historico()[0].resumo, /Fiz o app de lista de compras/);
});

test("agendamentos: salvar, listar, pausar, retomar, rodar agora e apagar", async () => {
  const cookie = await entrar();
  const daquiAUmaHora = new Date(Date.now() + 3600_000);
  const hora = `${String(daquiAUmaHora.getHours()).padStart(2, "0")}:${String(daquiAUmaHora.getMinutes()).padStart(2, "0")}`;
  const novo = { acao: "servico.reiniciar", params: { stack: "arca" }, quando: { tipo: "semana", dias: [0, 1, 2, 3, 4, 5, 6], hora } };
  const r = await pedir("POST", "/api/agendamentos/salvar", novo, cookie);
  assert.equal(r.status, 200);
  const id = r.corpo.agendamento.id;
  assert.equal(r.corpo.agendamento.nome, "Reiniciar arca");
  assert.ok(r.corpo.agendamento.proxima > Date.now());
  assert.equal((await pedir("POST", "/api/agendamentos/salvar", { ...novo, acao: "app.apagar" }, cookie)).status, 400);
  assert.match((await pedir("POST", "/api/agendamentos/salvar", { acao: "pc.ligar", quando: { tipo: "uma_vez", em: Date.now() - 1000 } }, cookie)).corpo.erro, /já passaram/);
  const lista = await pedir("GET", "/api/agendamentos", undefined, cookie);
  assert.ok(lista.corpo.agendaveis["pc.ligar"] === null);
  assert.deepEqual(lista.corpo.agendamentos.find((a: { id: number }) => a.id === id).execucoes, []);

  await pedir("POST", "/api/agendamentos/ativar", { id, ativo: false }, cookie);
  assert.equal(banco.agendamento(id)!.ativo, 0);
  await pedir("POST", "/api/agendamentos/ativar", { id, ativo: true }, cookie);
  assert.equal(banco.agendamento(id)!.ativo, 1);

  recebidos.length = 0;
  assert.equal((await pedir("POST", "/api/agendamentos/rodar", { id }, cookie)).status, 202);
  for (let i = 0; i < 50 && banco.historico(5, id)[0]?.estado !== "concluido"; i++) await new Promise((p) => setTimeout(p, 20));
  assert.deepEqual(recebidos[0].corpo, { params: { stack: "arca" }, origem: "agendamento" });
  assert.equal(banco.historico(5, id)[0].estado, "concluido");
  const historico = await pedir("GET", `/api/historico?agendamento=${id}`, undefined, cookie);
  assert.equal(historico.corpo.historico.length, 1);

  assert.equal((await pedir("POST", "/api/agendamentos/apagar", { id }, cookie)).status, 200);
  assert.equal((await pedir("POST", "/api/agendamentos/apagar", { id }, cookie)).status, 404);
});

test("pendências: as do README entram, as suas também; a que sai do README fica resolvida", async () => {
  assert.deepEqual(pendenciasDoReadme(README), ["**Backup:** não existe.", "**Diun:** não instalado, falta a regra 4."]);
  const cookie = await entrar();
  let r = await pedir("GET", "/api/pendencias", undefined, cookie);
  assert.equal(r.corpo.readme, "/opt/atena/README.md");
  assert.equal(r.corpo.pendencias.filter((p: { feita: number | null }) => !p.feita).length, 2);
  assert.equal((await pedir("POST", "/api/pendencias/nova", { texto: "trocar a pasta térmica" }, cookie)).status, 200);
  r = await pedir("GET", "/api/pendencias", undefined, cookie);
  const minha = r.corpo.pendencias.find((p: { origem: string }) => p.origem === "manual");
  const doReadme = r.corpo.pendencias.find((p: { origem: string }) => p.origem === "readme");
  assert.equal((await pedir("POST", "/api/pendencias/marcar", { id: minha.id, feita: true }, cookie)).status, 200);
  assert.equal((await pedir("POST", "/api/pendencias/apagar", { id: doReadme.id }, cookie)).status, 404);
  assert.equal((await pedir("POST", "/api/pendencias/apagar", { id: minha.id }, cookie)).status, 200);
  README = README.replace("- **Backup:** não existe.\n", "");
  r = await pedir("GET", "/api/pendencias", undefined, cookie);
  const backup = r.corpo.pendencias.find((p: { texto: string }) => p.texto.startsWith("**Backup"));
  assert.ok(backup.feita, "saiu do README: resolvida");
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
  banco.acertou("tailscale");
  for (let i = 0; i < 5; i++) {
    const r = await pedir("POST", "/api/entrar", { senha: "errada" });
    assert.equal(r.status, 401);
  }
  const bloqueado = await pedir("POST", "/api/entrar", { senha: "a senha certa" });
  assert.equal(bloqueado.status, 429);
  assert.match(bloqueado.corpo.erro, /15 min/);
  banco.acertou("tailscale");
});

test("sem senha definida, o login explica como definir", async () => {
  rmSync(config.arquivoSenha);
  const r = await pedir("POST", "/api/entrar", { senha: "x" });
  assert.equal(r.status, 503);
  assert.match(r.corpo.erro, /atena-painel-senha/);
});
