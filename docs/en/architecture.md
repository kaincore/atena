# Architecture

The server is split into **zones by trust level**. Each zone has four things of its own:

| | Where it lives |
|---|---|
| Configuration (compose files) | `/opt/atena/stacks/<zone>/<stack>/` (system disk) |
| Data | `/srv/<zone>/<stack>/` (can be another disk) |
| Docker network | `zone-<zone>`, with a fixed IP range |
| CPU/RAM limit | systemd's `atena-<zone>.slice` |

## The zones

| Zone | Network | What runs there | Who changes it |
|---|---|---|---|
| `prod` | `zone-prod-<client>` (10.10.101.0/24 onward) | Client systems, one network per client | Admin only |
| `core` | `zone-core` (10.10.0.0/24) | Dockge, Beszel, ntfy, monitoring and backup | Admin only |
| `apps` | `zone-apps` (10.10.10.0/24) | Personal apps (Arca, Open WebUI) | Admin |
| `ai` | `zone-ai` (10.10.20.0/24) | Ollama, Whisper, LiteLLM | Admin |
| `agents` | `zone-agents` (10.10.30.0/24) | Atena (Hermes), AI agents and workers | Admin, and agents through scripts |
| `lab` | `zone-lab` (10.10.40.0/24) | Disposable test environments | Admin, and agents through scripts |

Networks that Compose creates on its own (for example, a stack's internal database network) use `10.20.0.0/16`, away from the home network and from Tailscale (`100.64.0.0/10`).

## Communication between zones

Docker already isolates different networks: a container in `agents` can't reach one in `prod`. The exceptions are deliberate:

- **Service networks (`svc-*`).** They hold only one service and whoever may use it, with no internet access. `svc-llm` (10.10.250.0/24) connects LiteLLM to its consumers. Open WebUI and the agents can use LiteLLM, but can't reach Ollama or anything else in `ai`. `svc-ntfy` (10.10.251.0/24) connects ntfy to whoever publishes notifications (Hermes) without opening the `core` zone.
- **Agent workers.** They join `zone-agents`, `zone-lab` and `zone-apps`, and reach those services by name. The agent orchestrator (Hermes) stays only in `zone-agents`, `svc-llm` and `svc-ntfy`, so nothing under test in `lab` can talk to the thing that runs commands.
- **No agent** joins `zone-core` or `zone-prod-*`.

## Action executor

The executor (`/usr/local/sbin/atena-executor`) is the **only path** from clients (Atena and, later, a dashboard) to the server. It runs on the server itself as the `atena-exec` user and listens on the socket `/run/atena-executor/executor.sock` (group `atena-acoes`).

```
You (Telegram) ──> Hermes (agents zone) ──> LiteLLM (svc-llm) ──> Anthropic or home models
                      │
                      └─ socket ──> executor (server) ──> Docker, systemd, files, PC
Phone (ntfy app) <── alerts and approval requests ── executor
      └─ tap Approve ──> ntfy (respostas topic) ──> executor
```

- **Closed list.** Each action is a function with a fixed command and parameters checked against what exists (stack name, unit, path). There is no shell.
- **One token per client.** The token says which actions and which zones the client may request. Only the hash is stored (`/etc/atena/executor/tokens.json`).
- **Stack zone.** It comes from the compose folder (`/opt/atena/stacks/<zone>/...`) or from the `zone-*` networks. When in doubt, the most restricted one wins.
- **Approval on your phone.** An action that changes something can become a request: the executor sends a notification with Approve and Reject, and only runs after the tap. The request code exists only inside the notification, so the client can't approve itself. Each token says which actions need the phone.
- **Reading without secrets.** The service has a single capability, `CAP_DAC_READ_SEARCH`: it reads any file and writes nothing outside its own folders. System areas and key, token and password files are refused, and lines with a password, token or key come out as `***`.
- **Audit log.** Every request goes to the journal (`journalctl -u atena-executor`) with client, action, parameters and result.

| Group | Actions |
|---|---|
| Look at the server | `status.servicos`, `status.recursos`, `status.containers`, `status.sistema`, `gasto.api`, `servico.logs`, `servico.journal`, `sistema.processos`, `sistema.rede` |
| Files | `arquivo.ler`, `arquivo.buscar`, `arquivo.procurar`, `arquivo.entregar` |
| Private text | `local.processar` (the server's Ollama or the PC's LM Studio, no cloud) |
| Act | `servico.reiniciar` (can require the phone) |
| Home PC (optional) | `pc.estado`, `pc.ligar`, `pc.desligar`, `pc.reiniciar`, `pc.cancelar` |

The server's own alerts also go to your phone: `atena-avisar` reports when an `atena-*` unit fails and, every 5 minutes, when a container stops or becomes unhealthy.

## Atena (Hermes)

Atena is a personal assistant built on [Hermes Agent](https://github.com/NousResearch/hermes-agent). She talks to you on Telegram and looks after the server. Her personality and skills are written in Portuguese.

- **Where she runs.** The `hermes` container in the `agents` zone, as the server's `hermes` user: no Docker, no sudo and no route to your home network. Her data (config, memory, notes) lives in `/srv/agents/hermes`.
- **How she thinks.** Through LiteLLM, with her own key and a monthly cap. Haiku by default; voice messages are transcribed by the home Whisper.
- **How she acts.** Only through the executor, with a token that excludes the `prod` zone. Commands inside her own container go through "smart" approval: a helper model allows what is safe and sends anything destructive to you.
- **Personality and rules** in `SOUL.md`: she checks before stating something and asks for your OK before anything destructive.
- **Skills.** `servidor-atena` (how to use the executor) and `notas` (keeping and finding what you send her).
- **Patrol (ronda).** Every 3 minutes a cheap script lists what is out of the ordinary. Hermes compares it with the previous list and only wakes the AI (and spends API credit) when it changes.
- **Private data.** A client document, or anything that can't go to the cloud, goes to `local.processar`: the executor extracts the text and asks a home model, and only the answer goes back to Atena.

## CPU and RAM limits

Each zone is a systemd slice under `atena.slice`. Containers join the slice with `cgroup_parent: atena-<zone>.slice` in the compose file.

| Slice | Rule |
|---|---|
| `atena-prod` | `CPUWeight=1000`, `MemoryLow=4G` (protected memory) |
| `atena-core` | `CPUWeight=500`, `MemoryLow=512M` |
| `atena-apps` | `MemoryMax=4G` |
| `atena-ai` | `MemoryMax=6G` |
| `atena-agents` | `CPUWeight=50`, `CPUQuota=600%`, `MemoryMax=6G` |
| `atena-lab` | `CPUWeight=50`, `CPUQuota=600%`, `MemoryMax=4G` |

`atena.slice` has `MemoryLow=5G`, because a slice's memory protection only applies if its parent has protection too.

## Inbound and outbound

- **Containers going out:** the internet and the router's DNS, yes. The home network, Tailscale devices and the server itself, no.
- **Coming in from the home network:** any home device reaches whatever is published on the server's IP.
- **Coming in from away:** only through Tailscale, with `tailscale serve` per service.
- **Internet:** nothing is exposed.

Details and tests in [security](security.md).

## Rules for every stack

1. The compose file lives in `/opt/atena/stacks/<zone>/<stack>/` and data in `/srv/<zone>/<stack>/`. Stack names are unique across all zones.
2. Use the zone's network (`external: true`) and the zone's slice (`cgroup_parent`).
3. Databases go on the stack's own internal network (`internal: true`).
4. Pin the image version (no `:latest`).
5. When publishing a port, always write the IP: `"<server-ip>:<port>:<port>"` for the home network, or `"127.0.0.1:<port>:<port>"` for the server only.

```yaml
services:
  app:
    image: example/app:1.2.3
    cgroup_parent: atena-apps.slice
    volumes:
      - /srv/apps/example/data:/data
    networks: [zone, backend]
    ports:
      - "192.168.0.10:8080:8080"   # home network
      - "127.0.0.1:8080:8080"      # for tailscale serve
    restart: unless-stopped

  db:
    image: postgres:17.11-alpine3.24
    cgroup_parent: atena-apps.slice
    volumes:
      - /srv/apps/example/db:/var/lib/postgresql/data
    networks: [backend]
    restart: unless-stopped

networks:
  zone:
    name: zone-apps
    external: true
  backend:
    internal: true
```

## Dockge and subfolders

Dockge only sees stacks placed directly inside one folder. Since stacks live in `/opt/atena/stacks/<zone>/<stack>`, Dockge reads `/opt/atena/dockge` instead, which holds a symlink to each stack. `atena-stacks-sync.path` creates and removes those links automatically. Create new stacks in the zone's folder, not with Dockge's button.
