import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { conferir, gerar, lerSenha } from "../src/senha.ts";

const pasta = mkdtempSync(join(tmpdir(), "painel-senha-"));
const arquivo = (texto: string) => {
  const caminho = join(pasta, `senha-${Math.random()}`);
  writeFileSync(caminho, texto);
  return caminho;
};

// gerado pelo hashlib.scrypt do Python, como faz o atena-painel-senha
const DO_PYTHON = "scrypt$32768$8$1$AAECAwQFBgcICQoLDA0ODw==$z6KqGAUdRKNBZcfMpE2Lf95O/tYw+pdFOBqS3P+HHx8=";

test("aceita a senha gravada pelo script do servidor (Python)", async () => {
  const senha = lerSenha(arquivo(DO_PYTHON + "\n"));
  assert.ok(senha);
  assert.equal(await conferir(senha, "senha de teste çã"), true);
  assert.equal(await conferir(senha, "senha de teste ca"), false);
});

test("acentos em forma decomposta valem o mesmo (NFC)", async () => {
  const senha = lerSenha(arquivo(DO_PYTHON));
  assert.ok(senha);
  assert.equal(await conferir(senha, "senha de teste çã"), true);
});

test("gerar e conferir", async () => {
  const senha = lerSenha(arquivo(await gerar("outra senha", 2 ** 10)));
  assert.ok(senha);
  assert.equal(await conferir(senha, "outra senha"), true);
  assert.equal(await conferir(senha, "outra senh"), false);
});

test("arquivo ausente ou fora do formato vira null", () => {
  assert.equal(lerSenha(join(pasta, "nao-existe")), null);
  assert.equal(lerSenha(arquivo("")), null);
  assert.equal(lerSenha(arquivo("bcrypt$abc")), null);
  assert.equal(lerSenha(arquivo("scrypt$x$8$1$AAECAwQFBgcICQoLDA0ODw==$z6KqGAUdRKNBZcfMpE2Lf95O/tYw+pdFOBqS3P+HHx8=")), null);
  assert.equal(lerSenha(arquivo("scrypt$32768$8$1$AA==$z6KqGAUdRKNBZcfMpE2Lf95O/tYw+pdFOBqS3P+HHx8=")), null);
});

test("o id da senha muda quando a senha é trocada", async () => {
  const a = lerSenha(arquivo(await gerar("x", 2 ** 10)));
  const b = lerSenha(arquivo(await gerar("x", 2 ** 10)));
  assert.ok(a && b);
  assert.notEqual(a.id, b.id);
});
