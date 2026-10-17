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
| `core` | `zone-core` (10.10.0.0/24) | Dockge, Beszel, monitoramento e backup | Só o administrador |
| `apps` | `zone-apps` (10.10.10.0/24) | Apps pessoais (Arca, Open WebUI) | Administrador |
| `ai` | `zone-ai` (10.10.20.0/24) | Ollama, Whisper, LiteLLM | Administrador |
| `agents` | `zone-agents` (10.10.30.0/24) | Agentes de IA e workers | Administrador e agentes, por scripts |
| `lab` | `zone-lab` (10.10.40.0/24) | Ambientes de teste descartáveis | Administrador e agentes, por scripts |

As redes que o Compose cria sozinho (por exemplo, a rede interna do banco de uma stack) usam a faixa `10.20.0.0/16`, longe da rede de casa e do Tailscale (`100.64.0.0/10`).

## Comunicação entre zonas

O Docker já isola redes diferentes: um container da zona `agents` não alcança um da zona `prod`. As exceções são feitas de propósito:

- **Redes de serviço (`svc-*`).** Contêm só um serviço e quem pode usá-lo, e não têm saída para a internet. A `svc-llm` (10.10.250.0/24) liga o LiteLLM aos seus consumidores. Assim o Open WebUI e os agentes usam o LiteLLM, mas não alcançam o Ollama nem o resto da zona `ai`.
- **Workers dos agentes.** Entram em `zone-agents`, `zone-lab` e `zone-apps`, e alcançam esses serviços pelo nome. O orquestrador dos agentes fica só em `zone-agents` + `svc-llm`, para que nada de teste no lab consiga falar com quem executa comandos.
- **Nenhum agente** entra em `zone-core` nem em `zone-prod-*`.

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
