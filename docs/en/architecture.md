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
| `core` | `zone-core` (10.10.0.0/24) | Dockge, Beszel, monitoring and backup | Admin only |
| `apps` | `zone-apps` (10.10.10.0/24) | Personal apps (Arca, Open WebUI) | Admin |
| `ai` | `zone-ai` (10.10.20.0/24) | Ollama, Whisper, LiteLLM | Admin |
| `agents` | `zone-agents` (10.10.30.0/24) | AI agents and workers | Admin, and agents through scripts |
| `lab` | `zone-lab` (10.10.40.0/24) | Disposable test environments | Admin, and agents through scripts |

Networks that Compose creates on its own (for example, a stack's internal database network) use `10.20.0.0/16`, away from the home network and from Tailscale (`100.64.0.0/10`).

## Communication between zones

Docker already isolates different networks: a container in `agents` can't reach one in `prod`. The exceptions are deliberate:

- **Service networks (`svc-*`).** They hold only one service and whoever may use it, with no internet access. `svc-llm` (10.10.250.0/24) connects LiteLLM to its consumers. Open WebUI and the agents can use LiteLLM, but can't reach Ollama or anything else in `ai`.
- **Agent workers.** They join `zone-agents`, `zone-lab` and `zone-apps`, and reach those services by name. The agent orchestrator stays only in `zone-agents` + `svc-llm`, so nothing under test in `lab` can talk to the thing that runs commands.
- **No agent** joins `zone-core` or `zone-prod-*`.

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
