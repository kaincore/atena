# Mudanças

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
