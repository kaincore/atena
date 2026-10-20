// Servidor HTTP do painel: arquivos da interface e a API (/api/...).
// Toda ação passa pelo executor, que tem a lista fechada do servidor; esta aqui é a lista do painel.
import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { readdirSync, readFileSync } from "node:fs";
import { extname, join } from "node:path";
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
  "gasto.api": { muda: false },
  "servico.logs": { muda: false },
  "pc.estado": { muda: false },
  "app.lista": { muda: false },
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
};

const COOKIE = "atena_sessao";
const LIMITE_CORPO = 64 * 1024;
const TERMINADOS = new Set(["concluido", "falhou", "recusado", "expirado", "cancelado"]);
const TIPOS: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".webmanifest": "application/manifest+json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
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

function carregarPublico(pasta: string): Map<string, { tipo: string; dados: Buffer }> {
  const arquivos = new Map<string, { tipo: string; dados: Buffer }>();
  for (const nome of readdirSync(pasta, { recursive: true }) as string[]) {
    const tipo = TIPOS[extname(nome)];
    if (tipo) arquivos.set("/" + nome.split("\\").join("/"), { tipo, dados: readFileSync(join(pasta, nome)) });
  }
  return arquivos;
}

function responder(res: ServerResponse, status: number, corpo: unknown, cabecalhos: Record<string, string> = {}) {
  const dados = Buffer.from(JSON.stringify(corpo));
  res.writeHead(status, {
    ...SEGURANCA,
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": String(dados.length),
    "Cache-Control": "no-store",
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

function resumir(corpo: Record<string, unknown>): string {
  if (corpo.ok === false) return String(corpo.erro ?? "erro");
  const texto = JSON.stringify(corpo.resultado ?? corpo.mensagem ?? "");
  return texto.length > 300 ? texto.slice(0, 300) + "…" : texto;
}

export function criarServidor(config: Config, banco: Banco): Server {
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
      return responder(res, 200, { ok: true, historico: banco.historico() });
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
        banco.atualizarPedido(pedido[1], String(p.estado), resumir({ ok: p.estado === "concluido", erro: p.erro, resultado: p.resultado }));
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
      res.writeHead(200, {
        ...SEGURANCA,
        "Content-Type": arquivo.tipo,
        "Content-Length": String(arquivo.dados.length),
        "Cache-Control": "no-cache",
      });
      res.end(req.method === "HEAD" ? undefined : arquivo.dados);
    } catch (e) {
      if (e instanceof ErroHttp) return responder(res, e.status, { ok: false, erro: e.message });
      console.error(e);
      responder(res, 500, { ok: false, erro: "erro interno do painel (docker logs painel)" });
    }
  });
}
