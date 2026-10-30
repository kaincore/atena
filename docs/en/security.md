# Security

## Principles

- **The home network is trusted; nothing else is.** Any home device reaches the services. From away, only through Tailscale. From the internet, nothing.
- **Containers can't reach the home network.** If a container is compromised, it can't get to the router, your computers or your Tailscale devices. The one optional exception is the home PC (`ATENA_PC_IP`): LiteLLM reaches it, and only on LM Studio's port.
- **Isolated zones.** A problem in one zone doesn't reach the others.
- **Secrets stay out of the code.** They live in `.env` files with mode 600, generated on the server and never committed.
- **Agents act only through a closed list.** Atena has no Docker and no sudo: everything she does on the server goes through the executor, which only knows fixed actions.

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

### Executor
- **No shell.** Each action runs a fixed command; parameters are checked against what exists (stack, unit, path) and against a list of formats.
- **One token per client**, stored only as a hash, with the actions and zones it may request. Revoking takes effect immediately.
- **Approval on your phone.** Each request's code exists only inside the notification, on an ntfy topic only you read. A request is valid for 10 minutes, each client can have at most 5 waiting, and the zone is checked again right before running.
- **Locked-down service.** Runs as `atena-exec`, with `ProtectSystem=strict`, `NoNewPrivileges` and a single capability: `CAP_DAC_READ_SEARCH`, which reads files and can't write.
- **Secrets don't leave.** `/proc`, `/run`, `/var/lib/docker`, `/etc/atena/executor`, folders such as `.ssh` and files such as `.env`, `*.key` and `tokens.json` are refused, also through symlinks. In the text that goes out, password, token and key values become `***`.

### Atena (Hermes)
- **No Docker and no sudo.** The `hermes` user is only in the `atena-acoes` group, which grants access to the executor socket. The installer stops if `hermes` is in the `docker` group.
- **Token without the `prod` zone.** Client systems are out of her reach.
- **Only the owner talks to her.** Telegram accepts only your ID; messages from anyone else are ignored, with no reply.
- **Content is data, not orders.** `SOUL.md` tells her to treat web pages, documents and third-party messages as data. Commands in her container go through "smart" approval, and anything destructive goes to you.
- **Her rules are read-only.** `SOUL.md` and Atena's skills (`skills/atena`) are mounted read-only in the container. A text she reads can't rewrite them, and neither can Hermes's "learning". Only the installer or `./aplicar` changes them, from the repository. Changing the files' owner wasn't enough, because the folder is hers.
- **LiteLLM key with a monthly cap.** A mistake of hers can't drain your API credit.
- **Her API only opens to the executor.** The panel chats with her and sees her schedule through the Hermes API, which only listens on the `svc-atena` network, where there's no other container. From the server, reaching it takes the key (`API_SERVER_KEY`, in her `.env`), which only the executor reads: the panel asks the executor, and the key never reaches it. In the panel, Telegram and schedule conversations are read-only.

### Lab (Claude Code)
- **No sudo and no Docker.** `atena-claude` is only in the `atena-fila` and `atena-lab` groups. The installer stops if it's in the `docker` group.
- **Mandatory sandbox, with no way out.** Writes only to the project folder; Docker, the executor, D-Bus, systemd, the other zones and the accounts' credentials are hidden; internet only for package registries. If the sandbox doesn't start, Claude Code doesn't run.
- **The project doesn't configure Claude Code or git.** Only the account settings and `lab.json` count; project hooks are off; the runner's git ignores fsmonitor and hooks, and a `.git/config` that runs commands makes the job get refused.
- **What leaves the server goes through your phone.** `git push`, web pages and edits outside the folder become permission requests; without an answer, they're denied.
- **Locked-down lab apps.** Read-only disk, no capabilities, `no-new-privileges`, 512 MB, only the `zone-lab` network. Publishing and deleting need your phone by default.
- **Tailscale only through polkit.** The executor can only start the `atena-lab-tailscale-on@` and `-off@` units, on ports 8000-8999.
- **Style recipes:**
  - **What opens the site doesn't think, and what thinks doesn't open the site.** The collector is a Chromium with no AI, in a one-off container, read only, with no capabilities and 1 GB, on the `lab-coletor` network (no traffic between containers): it reaches the internet, but the container firewall blocks the home network, Tailscale and the server. Before that, the executor checks the address: only `http(s)`, no username or password, and every IP of the name on the internet. Claude Code reads the capture with no network to the site, and the `receita` skill treats everything that came from it as data, not as orders.
  - **REA goes through the command line, inside the sandbox.** Not as an MCP server: Claude Code's MCP servers run outside the Bash sandbox, with the network and disk of the `atena-claude` user. From the command line, it is under the same walls as everything else (writes only to the project, internet only for packages).
  - **The studied program never runs.** The file only comes from the delivery folders (Atena's space, the lab projects, the documents), goes through the secrets filter and refuses databases, up to 1 GB, and is copied into the study project. Claude Code reads it inside the sandbox, with no network, using REA and the decompilers (Ghidra, JADX, Apktool), which read without executing; the skill forbids running the program and treats what comes from it as data. The screenshots you send (`imagens`) go through the same folders and only get in if they're a real JPEG or PNG.
  - **The decompilers come checked.** Ghidra is downloaded from the NSA's GitHub and checked against the SHA-256 on its release page; the JADX bridge, against the SHA-256 REA itself pins; JDK 21 and Apktool come from Ubuntu. They live in `/usr/local/lib/atena-claude`, owned by root and read only for the worker. The paid ones (IDA, Hopper, JEB) don't get in.
  - **The executor copies the recipe without following links.** The study folder belongs to Claude Code, which read the internet: every file is opened without following a symbolic link anywhere in the path, with a size cap (200 KB for text, 64 KB for `receita.json`, 3 MB per screenshot), and only a real JPEG becomes a screenshot. A link there can't make the executor read something else.
  - **Deleting is destructive:** `receita.apagar` asks your phone (in the panel, the on-screen confirmation).

### Panel
- **No network, no root, no Docker.** `network_mode: none`, read-only disk, no capabilities, `no-new-privileges`, 256 MB. The `atena-painel` user is only in the `atena-acoes` group; the installer stops if it's in the `docker` group.
- **Entry through Tailscale**, through a socket only root and the panel can open (`/srv/core/painel` is 700). The home-network one (`ATENA_PAINEL_CASA=sim`) is a second socket next to it, opened by the systemd forwarder, which runs as `atena-painel` with no network of its own and no capabilities.
- **A password that's hard to brute-force:** scrypt (N=2^15, 32 MB per attempt), 5 mistakes in 15 minutes lock the entry they came through (Tailscale or the home network: someone guessing on the Wi-Fi can't lock the owner out from away), and one check at a time.
- **Cookie** HttpOnly, Secure (through Tailscale) and SameSite=Strict. Every POST requires JSON and a custom header, which blocks forms from other sites (CSRF).
- **CSP** that only allows the panel itself, no frames. Screens are built without `innerHTML`, so a container name or a log line never becomes code.
- **Own token, no phone approval:** 54 actions, 10 of them to chat with Atena, read her conversations and the Claude Code ones, and manage her schedule, and 6 for the style recipes. The ones that delete are `app.apagar` and `receita.apagar`, lab only: the code goes to the trash for 30 days, deleting the data requires typing the app's name, and deleting a recipe asks for the on-screen confirmation. It edits only the apps zone stacks, always with a snapshot first, and reads the server except secrets, like Atena. Whoever has the panel password has this reach: one more reason for a password used only there.
- **Schedule:** the scheduler only runs actions on the schedulable list (PC, restart a service, lab apps), and a run past its tolerance doesn't run later.
- **Deciding in the panel counts as the tap on the phone.** Only the panel token has `aprovacoes.decidir`; it never decides its own requests (except Claude Code's permissions and questions in jobs it started), and it only sees requests from clients within its zones (no `prod`). Whoever has the panel password can approve what Atena asks for: one more reason for a password used nowhere else.

## What was tested on the original server

| Test | Result |
|---|---|
| A container in `agents` trying the router, the home network, Tailscale and the server's SSH | Blocked |
| The same container trying the internet and DNS | Allowed |
| A simulated machine outside the home network (network namespace) trying a container published on `0.0.0.0` | Blocked. With the rule removed it got through, which proves the test catches the failure |
| One zone trying to reach another | Isolated |
| The same tests after restarting Docker and the server | Same results |
| SSH login with a password, and as root | Refused |
| Atena asking the executor for `/etc/shadow`, a `.env` file and an SSH key | Refused (403) |
| Approval with a wrong code, a repeated tap and an expired request | Nothing ran |
| A client asking for an action outside its token, or a stack in another zone | Refused (403) |
| The lab's Claude Code writing outside the project folder and using `sudo` and the Docker socket | Blocked by the sandbox |
| A project with `core.fsmonitor` in `.git/config` | Job refused, without starting Claude Code |
| Panel: an action outside its list, a POST without the custom header, a form from another site | Refused (403, 415), never reaching the executor |
| Panel: wrong password 5 times, then the right one | Locked for 15 min |
| Panel: `docker inspect` of the container, and port 3100 from the home network | No network, no Docker socket; nothing answers on the home network (with `ATENA_PAINEL_CASA=nao`, the default) |

The automated tests for the executor, the patrol and the lab live in `tests/`, the panel's in `stacks/core/painel/app/test/`, and all of them run on every push to GitHub.

## What Atena does NOT protect

- **The admin and Dockge have full access.** Dockge and the Beszel agent use the Docker socket, which is equivalent to root. Whoever gets into Dockge controls the server. Use a strong password.
- **Services without a password are open to the whole home network.** Lab apps, for example, have no login: any device on the Wi-Fi can open them.
- **Zones share the same kernel.** A serious container-escape bug would cross zones. For strong isolation, use virtual machines.
- **IPv6 inside containers** isn't used. If you enable IPv6 on Docker networks, review the firewall, which today only has IPv4 rules.
- **Whoever has the panel password** can restart services and shut down the PC, without going through the phone. Use a password you don't use anywhere else.
- **The executor has Docker access.** That is equivalent to root. The protection is the closed list: a bug in the executor would be a security bug for the whole server.
- **The secret filter works by name and by format.** A secret in an unknown format, inside a file with an ordinary name, can get through. Keep secrets in `.env`, `*.key` or `*.token` files.
- **What Atena reads goes to the cloud model** (Anthropic), except what goes through `local.processar`.
- **The panel on the home network (`ATENA_PAINEL_CASA=sim`) is HTTP.** Someone sniffing the Wi-Fi can read the password and the session cookie, and with the cookie they get in as you until the session expires. The cookie is also sent to the other services on the same IP (Dockge, Beszel, ntfy), because cookies don't separate ports. Prefer Tailscale, and change the password (`sudo atena-painel-senha`, which ends every session) if you suspect someone on the network.
- **ntfy without HTTPS on the home network.** With `http://`, someone sniffing the Wi-Fi could see a request's code and approve it before you. Away from home, use the Tailscale `https://` address in `ATENA_NTFY_URL`.
- **Prompt injection** (text that tries to command the AI) is reduced by the rules and the approvals, not eliminated. That's why Atena only acts without approval on what can be undone.
- **The lab's Claude Code downloads packages from the internet** (npm, PyPI, GitHub). A malicious package runs inside the sandbox, only in the project folder, but it can end up in a published app. Look at what it installed before publishing anything important.
- **Claude Code runs on your subscription.** What it reads in the project goes to Anthropic, like in a chat.
- **A recipe describes someone else's site.** It notes the choices (colors, sizes, techniques) and is written not to copy code, logos, images, text or paid fonts, but you decide what goes into a published project. Studying third-party software (not a site) may be forbidden by its license: only do it with what you have the right to analyze.
- **Other forwarded traffic** (virtual machines, a Tailscale subnet router) is dropped by the last rule of `DOCKER-USER`. If you need it, add exceptions.

## Before publishing anything

The repository has a commit guard (`tools/hooks/pre-commit`) and a GitHub check (gitleaks). Keep your list of personal data in `~/.config/atena/padroes-privados.txt`, **outside** the repository.
