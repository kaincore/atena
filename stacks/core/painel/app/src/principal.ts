// Painel Atena: o servidor no navegador do PC e do celular (PWA).
// O container não tem rede: o Tailscale entrega as visitas por um socket unix (tailscale serve), a rede de
// casa, se ligada, por outro (atena-painel-casa.socket, do systemd), e o painel fala com o executor por um
// terceiro. Sem socket do Docker, sem root, sistema de arquivos só leitura.
import { chmodSync, rmSync } from "node:fs";
import type { Server } from "node:http";
import { join } from "node:path";
import { Agendador } from "./agendador.ts";
import { Banco } from "./banco.ts";
import { pedirExecutor } from "./executor.ts";
import { criarServidor } from "./servidor.ts";

const dados = process.env.PAINEL_DADOS ?? "/dados";
const socket = process.env.PAINEL_SOCKET ?? join(dados, "run", "painel.sock");
// a entrada da rede de casa, em HTTP (ATENA_PAINEL_CASA=sim no atena.conf)
const casa = process.env.PAINEL_CASA === "sim";
const socketCasa = process.env.PAINEL_SOCKET_CASA ?? join(dados, "run", "painel-casa.sock");
const porta = process.env.PAINEL_PORTA; // só para desenvolvimento: escuta em 127.0.0.1:<porta>

const banco = new Banco(join(dados, "painel.db"));
banco.limpar();
// antes do agendador: o que ficou "executando" é do painel que parou, e não terá mais resposta
const interrompidas = banco.marcarInterrompidas();
if (interrompidas) console.log(`painel: ${interrompidas} ${interrompidas === 1 ? "execução interrompida" : "execuções interrompidas"} pelo reinício`);
setInterval(() => banco.limpar(), 3600_000).unref();

const config = {
  publico: new URL("../public", import.meta.url).pathname,
  arquivoSenha: join(dados, "senha"),
  arquivoToken: join(dados, "executor.token"),
  socketExecutor: process.env.EXECUTOR_SOCKET ?? "/run/atena-executor/executor.sock",
};
const agendador = new Agendador(banco, (metodo, caminho, corpo) =>
  pedirExecutor(config.socketExecutor, config.arquivoToken, metodo, caminho, corpo));
const servidor = criarServidor(config, banco, agendador);
agendador.iniciar();

if (porta) {
  servidor.listen(Number(porta), "127.0.0.1", () => console.log(`painel em http://127.0.0.1:${porta}`));
} else {
  const escutar = (alvo: Server, caminho: string) => {
    rmSync(caminho, { force: true }); // sobra de um container anterior
    alvo.listen(caminho, () => {
      chmodSync(caminho, 0o660);
      console.log(`painel no socket ${caminho}`);
    });
  };
  escutar(servidor, socket);
  // desligada, o socket some: o que sobrar repassando para ele recebe recusa, e não um painel velho
  if (casa) escutar(servidor.casa, socketCasa);
  else rmSync(socketCasa, { force: true });
}

for (const sinal of ["SIGTERM", "SIGINT"] as const) {
  process.on(sinal, () => {
    agendador.parar();
    for (const s of [servidor, servidor.casa]) {
      s.close();
      s.closeAllConnections();
    }
    banco.db.close();
    process.exit(0);
  });
}
