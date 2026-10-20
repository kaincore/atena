// Banco do painel (SQLite em /dados/painel.db): sessões, tentativas de entrada e histórico das ações.
import { createHash, randomBytes } from "node:crypto";
import { DatabaseSync } from "node:sqlite";

export const DURACAO_SESSAO = 30 * 24 * 3600 * 1000; // renova a cada uso: o celular não pede a senha de novo
export const LIMITE_TENTATIVAS = 5;
export const JANELA_TENTATIVAS = 15 * 60 * 1000;
const GUARDA_HISTORICO = 90 * 24 * 3600 * 1000;

export type Sessao = { id: string; criada: number; vista: number; aparelho: string };
export type Registro = {
  id: number;
  quando: number;
  acao: string;
  params: string;
  estado: string;
  resumo: string;
  pedido: string | null;
};

const hashToken = (token: string) => createHash("sha256").update(token).digest("hex");

export class Banco {
  db: DatabaseSync;

  constructor(arquivo: string) {
    this.db = new DatabaseSync(arquivo);
    this.db.exec(`
      PRAGMA journal_mode = WAL;
      CREATE TABLE IF NOT EXISTS sessoes (
        id TEXT PRIMARY KEY, criada INTEGER NOT NULL, vista INTEGER NOT NULL,
        senha TEXT NOT NULL, aparelho TEXT NOT NULL DEFAULT '');
      CREATE TABLE IF NOT EXISTS tentativas (quando INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY, quando INTEGER NOT NULL, acao TEXT NOT NULL, params TEXT NOT NULL,
        estado TEXT NOT NULL, resumo TEXT NOT NULL DEFAULT '', pedido TEXT);
    `);
  }

  limpar(agora = Date.now()) {
    this.db.prepare("DELETE FROM sessoes WHERE vista < ?").run(agora - DURACAO_SESSAO);
    this.db.prepare("DELETE FROM tentativas WHERE quando < ?").run(agora - JANELA_TENTATIVAS);
    this.db.prepare("DELETE FROM historico WHERE quando < ?").run(agora - GUARDA_HISTORICO);
  }

  // --- sessões: o cookie leva o token; o banco guarda só o hash dele

  criarSessao(senhaId: string, aparelho: string, agora = Date.now()): string {
    const token = randomBytes(32).toString("base64url");
    this.db
      .prepare("INSERT INTO sessoes (id, criada, vista, senha, aparelho) VALUES (?, ?, ?, ?, ?)")
      .run(hashToken(token), agora, agora, senhaId, aparelho.slice(0, 200));
    return token;
  }

  // a sessão vale se foi usada nos últimos 30 dias e a senha não mudou desde o login
  sessao(token: string, senhaId: string, agora = Date.now()): Sessao | null {
    const id = hashToken(token);
    const linha = this.db
      .prepare("SELECT id, criada, vista, aparelho FROM sessoes WHERE id = ? AND senha = ? AND vista >= ?")
      .get(id, senhaId, agora - DURACAO_SESSAO) as Sessao | undefined;
    if (!linha) return null;
    if (agora - linha.vista > 60_000) this.db.prepare("UPDATE sessoes SET vista = ? WHERE id = ?").run(agora, id);
    return linha;
  }

  sessoes(senhaId: string, agora = Date.now()): Sessao[] {
    return this.db
      .prepare("SELECT id, criada, vista, aparelho FROM sessoes WHERE senha = ? AND vista >= ? ORDER BY vista DESC")
      .all(senhaId, agora - DURACAO_SESSAO) as Sessao[];
  }

  encerrar(id: string) {
    return this.db.prepare("DELETE FROM sessoes WHERE id = ?").run(id).changes > 0;
  }

  encerrarToken(token: string) {
    this.encerrar(hashToken(token));
  }

  // --- tentativas erradas: 5 em 15 minutos bloqueiam a entrada (uma conta só, então a trava é geral)

  bloqueadoAte(agora = Date.now()): number | null {
    const linhas = this.db
      .prepare("SELECT quando FROM tentativas WHERE quando >= ? ORDER BY quando")
      .all(agora - JANELA_TENTATIVAS) as { quando: number }[];
    if (linhas.length < LIMITE_TENTATIVAS) return null;
    return linhas[linhas.length - LIMITE_TENTATIVAS].quando + JANELA_TENTATIVAS;
  }

  errou(agora = Date.now()): number {
    this.db.prepare("INSERT INTO tentativas (quando) VALUES (?)").run(agora);
    const { n } = this.db
      .prepare("SELECT count(*) AS n FROM tentativas WHERE quando >= ?")
      .get(agora - JANELA_TENTATIVAS) as { n: number };
    return Math.max(0, LIMITE_TENTATIVAS - n);
  }

  acertou() {
    this.db.exec("DELETE FROM tentativas");
  }

  // --- histórico das ações que mudam algo (as consultas não entram)

  registrar(acao: string, params: unknown, estado: string, resumo: string, pedido: string | null = null) {
    this.db
      .prepare("INSERT INTO historico (quando, acao, params, estado, resumo, pedido) VALUES (?, ?, ?, ?, ?, ?)")
      .run(Date.now(), acao, JSON.stringify(params ?? {}), estado, resumo.slice(0, 1000), pedido);
  }

  atualizarPedido(pedido: string, estado: string, resumo: string) {
    this.db
      .prepare("UPDATE historico SET estado = ?, resumo = ? WHERE pedido = ?")
      .run(estado, resumo.slice(0, 1000), pedido);
  }

  historico(limite = 100): Registro[] {
    return this.db
      .prepare("SELECT id, quando, acao, params, estado, resumo, pedido FROM historico ORDER BY id DESC LIMIT ?")
      .all(limite) as Registro[];
  }
}
