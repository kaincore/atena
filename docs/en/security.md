# Security

## Principles

- **The home network is trusted; nothing else is.** Any home device reaches the services. From away, only through Tailscale. From the internet, nothing.
- **Containers can't reach the home network.** If a container is compromised, it can't get to the router, your computers or your Tailscale devices.
- **Isolated zones.** A problem in one zone doesn't reach the others.
- **Secrets stay out of the code.** They live in `.env` files with mode 600, generated on the server and never committed.

## The layers

### The server (ufw)
- Inbound blocked by default.
- SSH only from the home network and over the Tailscale interface.
- With `--ssh`: key-only login, no root, admin user only.

### Containers (atena-docker-firewall)
ufw **does not protect Docker's ports**: Docker writes its own rules. So Atena uses the `DOCKER-USER` chain, which Docker checks before its own rules.

**Outbound (`ATENA-EGRESS` chain):**
- Allows replies, container-to-container traffic (Docker already isolates networks) and the router's DNS.
- Blocks the Tailscale interface and the private ranges: `192.168.0.0/16`, `172.16.0.0/12`, `10.0.0.0/8`, `100.64.0.0/10` and `169.254.0.0/16`.
- When applied, it drops connections that containers had already opened to the home network and to Tailscale. A new rule doesn't cut connections that are already established.

**Inbound:** only replies, plus new connections from the home network to the server's IP. Everything else is dropped, even if a port was published on `0.0.0.0` by mistake.

The rules load **before Docker** (`Before=docker.service`), so no container ever runs without them.

### Published ports
Three layers keep a port from leaking by mistake:
1. Compose files always write the IP on every port.
2. Zone networks use `host_binding_ipv4=127.0.0.1`: a port published without an IP stays on the server.
3. The inbound firewall drops the rest.

## What was tested on the original server

| Test | Result |
|---|---|
| A container in `agents` trying the router, the home network, Tailscale and the server's SSH | Blocked |
| The same container trying the internet and DNS | Allowed |
| A simulated machine outside the home network (network namespace) trying a container published on `0.0.0.0` | Blocked. With the rule removed it got through, which proves the test catches the failure |
| One zone trying to reach another | Isolated |
| The same tests after restarting Docker and the server | Same results |
| SSH login with a password, and as root | Refused |

## What Atena does NOT protect

- **The admin and Dockge have full access.** Dockge and the Beszel agent use the Docker socket, which is equivalent to root. Whoever gets into Dockge controls the server. Use a strong password.
- **Services without a password are open to the whole home network.** Arca, for example, has no login: any device on the Wi-Fi can see and delete files.
- **Zones share the same kernel.** A serious container-escape bug would cross zones. For strong isolation, use virtual machines.
- **IPv6 inside containers** isn't used. If you enable IPv6 on Docker networks, review the firewall, which today only has IPv4 rules.
- **Other forwarded traffic** (virtual machines, a Tailscale subnet router) is dropped by the last rule of `DOCKER-USER`. If you need it, add exceptions.

## Before publishing anything

The repository has a commit guard (`tools/hooks/pre-commit`) and a GitHub check (gitleaks). Keep your list of personal data in `~/.config/atena/padroes-privados.txt`, **outside** the repository.
