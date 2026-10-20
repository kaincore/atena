// Painel Atena: o servidor no navegador do PC e do celular (PWA).
// O container não tem rede: o Tailscale entrega as visitas por um socket unix (tailscale serve) e
// o painel fala com o executor por outro. Sem socket do Docker, sem root, sistema de arquivos só leitura.
import { chmodSync, rmSync } from "node:fs";
import { join } from "node:path";
import { Banco } from "./banco.ts";
import { criarServidor } from "./servidor.ts";

const dados = process.env.PAINEL_DADOS ?? "/dados";
const socket = process.env.PAINEL_SOCKET ?? join(dados, "run", "painel.sock");
const porta = process.env.PAINEL_PORTA; // só para desenvolvimento: escuta em 127.0.0.1:<porta>

const banco = new Banco(join(dados, "painel.db"));
banco.limpar();
setInterval(() => banco.limpar(), 3600_000).unref();

const servidor = criarServidor(
  {
    publico: new URL("../public", import.meta.url).pathname,
    arquivoSenha: join(dados, "senha"),
    arquivoToken: join(dados, "executor.token"),
    socketExecutor: process.env.EXECUTOR_SOCKET ?? "/run/atena-executor/executor.sock",
  },
  banco,
);

if (porta) {
  servidor.listen(Number(porta), "127.0.0.1", () => console.log(`painel em http://127.0.0.1:${porta}`));
} else {
  rmSync(socket, { force: true }); // sobra de um container anterior
  servidor.listen(socket, () => {
    chmodSync(socket, 0o660);
    console.log(`painel no socket ${socket}`);
  });
}

for (const sinal of ["SIGTERM", "SIGINT"] as const) {
  process.on(sinal, () => {
    servidor.close();
    servidor.closeAllConnections();
    banco.db.close();
    process.exit(0);
  });
}
