# Arquitetura

O servidor é dividido em **zonas por nível de confiança**. Cada zona tem quatro coisas próprias:

| | Onde fica |
|---|---|
| Configuração (composes) | `/opt/atena/stacks/<zona>/<stack>/` (disco do sistema) |
| Dados | `/srv/<zona>/<stack>/` (pode ser outro disco) |
| Rede Docker | `zone-<zona>`, com faixa de IP fixa |
| Limite de CPU/RAM | `atena-<zona>.slice` do systemd |

## As zonas

| Zona | Rede | O que roda | Quem mexe |
|---|---|---|---|
| `prod` | `zone-prod-<cliente>` (10.10.101.0/24 em diante) | Sistemas de clientes, uma rede por cliente | Só o administrador |
| `core` | `zone-core` (10.10.0.0/24) | Dockge, Beszel, ntfy, monitoramento e backup | Só o administrador |
| `apps` | `zone-apps` (10.10.10.0/24) | Apps pessoais (Arca, Open WebUI) | Administrador e a Atena, pelo executor (com foto antes de cada mudança) |
| `ai` | `zone-ai` (10.10.20.0/24) | Ollama, Whisper, voz, LiteLLM | Administrador |
| `agents` | `zone-agents` (10.10.30.0/24) | A Atena (Hermes), agentes de IA e workers | Administrador e agentes, por scripts |
| `lab` | `zone-lab` (10.10.40.0/24) | Ambientes de teste descartáveis | Administrador e agentes, por scripts |

As redes que o Compose cria sozinho (por exemplo, a rede interna do banco de uma stack) usam a faixa `10.20.0.0/16`, longe da rede de casa e do Tailscale (`100.64.0.0/10`).

## Comunicação entre zonas

O Docker já isola redes diferentes: um container da zona `agents` não alcança um da zona `prod`. As exceções são feitas de propósito:

- **Redes de serviço (`svc-*`).** Contêm só um serviço e quem pode usá-lo, e não têm saída para a internet. A `svc-llm` (10.10.250.0/24) liga o LiteLLM aos seus consumidores. Assim o Open WebUI e os agentes usam o LiteLLM, mas não alcançam o Ollama nem o resto da zona `ai`. A `svc-ntfy` (10.10.251.0/24) liga o ntfy a quem publica avisos (o Hermes), sem abrir a zona `core`.
- **Workers dos agentes.** Entram em `zone-agents`, `zone-lab` e `zone-apps`, e alcançam esses serviços pelo nome. O orquestrador dos agentes (o Hermes) fica só em `zone-agents`, `svc-llm` e `svc-ntfy`, para que nada de teste no lab consiga falar com quem executa comandos.
- **Nenhum agente** entra em `zone-core` nem em `zone-prod-*`.

## Executor de ações

O executor (`/usr/local/sbin/atena-executor`) é o **único caminho** dos clientes (a Atena e, no futuro, um painel) até o servidor. Ele roda no próprio servidor, como o usuário `atena-exec`, e ouve o socket `/run/atena-executor/executor.sock` (grupo `atena-acoes`).

<p align="center"><img src="../assets/fluxo.svg" width="100%" alt="Caminho de um pedido: você fala no Telegram com o Hermes, que usa o LiteLLM para chegar ao Claude ou aos modelos de casa. Pelo socket, o Hermes pede ao executor, que age no servidor (Docker, systemd, arquivos, PC). Para aprovar, o executor avisa o celular pelo ntfy, e o toque em Aprovar volta pelo ntfy até o executor."></p>

<details>
<summary>Diagrama em texto</summary>

```text
Você (Telegram) ──> Hermes (zona agents) ──> LiteLLM (svc-llm) ──> Anthropic ou modelos de casa
                       │
                       └─ socket ──> executor (servidor) ──> Docker, systemd, arquivos, PC
Celular (app ntfy) <── alertas e pedidos de aprovação ── executor
       └─ toque em Aprovar ──> ntfy (tópico respostas) ──> executor
```

</details>

- **Lista fechada.** Cada ação é uma função com comando fixo e parâmetros validados contra o que existe (nome da stack, unidade, caminho). Não há shell.
- **Um token por cliente.** O token diz quais ações e quais zonas o cliente pode pedir. Só o hash fica guardado (`/etc/atena/executor/tokens.json`).
- **Zona da stack.** Vem da pasta do compose (`/opt/atena/stacks/<zona>/...`) ou das redes `zone-*`. Na dúvida, vale a mais restrita.
- **Aprovação no celular.** Uma ação que muda algo pode virar um pedido: o executor manda uma notificação com Aprovar e Recusar, e só roda depois do toque. O código do pedido só existe na notificação, então o cliente não consegue se aprovar. Cada token diz quais ações pedem o celular.
- **Leitura sem segredos.** O serviço tem só a capacidade `CAP_DAC_READ_SEARCH`: lê qualquer arquivo e só escreve nas pastas dele, nas entregas da Atena, no Arca e nas stacks da zona `apps` (estas duas por ACL, sem tirar o dono de nada). Áreas do sistema e arquivos de chave, token e senha são recusados, e linhas com senha, token ou chave saem com `***`.
- **Registro.** Cada pedido vai para o journal (`journalctl -u atena-executor`), com cliente, ação, parâmetros e resultado.
- **Stacks de apps com foto.** `stack.editar` guarda o conteúdo anterior antes de gravar, e `stack.desfazer` volta. Uma mudança no compose só fica se o compose inteiro (`docker compose config`, com includes e overrides) caber nas regras da zona: nada do host (`privileged`, `cap_add`, `devices`, rede ou PID do host, socket do Docker), pastas só da própria stack e de `/srv/apps/<stack>`, redes só `zone-apps` e `svc-llm`, portas sempre com IP na frente. `stack.aplicar` confere de novo e sobe em segundo plano.

| Grupo | Ações |
|---|---|
| Ver o servidor | `status.servicos`, `status.recursos`, `status.containers`, `status.sistema`, `gasto.api`, `servico.logs`, `servico.journal`, `sistema.processos`, `sistema.rede`, `sistema.sensores` (temperaturas e ventoinhas) |
| Arquivos | `arquivo.ler`, `arquivo.buscar`, `arquivo.procurar`, `arquivo.entregar` |
| Texto privado | `local.processar` (Ollama do servidor ou LM Studio do PC, sem nuvem) |
| Arca | `arca.lista`, `arca.pegar`, `arca.guardar` (pelo nome original; guardar não substitui nada) |
| Stacks de apps | `stack.editar`, `stack.aplicar`, `stack.fotos`, `stack.desfazer` |
| Agir | `servico.reiniciar` (pode pedir o celular) |
| PC da rede de casa (opcional) | `pc.estado`, `pc.ligar`, `pc.desligar`, `pc.reiniciar`, `pc.cancelar` |

Os avisos do próprio servidor também vão ao celular: o `atena-avisar` avisa quando uma unidade `atena-*` falha e, de 5 em 5 minutos, quando um container para ou fica doente.

## A Atena (Hermes)

A Atena é uma assistente pessoal feita com o [Hermes Agent](https://github.com/NousResearch/hermes-agent). Ela conversa com você pelo Telegram e cuida do servidor.

- **Onde roda.** Container `hermes` na zona `agents`, como o usuário `hermes` do servidor: sem Docker, sem sudo e sem rede até a sua casa. Os dados dela (configuração, memória, notas) ficam em `/srv/agents/hermes`.
- **Como pensa.** Pelo LiteLLM, com uma chave própria e teto mensal. Haiku por padrão; mensagens de voz são transcritas pelo Whisper da casa. Com `ATENA_VOZ=sim` (e GPU), ela também responde em voz, gerada em casa pelo Kokoro.
- **Como age.** Só pelo executor, com um token sem a zona `prod`. Comandos no próprio container passam pela aprovação "smart": um modelo auxiliar libera o que é seguro e manda o destrutivo para você decidir.
- **Personalidade e regras** em `SOUL.md`: confere antes de afirmar e pede o seu ok para qualquer medida destrutiva.
- **Habilidades.** `servidor-atena` (como usar o executor) e `notas` (guardar e consultar o que você manda).
- **Ronda.** De 3 em 3 minutos, um script barato lista o que está fora do normal. O Hermes compara com a lista anterior e só acorda a IA (e gasta API) quando ela muda.
- **Dados privados.** Documento de cliente ou dado que não pode ir para a nuvem vai para `local.processar`: o executor extrai o texto e pergunta a um modelo de casa, e só a resposta volta para a Atena.

## Limites de CPU e RAM

Cada zona é um slice do systemd dentro de `atena.slice`. Os containers entram no slice com `cgroup_parent: atena-<zona>.slice` no compose.

| Slice | Regra |
|---|---|
| `atena-prod` | `CPUWeight=1000`, `MemoryLow=4G` (memória protegida) |
| `atena-core` | `CPUWeight=500`, `MemoryLow=512M` |
| `atena-apps` | `MemoryMax=4G` |
| `atena-ai` | `MemoryMax=6G` |
| `atena-agents` | `CPUWeight=50`, `CPUQuota=600%`, `MemoryMax=6G` |
| `atena-lab` | `CPUWeight=50`, `CPUQuota=600%`, `MemoryMax=4G` |

O `atena.slice` tem `MemoryLow=5G`, porque a proteção de memória de um slice só vale se o slice pai também tiver.

## Entrada e saída

- **Saída dos containers:** internet e DNS do roteador, sim. Rede de casa, aparelhos do Tailscale e o próprio servidor, não.
- **Entrada pela rede de casa:** qualquer aparelho da rede de casa acessa o que estiver publicado no IP do servidor.
- **Entrada de fora de casa:** só pelo Tailscale, com `tailscale serve` em cada serviço.
- **Internet:** nada fica exposto.

Detalhes e testes em [segurança](seguranca.md).

## Regras para toda stack

1. O compose fica em `/opt/atena/stacks/<zona>/<stack>/` e os dados em `/srv/<zona>/<stack>/`. O nome da stack é único entre todas as zonas.
2. Use a rede da zona (`external: true`) e o slice da zona (`cgroup_parent`).
3. Bancos de dados ficam numa rede interna da própria stack (`internal: true`).
4. Fixe a versão da imagem (nada de `:latest`).
5. Ao publicar uma porta, escreva o IP: `"<ip-do-servidor>:<porta>:<porta>"` para a rede de casa, ou `"127.0.0.1:<porta>:<porta>"` só para o servidor.

```yaml
services:
  app:
    image: exemplo/app:1.2.3
    cgroup_parent: atena-apps.slice
    volumes:
      - /srv/apps/exemplo/data:/data
    networks: [zone, backend]
    ports:
      - "192.168.0.10:8080:8080"   # rede de casa
      - "127.0.0.1:8080:8080"      # para o tailscale serve
    restart: unless-stopped

  db:
    image: postgres:17.11-alpine3.24
    cgroup_parent: atena-apps.slice
    volumes:
      - /srv/apps/exemplo/db:/var/lib/postgresql/data
    networks: [backend]
    restart: unless-stopped

networks:
  zone:
    name: zone-apps
    external: true
  backend:
    internal: true
```

## Dockge e as subpastas

O Dockge só enxerga stacks que ficam direto numa pasta. Como as stacks ficam em `/opt/atena/stacks/<zona>/<stack>`, ele lê `/opt/atena/dockge`, que tem um atalho para cada stack. O `atena-stacks-sync.path` cria e remove esses atalhos sozinho. Crie stacks novas na pasta da zona, não pelo botão do Dockge.
