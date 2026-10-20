# Mudanças

## 0.4.0 (2026-10-20)

O lab: a Atena manda trabalhos de programação ao Claude Code. Extraído do primeiro servidor Atena.

- **Claude Code pela Atena** (opcional, `./install.sh --lab`): `claude.tarefa` põe o trabalho na fila, e o runner roda o Claude Code como `atena-claude` (sem sudo, sem Docker) em `/srv/lab/projetos/<projeto>`, num sandbox estrito, até 3 ao mesmo tempo. O Claude Code tem versão fixa (`ATENA_CLAUDE_VERSAO`), baixada do repositório oficial e conferida pelo checksum.
- **Permissões e perguntas no celular:** o que o Claude Code pede vem com Aprovar e Recusar; uma dúvida dele chega ao celular e à Atena, que decide se você não responder em 10 min.
- **Contas:** as de `ATENA_CLAUDE_CONTAS`, com login pelo `atena-claude-conta`. No limite de uso, o trabalho para e a Atena avisa; a troca automática para outra conta é opcional (`ATENA_CLAUDE_TROCA=sim`). Continuar em outra conta, a seu pedido, leva a conversa junto.
- **Apps do lab:** `app.publicar` constrói pelo Dockerfile e põe no ar na zona lab (porta 8000-8999 na rede de casa e, com Tailscale, fora de casa). `app.reiniciar`, `app.parar`, `app.cancelar`, `app.apagar` (o código vai para uma lixeira por 30 dias), `app.restaurar`, `app.comando` e `app.lista`. Publicar e apagar pedem o celular.
- **A Atena no lab:** os projetos ficam no terminal dela, para ajustes pequenos com commit; a habilidade `lab` diz quando fazer ela mesma e quando mandar ao Claude Code; a ronda avisa quando um trabalho termina e quando o Claude Code pergunta algo.
- **Lab interativo:** o seu Claude Code em `/srv/lab` ganha o mesmo sandbox e um guarda de escopo.
- **Travas para quem escreve nos projetos:** o Claude Code só lê a configuração da conta e o `lab.json`, sem hooks do projeto, e o git do runner ignora fsmonitor e hooks; um `.git/config` que rode comandos faz o trabalho ser recusado.
- Correção que veio junto: depois de trocar de conta, o aviso de limite da rodada anterior não vale mais para a nova.
- Ainda não: as skills do Claude Code e os prints de tela (próxima versão).
- Testado numa VM Ubuntu 26.04 sem GPU, instalando o lab sobre uma 0.3.1 com a Atena: o Claude Code (de mentira, com a ponte e a fila de verdade) fez um app e perguntou pela ponte; a Atena respondeu; o app foi publicado com o Aprovar pelo ntfy, respondeu na rede de casa, foi parado, apagado (código para a lixeira) e restaurado; a Atena fez commit no projeto pelo terminal dela; e o instalador rodou de novo sem refazer o token nem mexer nas permissões. O teste achou dois defeitos, já corrigidos: o arquivo de configuração do git da Atena tinha ficado fora do repositório, e o needrestart reiniciava serviços durante a instalação.

## 0.3.1 (2026-10-20)

- **Correção nas stacks de apps:** com o Docker Compose 2.x, o executor não enxergava o `env_file` e o `label_file` de um compose, e deixava uma stack de apps ler o `.env` de outra. Agora ele lê o compose uma segunda vez com `--no-interpolate`, que mostra esses caminhos em qualquer versão (testado no 2.24, 2.38, 2.40 e 5.6). Com o Compose v5, que o instalador traz, a regra já funcionava.

## 0.3.0 (2026-10-20)

Voz, temperaturas, o Arca e as stacks de apps nas mãos da Atena, extraídos do primeiro servidor Atena.

- **Temperaturas e ventoinhas**: `sistema.sensores` (CPU AMD ou Intel, NVMe, GPU e o chip da placa) e as temperaturas no `status.recursos`. A ronda avisa CPU acima de 85 °C e NVMe acima de 70 °C. O chip da placa, que lê as ventoinhas, vem de um módulo opcional (`ATENA_SENSORES_MODULO`).
- **Arca pela Atena**: `arca.lista`, `arca.pegar` e `arca.guardar`, pelo nome original e no formato do próprio Arca (texto com segredos ocultos).
- **Stacks de apps pela Atena**: `stack.editar` (com foto antes de cada mudança), `stack.desfazer`, `stack.fotos` e `stack.aplicar`, que sobe a stack em segundo plano. O compose inteiro precisa caber nas regras da zona `apps`.
- **Voz** (opcional, com GPU: `ATENA_VOZ=sim`): stack `ai/voz` com o Kokoro, modelo `voz` no LiteLLM (custo zero) e respostas em voz no Telegram com `/voice`.
- O Ollama sai da GPU depois de 2 minutos sem uso, para caber com o Whisper e a voz numa placa de 6 GB.
- O executor reconhece chave privada pelo cabeçalho do bloco PEM (antes recusava até o próprio código) e aceita pedidos de até 1 MB.
- Numa atualização, o token da Atena ganha as ações novas, com as mesmas zonas e a mesma regra de aprovação. Os passos que são seus (LiteLLM, chave da Atena e Ollama) estão em [operação](docs/pt/operacao.md#atualizar-da-02-para-a-03).
- O token da Atena agora é gravado num arquivo novo e movido para o lugar, e o instalador refaz o token quando o do arquivo não vale mais: no Ubuntu 26.04, o `install` não copia de `/dev/stdin` por cima de um arquivo que já existe.
- Testado numa VM Ubuntu 26.04 sem GPU, atualizando uma 0.2 em uso: a Atena listou, pegou e guardou arquivos no Arca, editou e aplicou a stack do Arca (com o `docker compose up --build` dentro do sandbox do executor), desfez a edição, teve compose com `privileged` e `.env` recusados, e o instalador rodou mais três vezes sem refazer o token nem duplicar nada.

## 0.2.0 (2026-10-19)

O executor de ações e a Atena (Hermes), extraídos do primeiro servidor Atena.

- **Executor de ações** (`atena-executor`): o único caminho dos agentes até o servidor. Lista fechada de ações, sem shell, token por cliente com ações e zonas, leitura do servidor inteiro sem segredos (só `CAP_DAC_READ_SEARCH`), aprovação no celular pelo ntfy, PC opcional da rede de casa (Wake-on-LAN e desligar por SSH restrito) e texto privado num modelo de casa (`local.processar`).
- **ntfy** na zona `core`, com login obrigatório, e a rede interna `svc-ntfy`.
- **Avisos no celular**: unidade `atena-*` que falha e container parado ou doente (`atena-avisar`, `atena-vigia.timer`).
- **A Atena** (opcional, `--hermes`): Hermes Agent na zona `agents`, sem Docker nem sudo, com personalidade, habilidades `servidor-atena` e `notas`, ronda de 3 em 3 minutos que só gasta API quando algo muda, voz pelo Whisper e configuração aplicada pelo `hermes config set`.
- Comandos novos: `atena-ntfy-celular`, `atena-hermes-chave` e `atena-telegram` (os segredos não aparecem na tela).
- LiteLLM com o modelo `whisper`, para quem só alcança o LiteLLM.
- `atena.conf`: `ATENA_TZ`, `ATENA_NTFY_URL`, modelo local e o PC opcional (`ATENA_PC_*`). Um `atena.conf` antigo continua valendo.
- Testes do executor e da ronda, rodando a cada envio ao GitHub. O verificador de vazamentos reconhece tokens do Telegram, do ntfy e do executor.
- Instalador testado de ponta a ponta numa VM Ubuntu 26.04 sem GPU, com `--hermes`: executor pela Atena, segredos recusados, aprovação pelo ntfy de verdade, avisos de falha, chave do LiteLLM e três execuções seguidas sem duplicar nada.

## 0.1.0 (2026-10-17)

Primeira versão do modelo, extraída do primeiro servidor Atena.

- Seis zonas (`prod`, `core`, `apps`, `ai`, `agents`, `lab`) com redes de faixa fixa e limites de CPU/RAM por slice do systemd.
- Firewall dos containers: saída só para a internet, entrada só da rede de casa.
- Instalador em etapas, que pode rodar de novo sem estragar o que já existe.
- GPU NVIDIA opcional (driver headless assinado, sem DKMS) e Tailscale opcional.
- Stacks: Dockge, Beszel, Ollama, Whisper, LiteLLM (com tetos de gasto por modelo e por chave), Open WebUI e Arca.
- Verificador de vazamentos, trava de commit e verificação no GitHub (shellcheck, composes e gitleaks).
- Documentação em português e inglês.
