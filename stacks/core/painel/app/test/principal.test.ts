// O painel de verdade (principal.ts) subindo num banco em que o reinício cortou uma execução no meio.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Banco } from "../src/banco.ts";

test("ao subir, o painel marca como interrompidas as execuções que ficaram rodando", async () => {
  const pasta = mkdtempSync(join(tmpdir(), "painel-principal-"));
  const antes = new Banco(join(pasta, "painel.db"));
  const id = antes.salvarAgendamento({ nome: "Ligar o PC", acao: "pc.ligar", params: {},
    quando: { tipo: "semana", dias: [3], hora: "19:00" }, aviso: "nunca", tolerancia: 15, ativo: false, proxima: null });
  antes.registrar("pc.ligar", {}, "executando", "", null, id);
  antes.db.close();

  // PAINEL_PORTA: escuta em 127.0.0.1 (porta livre qualquer) em vez do socket; o executor nem existe
  const painel = spawn(process.execPath, ["--disable-warning=ExperimentalWarning", "src/principal.ts"], {
    cwd: new URL("..", import.meta.url).pathname,
    env: { ...process.env, PAINEL_DADOS: pasta, PAINEL_PORTA: "0", EXECUTOR_SOCKET: join(pasta, "executor.sock") },
  });
  let saida = "";
  await new Promise<void>((resolve, reject) => {
    painel.stdout.on("data", (p: Buffer) => {
      saida += p.toString();
      if (saida.includes("painel em")) resolve();
    });
    painel.stderr.on("data", (p: Buffer) => { saida += p.toString(); });
    painel.on("exit", (codigo) => reject(new Error(`o painel saiu (${codigo}): ${saida}`)));
  });
  const saiu = new Promise((r) => painel.once("exit", r));
  painel.kill("SIGTERM");
  await saiu;

  const depois = new Banco(join(pasta, "painel.db"));
  try {
    const [registro] = depois.historico(5, id);
    assert.equal(registro.estado, "interrompida");
    assert.match(registro.resumo, /o painel reiniciou/);
    assert.equal(depois.agendamento(id)!.ultimo_estado, "interrompida");
    assert.match(saida, /1 execução interrompida/);
  } finally {
    depois.db.close();
    rmSync(pasta, { recursive: true, force: true });
  }
});
