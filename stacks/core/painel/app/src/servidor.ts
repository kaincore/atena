// Servidor HTTP do painel: arquivos da interface e a API (/api/...).
// Toda ação passa pelo executor, que tem a lista fechada do servidor; esta aqui é a lista do painel.
import { createHash } from "node:crypto";
import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { readdirSync, readFileSync } from "node:fs";
import { extname, join } from "node:path";
import { gzipSync } from "node:zlib";
import { AGENDAVEIS, Agendador, EntradaInvalida, ler, proxima, validar } from "./agendador.ts";
import type { Banco } from "./banco.ts";
import { DURACAO_SESSAO } from "./banco.ts";
import { pedirExecutor, SemToken } from "./executor.ts";
import { conferir, lerSenha } from "./senha.ts";

export type Config = {
  publico: string; // pasta da interface
  arquivoSenha: string;
  arquivoToken: string;
  socketExecutor: string;
};

// muda = entra no histórico (a interface pede confirmação antes das que mudam algo)
export const ACOES: Record<string, { muda: boolean }> = {
  "status.servicos": { muda: false },
  "status.recursos": { muda: false },
  "status.containers": { muda: false },
  "status.sistema": { muda: false },
  "sistema.sensores": { muda: false },
  "sistema.processos": { muda: false },
  "sistema.rede": { muda: false },
  "gasto.api": { muda: false },
  "servico.logs": { muda: false },
  "servico.journal": { muda: false },
  "stack.fotos": { muda: false },
  "arquivo.ler": { muda: false },
  "arquivo.procurar": { muda: false },
  "arquivo.buscar": { muda: false },
  "pc.estado": { muda: false },
  "app.lista": { muda: false },
  "claude.trabalhos": { muda: false },
  "aprovacoes.lista": { muda: false },
  "atividade.lista": { muda: false },
  "aprovacoes.decidir": { muda: true },
  "servico.reiniciar": { muda: true },
  "pc.ligar": { muda: true },
  "pc.desligar": { muda: true },
  "pc.reiniciar": { muda: true },
  "pc.cancelar": { muda: true },
  "app.reiniciar": { muda: true },
  "app.parar": { muda: true },
  "app.publicar": { muda: true },
  "app.cancelar": { muda: true },
  "app.apagar": { muda: true },
  "app.restaurar": { muda: true },
  "app.comando": { muda: true },
  "claude.tarefa": { muda: true },
  "claude.cancelar": { muda: true },
  "stack.editar": { muda: true },
  "stack.aplicar": { muda: true },
  "stack.desfazer": { muda: true },
};

const COOKIE = "atena_sessao";
const LIMITE_CORPO = 512 * 1024; // o editor de stacks manda o trecho antes e depois da troca
const TERMINADOS = new Set(["concluido", "falhou", "recusado", "expirado", "cancelado"]);
const TIPOS: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".webmanifest": "application/manifest+json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".webp": "image/webp", // a gravura da entrada: em WebP, com o recorte no alfa, ela sai bem menor que em PNG
  ".woff2": "font/woff2", // as fontes vêm do próprio painel (a CSP não deixa buscar fora)
};
const SEGURANCA = {
  "Content-Security-Policy":
    "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'; " +
    "manifest-src 'self'; worker-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Cross-Origin-Opener-Policy": "same-origin",
};

class ErroHttp extends Error {
  status: number;
  constructor(status: number, mensagem: string) {
    super(mensagem);
    this.status = status;
  }
}

type Arquivo = { tipo: string; dados: Buffer; gzip: Buffer | null; etag: string };

const aceitaGzip = (req: IncomingMessage) => /\bgzip\b/.test(String(req.headers["accept-encoding"] ?? ""));

// O sw.js sai com a versão (um resumo de todos os outros arquivos) e a lista da casca: mudar qualquer
// arquivo da interface instala um cache novo no celular, sem lista nem número para lembrar de subir.
function carregarPublico(pasta: string): Map<string, Arquivo> {
  const lidos = new Map<string, { tipo: string; dados: Buffer }>();
  for (const nome of readdirSync(pasta, { recursive: true }) as string[]) {
    const tipo = TIPOS[extname(nome)];
    if (tipo) lidos.set("/" + nome.split("\\").join("/"), { tipo, dados: readFileSync(join(pasta, nome)) });
  }
  const caminhos = [...lidos.keys()].filter((c) => c !== "/sw.js").sort();
  const sw = lidos.get("/sw.js");
  if (sw) {
    const resumo = createHash("sha256");
    for (const c of caminhos) resumo.update(c).update(lidos.get(c)!.dados);
    const casca = caminhos.map((c) => (c === "/index.html" ? "/" : c));
    sw.dados = Buffer.from(sw.dados.toString("utf8")
      .replace('const VERSAO = "dev";', `const VERSAO = "${resumo.digest("hex").slice(0, 12)}";`)
      .replace('const CASCA = ["/"];', `const CASCA = ${JSON.stringify(casca)};`));
  }
  const arquivos = new Map<string, Arquivo>();
  for (const [caminho, { tipo, dados }] of lidos) {
    // fonte e imagem já vêm comprimidas; texto cai para menos de um terço
    const gzip = /^(text\/|application\/manifest|image\/svg)/.test(tipo) ? gzipSync(dados, { level: 9 }) : null;
    arquivos.set(caminho, {
      tipo, dados, gzip: gzip && gzip.length < dados.length ? gzip : null,
      etag: `"${createHash("sha256").update(dados).digest("base64url").slice(0, 22)}"`,
    });
  }
  return arquivos;
}

function responder(res: ServerResponse, status: number, corpo: unknown, cabecalhos: Record<string, string> = {}) {
  let dados = Buffer.from(JSON.stringify(corpo));
  // as listas grandes (atividade, processos, rede) viajam comprimidas até o celular
  const comprimir = dados.length > 1024 && res.req && aceitaGzip(res.req);
  if (comprimir) dados = gzipSync(dados);
  res.writeHead(status, {
    ...SEGURANCA,
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": String(dados.length),
    "Cache-Control": "no-store",
    ...(comprimir ? { "Content-Encoding": "gzip", Vary: "Accept-Encoding" } : {}),
    ...cabecalhos,
  });
  res.end(dados);
}

function lerCorpo(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const partes: Buffer[] = [];
    let tamanho = 0;
    req.on("data", (p: Buffer) => {
      tamanho += p.length;
      if (tamanho > LIMITE_CORPO) {
        reject(new ErroHttp(413, "pedido grande demais"));
        req.destroy();
      } else partes.push(p);
    });
    req.on("end", () => {
      try {
        const corpo = partes.length ? JSON.parse(Buffer.concat(partes).toString("utf8")) : {};
        if (typeof corpo !== "object" || corpo === null || Array.isArray(corpo)) throw new Error();
        resolve(corpo);
      } catch {
        reject(new ErroHttp(400, "o corpo deve ser um objeto JSON"));
      }
    });
    req.on("error", reject);
  });
}

function cookie(req: IncomingMessage, nome: string): string | null {
  for (const parte of (req.headers.cookie ?? "").split(";")) {
    const [chave, ...valor] = parte.trim().split("=");
    if (chave === nome) return valor.join("=");
  }
  return null;
}

const cookieSessao = (token: string, segundos: number) =>
  `${COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${segundos}`;

// "Android · Chrome": só para você reconhecer o aparelho na lista de sessões
export function aparelho(agente: string): string {
  const sistema =
    [["Android", "Android"], ["iPhone", "iPhone"], ["iPad", "iPad"], ["Windows", "Windows"],
     ["Mac OS", "Mac"], ["Linux", "Linux"]].find(([m]) => agente.includes(m))?.[1] ?? "?";
  const navegador =
    [["Edg/", "Edge"], ["Firefox/", "Firefox"], ["Chrome/", "Chrome"], ["Safari/", "Safari"]]
      .find(([m]) => agente.includes(m))?.[1] ?? "?";
  return `${sistema} · ${navegador}`;
}

// as pendências conhecidas do servidor ficam numa seção do README dele (quando existe)
export const README_SERVIDOR = "/opt/atena/README.md";

export function pendenciasDoReadme(texto: string): string[] {
  const linhas = texto.split("\n");
  const inicio = linhas.findIndex((l) => /^##\s+Pendências conhecidas/i.test(l));
  if (inicio < 0) return [];
  const itens: string[] = [];
  for (const l of linhas.slice(inicio + 1)) {
    if (/^#{1,2}\s/.test(l)) break;
    if (/^[-*]\s+/.test(l)) itens.push(l.replace(/^[-*]\s+/, "").trim());
    else if (/^\s+\S/.test(l) && itens.length) itens[itens.length - 1] += " " + l.trim();
  }
  return itens.filter(Boolean);
}

const numero = (valor: unknown) => {
  const n = Number(valor);
  if (!Number.isInteger(n) || n < 1) throw new ErroHttp(400, "id inválido");
  return n;
};

function resumir(corpo: Record<string, unknown>): string {
  if (corpo.ok === false) return String(corpo.erro ?? "erro");
  const texto = JSON.stringify(corpo.resultado ?? corpo.mensagem ?? "");
  return texto.length > 300 ? texto.slice(0, 300) + "…" : texto;
}

export function criarServidor(config: Config, banco: Banco, agendador?: Agendador): Server {
  const publico = carregarPublico(config.publico);
  let conferindo = false; // scrypt usa 32 MB: uma conferência de senha por vez

  function exigirSessao(req: IncomingMessage) {
    const senha = lerSenha(config.arquivoSenha);
    const token = cookie(req, COOKIE);
    const sessao = senha && token ? banco.sessao(token, senha.id) : null;
    if (!sessao || !senha) throw new ErroHttp(401, "entre com a senha");
    return { sessao, senha, token: token as string };
  }

  async function executor(metodo: "GET" | "POST", caminho: string, corpo?: unknown) {
    try {
      return await pedirExecutor(config.socketExecutor, config.arquivoToken, metodo, caminho, corpo);
    } catch (e) {
      if (e instanceof SemToken) throw new ErroHttp(503, `${e.message} (rode o instalador do painel)`);
      throw new ErroHttp(502, "o executor não respondeu (sudo systemctl status atena-executor)");
    }
  }

  async function api(req: IncomingMessage, res: ServerResponse, url: URL) {
    const rota = url.pathname;
    if (req.method === "POST") {
      // cookie SameSite=Strict + cabeçalho próprio: outro site não consegue mandar ações em seu nome
      if (req.headers["x-atena"] !== "1") throw new ErroHttp(403, "pedido sem o cabeçalho do painel");
      if (!String(req.headers["content-type"] ?? "").startsWith("application/json"))
        throw new ErroHttp(415, "mande JSON");
    }

    if (rota === "/api/entrar" && req.method === "POST") {
      const { senha: tentativa } = await lerCorpo(req);
      const senha = lerSenha(config.arquivoSenha);
      if (!senha) throw new ErroHttp(503, "a senha ainda não foi definida: no servidor, rode sudo atena-painel-senha");
      const ate = banco.bloqueadoAte();
      if (ate) {
        const minutos = Math.ceil((ate - Date.now()) / 60000);
        throw new ErroHttp(429, `muitas tentativas erradas; tente de novo em ${minutos} min`);
      }
      if (typeof tentativa !== "string" || !tentativa || tentativa.length > 1024)
        throw new ErroHttp(400, "digite a senha");
      if (conferindo) throw new ErroHttp(429, "aguarde a tentativa anterior");
      conferindo = true;
      let certa: boolean;
      try {
        certa = await conferir(senha, tentativa);
      } finally {
        conferindo = false;
      }
      if (!certa) {
        const restam = banco.errou();
        throw new ErroHttp(401, restam ? `senha errada (restam ${restam} tentativas)` : "senha errada; entrada bloqueada por 15 min");
      }
      banco.acertou();
      const token = banco.criarSessao(senha.id, aparelho(String(req.headers["user-agent"] ?? "")));
      return responder(res, 200, { ok: true }, { "Set-Cookie": cookieSessao(token, DURACAO_SESSAO / 1000) });
    }

    const { sessao, senha, token } = exigirSessao(req);

    if (rota === "/api/eu" && req.method === "GET") {
      // renova o cookie: enquanto o app for aberto, a sessão não vence
      return responder(res, 200, { ok: true, sessao: sessao.id.slice(0, 12), acoes: ACOES },
        { "Set-Cookie": cookieSessao(token, DURACAO_SESSAO / 1000) });
    }
    if (rota === "/api/sair" && req.method === "POST") {
      banco.encerrarToken(token);
      return responder(res, 200, { ok: true }, { "Set-Cookie": cookieSessao("", 0) });
    }
    if (rota === "/api/sessoes" && req.method === "GET") {
      const sessoes = banco.sessoes(senha.id).map((s) => ({
        id: s.id.slice(0, 12), criada: s.criada, vista: s.vista, aparelho: s.aparelho, esta: s.id === sessao.id,
      }));
      return responder(res, 200, { ok: true, sessoes });
    }
    if (rota === "/api/sessoes/encerrar" && req.method === "POST") {
      const { id } = await lerCorpo(req);
      const alvo = banco.sessoes(senha.id).find((s) => typeof id === "string" && id.length === 12 && s.id.startsWith(id));
      if (!alvo) throw new ErroHttp(404, "sessão não encontrada");
      banco.encerrar(alvo.id);
      return responder(res, 200, { ok: true });
    }
    if (rota === "/api/historico" && req.method === "GET") {
      const agendamento = url.searchParams.get("agendamento");
      return responder(res, 200, { ok: true, historico: banco.historico(100, agendamento ? numero(agendamento) : null) });
    }

    // --- agendamentos (o agendador roda as ações; veja agendador.ts)
    if (rota === "/api/agendamentos" && req.method === "GET") {
      const agendamentos = banco.agendamentos().map((l) => ({ ...ler(l), execucoes: banco.historico(5, l.id) }));
      return responder(res, 200, { ok: true, agendaveis: AGENDAVEIS, agendamentos });
    }
    if (rota === "/api/agendamentos/salvar" && req.method === "POST") {
      let entrada;
      try {
        entrada = validar(await lerCorpo(req));
      } catch (e) {
        if (e instanceof EntradaInvalida) throw new ErroHttp(400, e.message);
        throw e;
      }
      if (entrada.id && !banco.agendamento(entrada.id)) throw new ErroHttp(404, "agendamento não encontrado");
      const seguinte = proxima(entrada.quando, Date.now());
      if (seguinte === null) throw new ErroHttp(400, "essa data e hora já passaram");
      const id = banco.salvarAgendamento({ ...entrada, ativo: true, proxima: seguinte });
      return responder(res, 200, { ok: true, agendamento: ler(banco.agendamento(id)!) });
    }
    const operacao = rota.match(/^\/api\/agendamentos\/(ativar|apagar|rodar)$/);
    if (operacao && req.method === "POST") {
      const corpo = await lerCorpo(req);
      const linha = banco.agendamento(numero(corpo.id));
      if (!linha) throw new ErroHttp(404, "agendamento não encontrado");
      const a = ler(linha);
      if (operacao[1] === "apagar") banco.apagarAgendamento(a.id);
      else if (operacao[1] === "ativar") {
        if (corpo.ativo) {
          const seguinte = proxima(a.quando, Date.now());
          if (seguinte === null) throw new ErroHttp(400, "essa data e hora já passaram; edite o agendamento");
          banco.marcarAgendamento(a.id, { ativo: true, proxima: seguinte });
        } else banco.marcarAgendamento(a.id, { ativo: false });
      } else {
        if (!agendador) throw new ErroHttp(503, "o agendador não está ligado");
        if (agendador.rodando.has(a.id)) throw new ErroHttp(409, "esse agendamento já está rodando");
        agendador.rodar(a).catch((e) => console.error("agendador:", e)); // pode levar minutos
        return responder(res, 202, { ok: true });
      }
      return responder(res, 200, { ok: true });
    }

    // --- pendências: as do README do servidor e as suas
    if (rota === "/api/pendencias" && req.method === "GET") {
      let readme: string | null = null;
      try {
        const r = await executor("POST", "/acao/arquivo.ler", { params: { caminho: README_SERVIDOR }, origem: "painel" });
        const texto = (r.corpo.resultado as { texto?: unknown } | undefined)?.texto;
        if (r.status === 200 && typeof texto === "string") {
          banco.sincronizarReadme(pendenciasDoReadme(texto));
          readme = README_SERVIDOR;
        }
      } catch {
        // sem executor: mostra o que já está no banco
      }
      return responder(res, 200, { ok: true, readme, pendencias: banco.pendencias() });
    }
    if (rota === "/api/pendencias/nova" && req.method === "POST") {
      const { texto } = await lerCorpo(req);
      if (typeof texto !== "string" || !texto.trim() || texto.length > 300) throw new ErroHttp(400, "escreva a pendência (até 300 letras)");
      banco.novaPendencia(texto.trim());
      return responder(res, 200, { ok: true });
    }
    if (rota === "/api/pendencias/marcar" && req.method === "POST") {
      const { id, feita } = await lerCorpo(req);
      if (!banco.marcarPendencia(numero(id), Boolean(feita))) throw new ErroHttp(404, "pendência não encontrada");
      return responder(res, 200, { ok: true });
    }
    if (rota === "/api/pendencias/apagar" && req.method === "POST") {
      const { id } = await lerCorpo(req);
      if (!banco.apagarPendencia(numero(id))) throw new ErroHttp(404, "só dá para apagar as que você criou (as do README somem quando saem de lá)");
      return responder(res, 200, { ok: true });
    }

    const acao = rota.match(/^\/api\/acao\/([a-z.]+)$/);
    if (acao && req.method === "POST") {
      const nome = acao[1];
      if (!ACOES[nome]) throw new ErroHttp(403, `o painel não faz ${nome}`);
      const { params = {} } = await lerCorpo(req);
      if (typeof params !== "object" || params === null || Array.isArray(params))
        throw new ErroHttp(400, "params deve ser um objeto");
      const r = await executor("POST", `/acao/${nome}`, { params, origem: "painel" });
      if (ACOES[nome].muda) {
        const pedido = r.status === 202 ? String(r.corpo.pedido) : null;
        const estado = pedido ? String(r.corpo.estado ?? "executando") : r.corpo.ok ? "concluido" : "falhou";
        banco.registrar(nome, params, estado, resumir(r.corpo), pedido);
      }
      return responder(res, r.status, r.corpo);
    }

    const pedido = rota.match(/^\/api\/pedido\/([0-9a-f]{8})$/);
    if (pedido && req.method === "GET") {
      const esperar = Math.min(Math.max(Number(url.searchParams.get("esperar")) || 0, 0), 60);
      const r = await executor("GET", `/pedido/${pedido[1]}?esperar=${Math.floor(esperar)}`);
      const p = r.corpo.pedido as Record<string, unknown> | undefined;
      if (p && TERMINADOS.has(String(p.estado)))
        // o trabalho do Claude Code termina com um resumo em vez de resultado
        banco.atualizarPedido(pedido[1], String(p.estado), resumir({
          ok: p.estado === "concluido", erro: p.erro ?? p.resumo ?? p.estado, resultado: p.resultado ?? p.resumo,
        }));
      return responder(res, r.status, r.corpo);
    }

    throw new ErroHttp(404, "rota desconhecida");
  }

  return createServer(async (req, res) => {
    const url = new URL(req.url ?? "/", "http://painel");
    try {
      if (url.pathname === "/saude") return responder(res, 200, { ok: true });
      if (url.pathname.startsWith("/api/")) return await api(req, res, url);
      if (req.method !== "GET" && req.method !== "HEAD") throw new ErroHttp(405, "método não permitido");
      const arquivo = publico.get(url.pathname === "/" ? "/index.html" : url.pathname);
      if (!arquivo) throw new ErroHttp(404, "não encontrado");
      // no-cache com ETag: o navegador sempre pergunta, e o que não mudou volta como 304, sem corpo
      const cabecalhos = { ...SEGURANCA, "Cache-Control": "no-cache", ETag: arquivo.etag, Vary: "Accept-Encoding" };
      if (req.headers["if-none-match"] === arquivo.etag) {
        res.writeHead(304, cabecalhos);
        return res.end();
      }
      const corpo = arquivo.gzip && aceitaGzip(req) ? arquivo.gzip : arquivo.dados;
      res.writeHead(200, {
        ...cabecalhos,
        "Content-Type": arquivo.tipo,
        "Content-Length": String(corpo.length),
        ...(corpo === arquivo.gzip ? { "Content-Encoding": "gzip" } : {}),
      });
      res.end(req.method === "HEAD" ? undefined : corpo);
    } catch (e) {
      if (e instanceof ErroHttp) return responder(res, e.status, { ok: false, erro: e.message });
      console.error(e);
      responder(res, 500, { ok: false, erro: "erro interno do painel (docker logs painel)" });
    }
  });
}
