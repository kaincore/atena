// Banco do painel (SQLite em /dados/painel.db): sessões, tentativas de entrada, histórico das ações,
// agendamentos e pendências.
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
  agendamento: number | null;
};
export type LinhaAgendamento = {
  id: number;
  nome: string;
  acao: string;
  params: string;
  quando: string;
  aviso: string;
  tolerancia: number;
  ativo: number;
  proxima: number | null;
  ultima: number | null;
  ultimo_estado: string | null;
  criado: number;
};
export type Pendencia = { id: number; texto: string; origem: string; feita: number | null; criada: number };

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
      CREATE TABLE IF NOT EXISTS tentativas (quando INTEGER NOT NULL, entrada TEXT NOT NULL DEFAULT 'tailscale');
      CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY, quando INTEGER NOT NULL, acao TEXT NOT NULL, params TEXT NOT NULL,
        estado TEXT NOT NULL, resumo TEXT NOT NULL DEFAULT '', pedido TEXT);
      CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY, nome TEXT NOT NULL, acao TEXT NOT NULL, params TEXT NOT NULL,
        quando TEXT NOT NULL, aviso TEXT NOT NULL, tolerancia INTEGER NOT NULL, ativo INTEGER NOT NULL,
        proxima INTEGER, ultima INTEGER, ultimo_estado TEXT, criado INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS pendencias (
        id INTEGER PRIMARY KEY, texto TEXT NOT NULL, origem TEXT NOT NULL, feita INTEGER,
        criada INTEGER NOT NULL, UNIQUE (origem, texto));
    `);
    // banco da versão 0.4 e anteriores: o histórico ainda não ligava a execução ao agendamento
    const colunas = (tabela: string) => (this.db.prepare(`PRAGMA table_info(${tabela})`).all() as { name: string }[]).map((c) => c.name);
    if (!colunas("historico").includes("agendamento")) this.db.exec("ALTER TABLE historico ADD COLUMN agendamento INTEGER");
    // banco da versão 0.14 e anteriores: as tentativas erradas não diziam a entrada e travavam as duas;
    // as que ainda estão na janela (15 min no máximo) continuam valendo nas duas
    if (!colunas("tentativas").includes("entrada"))
      this.db.exec(`BEGIN;
        ALTER TABLE tentativas ADD COLUMN entrada TEXT NOT NULL DEFAULT 'tailscale';
        INSERT INTO tentativas (quando, entrada) SELECT quando, 'casa' FROM tentativas;
        COMMIT;`);
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

  // --- tentativas erradas: 5 em 15 minutos bloqueiam a entrada por onde vieram (tailscale ou casa).
  // Uma conta só, mas a trava é de cada entrada: quem erra a senha no Wi-Fi não tranca o dono fora de casa

  bloqueadoAte(entrada: string, agora = Date.now()): number | null {
    const linhas = this.db
      .prepare("SELECT quando FROM tentativas WHERE entrada = ? AND quando >= ? ORDER BY quando")
      .all(entrada, agora - JANELA_TENTATIVAS) as { quando: number }[];
    if (linhas.length < LIMITE_TENTATIVAS) return null;
    return linhas[linhas.length - LIMITE_TENTATIVAS].quando + JANELA_TENTATIVAS;
  }

  errou(entrada: string, agora = Date.now()): number {
    this.db.prepare("INSERT INTO tentativas (quando, entrada) VALUES (?, ?)").run(agora, entrada);
    const { n } = this.db
      .prepare("SELECT count(*) AS n FROM tentativas WHERE entrada = ? AND quando >= ?")
      .get(entrada, agora - JANELA_TENTATIVAS) as { n: number };
    return Math.max(0, LIMITE_TENTATIVAS - n);
  }

  acertou(entrada: string) {
    this.db.prepare("DELETE FROM tentativas WHERE entrada = ?").run(entrada);
  }

  // --- histórico das ações que mudam algo (as consultas não entram)

  registrar(acao: string, params: unknown, estado: string, resumo: string, pedido: string | null = null,
    agendamento: number | null = null): number {
    return Number(this.db
      .prepare("INSERT INTO historico (quando, acao, params, estado, resumo, pedido, agendamento) VALUES (?, ?, ?, ?, ?, ?, ?)")
      .run(Date.now(), acao, JSON.stringify(params ?? {}), estado, resumo.slice(0, 1000), pedido, agendamento)
      .lastInsertRowid);
  }

  atualizarRegistro(id: number, campos: { estado?: string; resumo?: string; pedido?: string }) {
    const atual = this.db.prepare("SELECT estado, resumo, pedido FROM historico WHERE id = ?").get(id) as
      { estado: string; resumo: string; pedido: string | null } | undefined;
    if (!atual) return;
    this.db
      .prepare("UPDATE historico SET estado = ?, resumo = ?, pedido = ? WHERE id = ?")
      .run(campos.estado ?? atual.estado, (campos.resumo ?? atual.resumo).slice(0, 1000), campos.pedido ?? atual.pedido, id);
  }

  atualizarPedido(pedido: string, estado: string, resumo: string) {
    this.db
      .prepare("UPDATE historico SET estado = ?, resumo = ? WHERE pedido = ?")
      .run(estado, resumo.slice(0, 1000), pedido);
  }

  // Ao subir: o que ficou "executando" e ainda sem resumo era do painel que parou. Sem pedido, esperava a
  // resposta do executor, que se perdeu; do agendador com pedido, perdeu quem o acompanhava (e o aviso no
  // celular). Os dois viram "interrompida". Ficam como estão o pedido de uma ação da tela (quem o acompanha
  // é a tela) e o que o agendador já tinha desistido de esperar (tem resumo): o Histórico pergunta ao
  // executor como eles terminaram, e faz o mesmo com o interrompido que tem pedido.
  marcarInterrompidas(): number {
    const abertas = this.db
      .prepare(`SELECT id, quando, pedido, agendamento FROM historico
        WHERE estado = 'executando' AND resumo = '' AND (pedido IS NULL OR agendamento IS NOT NULL)`)
      .all() as { id: number; quando: number; pedido: string | null; agendamento: number | null }[];
    const marcar = this.db.prepare("UPDATE historico SET estado = 'interrompida', resumo = ? WHERE id = ?");
    const ultima = this.db.prepare("SELECT max(id) AS id FROM historico WHERE agendamento = ?");
    for (const r of abertas) {
      marcar.run(r.pedido
        ? `o painel reiniciou enquanto acompanhava o pedido ${r.pedido}; o Histórico pergunta ao executor como ele terminou`
        : "o painel reiniciou antes de o executor responder; confira se a ação aconteceu", r.id);
      // a última vez do agendamento passa a ser esta, se depois dela não rodou de novo
      if (r.agendamento !== null && (ultima.get(r.agendamento) as { id: number }).id === r.id)
        this.marcarAgendamento(r.agendamento, { ultima: r.quando, ultimo_estado: "interrompida" });
    }
    return abertas.length;
  }

  historico(limite = 100, agendamento: number | null = null): Registro[] {
    const colunas = "SELECT id, quando, acao, params, estado, resumo, pedido, agendamento FROM historico";
    if (agendamento !== null)
      return this.db.prepare(`${colunas} WHERE agendamento = ? ORDER BY id DESC LIMIT ?`).all(agendamento, limite) as Registro[];
    return this.db.prepare(`${colunas} ORDER BY id DESC LIMIT ?`).all(limite) as Registro[];
  }

  // --- agendamentos: o agendador do painel roda as ações na hora marcada (veja agendador.ts)

  agendamentos(): LinhaAgendamento[] {
    return this.db.prepare("SELECT * FROM agendamentos ORDER BY ativo DESC, proxima IS NULL, proxima, id").all() as LinhaAgendamento[];
  }

  agendamento(id: number): LinhaAgendamento | null {
    return (this.db.prepare("SELECT * FROM agendamentos WHERE id = ?").get(id) as LinhaAgendamento | undefined) ?? null;
  }

  salvarAgendamento(a: { id?: number; nome: string; acao: string; params: unknown; quando: unknown; aviso: string;
    tolerancia: number; ativo: boolean; proxima: number | null }, agora = Date.now()): number {
    const valores = [a.nome, a.acao, JSON.stringify(a.params), JSON.stringify(a.quando), a.aviso, a.tolerancia, a.ativo ? 1 : 0, a.proxima];
    if (a.id) {
      this.db
        .prepare("UPDATE agendamentos SET nome = ?, acao = ?, params = ?, quando = ?, aviso = ?, tolerancia = ?, ativo = ?, proxima = ? WHERE id = ?")
        .run(...valores, a.id);
      return a.id;
    }
    return Number(this.db
      .prepare("INSERT INTO agendamentos (nome, acao, params, quando, aviso, tolerancia, ativo, proxima, criado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
      .run(...valores, agora).lastInsertRowid);
  }

  marcarAgendamento(id: number, campos: { proxima?: number | null; ativo?: boolean; ultima?: number; ultimo_estado?: string }) {
    const atual = this.agendamento(id);
    if (!atual) return;
    this.db
      .prepare("UPDATE agendamentos SET proxima = ?, ativo = ?, ultima = ?, ultimo_estado = ? WHERE id = ?")
      .run(campos.proxima !== undefined ? campos.proxima : atual.proxima,
        campos.ativo !== undefined ? (campos.ativo ? 1 : 0) : atual.ativo,
        campos.ultima ?? atual.ultima, campos.ultimo_estado ?? atual.ultimo_estado, id);
  }

  apagarAgendamento(id: number) {
    return this.db.prepare("DELETE FROM agendamentos WHERE id = ?").run(id).changes > 0;
  }

  // --- pendências: as do README do servidor (origem readme) e as suas (origem manual)

  pendencias(): Pendencia[] {
    return this.db.prepare("SELECT * FROM pendencias ORDER BY feita IS NOT NULL, feita DESC, id").all() as Pendencia[];
  }

  // o que entrou no README vira pendência; o que saiu dele foi resolvido
  sincronizarReadme(textos: string[], agora = Date.now()) {
    const inserir = this.db.prepare("INSERT OR IGNORE INTO pendencias (texto, origem, criada) VALUES (?, 'readme', ?)");
    for (const texto of textos) inserir.run(texto, agora);
    const abertas = this.db.prepare("SELECT id, texto FROM pendencias WHERE origem = 'readme' AND feita IS NULL").all() as Pendencia[];
    const marcar = this.db.prepare("UPDATE pendencias SET feita = ? WHERE id = ?");
    for (const p of abertas) if (!textos.includes(p.texto)) marcar.run(agora, p.id);
  }

  novaPendencia(texto: string, agora = Date.now()): number {
    return Number(this.db.prepare("INSERT OR IGNORE INTO pendencias (texto, origem, criada) VALUES (?, 'manual', ?)")
      .run(texto, agora).lastInsertRowid);
  }

  marcarPendencia(id: number, feita: boolean, agora = Date.now()) {
    return this.db.prepare("UPDATE pendencias SET feita = ? WHERE id = ?").run(feita ? agora : null, id).changes > 0;
  }

  // só as suas: uma do README voltaria na próxima leitura
  apagarPendencia(id: number) {
    return this.db.prepare("DELETE FROM pendencias WHERE id = ? AND origem = 'manual'").run(id).changes > 0;
  }
}
