// Cliente do atena-executor: HTTP no socket unix dele, com o token do painel.
// O token é lido a cada pedido, então trocar o arquivo não exige reiniciar o painel.
import { request } from "node:http";
import { readFileSync } from "node:fs";

export type RespostaExecutor = { status: number; corpo: Record<string, unknown> };

export class SemToken extends Error {}
// o executor não respondeu no prazo: a ação pode ter acontecido mesmo assim
export class PrazoEsgotado extends Error {}

export function pedirExecutor(
  socket: string,
  arquivoToken: string,
  metodo: "GET" | "POST",
  caminho: string,
  corpo?: unknown,
  segundos = 180,
): Promise<RespostaExecutor> {
  let token: string;
  try {
    token = readFileSync(arquivoToken, "utf8").trim();
  } catch {
    return Promise.reject(new SemToken("o painel ainda não tem o token do executor"));
  }
  if (!token) return Promise.reject(new SemToken("o arquivo do token do executor está vazio"));
  const dados = corpo === undefined ? undefined : Buffer.from(JSON.stringify(corpo));
  return new Promise((resolve, reject) => {
    const pedido = request(
      {
        socketPath: socket,
        method: metodo,
        path: caminho,
        timeout: segundos * 1000,
        headers: {
          Authorization: `Bearer ${token}`,
          ...(dados ? { "Content-Type": "application/json", "Content-Length": dados.length } : {}),
        },
      },
      (resposta) => {
        const partes: Buffer[] = [];
        resposta.on("data", (p: Buffer) => partes.push(p));
        resposta.on("end", () => {
          const texto = Buffer.concat(partes).toString("utf8");
          try {
            resolve({ status: resposta.statusCode ?? 502, corpo: JSON.parse(texto) });
          } catch {
            resolve({ status: 502, corpo: { ok: false, erro: "resposta inválida do executor" } });
          }
        });
      },
    );
    pedido.on("timeout", () => pedido.destroy(new PrazoEsgotado("o executor demorou demais para responder")));
    pedido.on("error", reject);
    if (dados) pedido.write(dados);
    pedido.end();
  });
}
