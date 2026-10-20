// Senha do painel: hash scrypt num arquivo, gravado pelo atena-painel-senha no servidor.
// Formato (uma linha): scrypt$N$r$p$<sal base64>$<hash base64>. O mesmo que o hashlib.scrypt do Python.
import { randomBytes, scrypt, timingSafeEqual } from "node:crypto";
import { readFileSync } from "node:fs";

export type Senha = { N: number; r: number; p: number; sal: Buffer; hash: Buffer; id: string };

const MEMORIA_MAXIMA = 128 * 1024 * 1024; // N=2^15, r=8 usa 32 MB, acima do padrão do Node

export function lerSenha(arquivo: string): Senha | null {
  let texto: string;
  try {
    texto = readFileSync(arquivo, "utf8").trim();
  } catch {
    return null;
  }
  const partes = texto.split("$");
  if (partes.length !== 6 || partes[0] !== "scrypt") return null;
  const [N, r, p] = partes.slice(1, 4).map(Number);
  const sal = Buffer.from(partes[4], "base64");
  const hash = Buffer.from(partes[5], "base64");
  if (![N, r, p].every(Number.isInteger) || sal.length < 16 || hash.length < 16) return null;
  // o sal muda a cada troca de senha: as sessões guardam este id e caem quando ele muda
  return { N, r, p, sal, hash, id: partes[4] };
}

function derivar(texto: string, sal: Buffer, tamanho: number, N: number, r: number, p: number): Promise<Buffer> {
  return new Promise((resolve, reject) =>
    scrypt(texto.normalize("NFC"), sal, tamanho, { N, r, p, maxmem: MEMORIA_MAXIMA }, (erro, chave) =>
      erro ? reject(erro) : resolve(chave),
    ),
  );
}

export async function conferir(senha: Senha, tentativa: string): Promise<boolean> {
  const chave = await derivar(tentativa, senha.sal, senha.hash.length, senha.N, senha.r, senha.p);
  return timingSafeEqual(chave, senha.hash);
}

export async function gerar(texto: string, N = 2 ** 15, r = 8, p = 1): Promise<string> {
  const sal = randomBytes(16);
  const hash = await derivar(texto, sal, 32, N, r, p);
  return ["scrypt", N, r, p, sal.toString("base64"), hash.toString("base64")].join("$");
}
