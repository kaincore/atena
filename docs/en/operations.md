# Operations

## Add a stack

1. Create the folder in the right zone: `/opt/atena/stacks/<zone>/<name>/`. The name must be unique across all zones.
2. Write the `compose.yaml` following the [rules](architecture.md#rules-for-every-stack).
3. The stack shows up in Dockge on its own. Start it there or with `docker compose up -d`.
4. To reach it from away:
   ```bash
   sudo tailscale serve --bg --https=<port> http://127.0.0.1:<port>
   sudo ufw allow in on tailscale0 to any port <port> proto tcp comment '<name> via Tailscale Serve'
   ```
   tailscaled listens on that port through the kernel, so without the ufw rule other devices are blocked. **Test from another device**: a test run on the server itself passes even without the rule.

## Add a client to the prod zone

Each client gets its own network, so clients can't see each other:

```bash
sudo docker network create --subnet 10.10.101.0/24 \
  -o com.docker.network.bridge.name=br-prod-<name> \
  -o com.docker.network.bridge.host_binding_ipv4=127.0.0.1 \
  --label atena.zone=prod zone-prod-<name>
sudo install -d -m 700 -o <admin> -g <admin> /opt/atena/stacks/prod/<name> /srv/prod/<name>
```

Use the next free range (10.10.102.0/24, 10.10.103.0/24...). Interface names have at most 15 characters.

**Before putting a client online:** a UPS installed and a tested backup, with a completed restore.

## Add a container firewall exception

Edit the "exceções" (exceptions) section of `/usr/local/sbin/atena-docker-firewall` (for example, so a container can monitor a printer on the home network) and apply it:

```bash
sudo systemctl restart atena-docker-firewall
```

## LiteLLM

- **Anthropic key:** `atena-chave-anthropic`. The key isn't shown on screen, is checked against Anthropic at no cost, and only then saved.
- **One key per consumer:** create a virtual key for each consumer (Open WebUI, agents...), each with its own cap:
  ```bash
  curl -s http://127.0.0.1:4000/key/generate \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' \
    -d '{"key_alias":"open-webui","models":["local","haiku"],"max_budget":10,"budget_duration":"1mo"}'
  ```
- **Per-model caps:** `max_budget` in `config.yaml`. A model's `id` can't equal its `model_name` (see the [lessons](lessons.md)).
- **Monthly reset:** key caps (`1mo`) reset on their own on the 1st at 00:00 UTC. Per-model caps are reset at the same time by `atena-litellm-virada-mes.timer`. If the server was off, the reset runs at boot, waits for Redis and LiteLLM and retries every 5 min (up to 5 times); the final failure notifies your phone.
- **After editing `config.yaml`:** `docker compose up -d --force-recreate litellm`.

## Phone notifications (ntfy)

1. Install the **ntfy** app on your phone (Android).
2. Create your read-only user: `sudo atena-ntfy-celular <your-name>`.
3. In the app, add the server from `ATENA_NTFY_URL` with that user and subscribe to the topics `alertas`, `aprovacoes` and `atena`, in lowercase and without accents.
4. Test: `sudo atena-avisar "Test" "Did it arrive?"`.

To get notifications away from home, publish ntfy through Tailscale (as in [Add a stack](#add-a-stack), port 2586) and change the address:

1. In `/etc/atena/atena.conf`, `ATENA_NTFY_URL=https://<server>.<your-tailnet>.ts.net:2586`. The executor reads the file on every request.
2. In `/opt/atena/stacks/core/ntfy/server.yml`, the same address in `base-url`, then `docker compose up -d --force-recreate` in the ntfy folder.
3. In the app, switch the server to the new address.

## Containers after a boot

After an unclean shutdown, Docker can bring a container back without one of its networks, with no error at all. `atena-reconciliar` checks each container's networks and ports against its stack's compose: 3 min after boot, it recreates once whatever came back wrong and notifies you; after that, every 5 min, it only notifies, once per problem. It never starts what you stopped and never creates what is missing.

- See the differences without touching anything: `sudo atena-reconciliar --so-ver`.
- Its notices and the watchdog's (a container stopped with an error, or unhealthy) arrive on the `alertas` topic.
- Docker only starts with `/srv` mounted: if the data disk doesn't mount, the services stay stopped instead of starting empty on the system disk.

## Executor: clients and tokens

```bash
sudo atena-executor tokens                                    # who may request what
sudo atena-executor token-novo <client> <actions> <zones> [approve]
sudo atena-executor token-remover <client>
journalctl -u atena-executor -f                               # every request, with its result
```

- Lists are comma-separated. `approve` says which actions need the phone: `nenhuma` (none), or a list. Without that field, every action that can ask for approval does.
- The token is shown only once. Creating it again for the same client revokes the old one.
- Example: Atena starts asking your phone before restarting anything (her token lives in `/srv/agents/hermes/executor.token`):
  ```bash
  sudo atena-executor tokens | grep hermes      # copy her list of actions and zones
  sudo atena-executor token-novo hermes <actions> <zones> servico.reiniciar \
    | sudo tee /srv/agents/hermes/executor.token >/dev/null   # the file stays hermes-owned, mode 600
  ```

## Atena (Hermes)

**Install.** `sudo ./install.sh --hermes`. Then:

1. Start LiteLLM (stack `ai/litellm`) and save the Anthropic key with `atena-chave-anthropic`. To understand voice messages, also start Whisper (`ai/whisper`).
2. `sudo atena-hermes-chave [cap]`: creates Atena's LiteLLM key with a monthly cap in dollars (default 10) and saves it in Hermes without showing it.
3. Create a bot with **@BotFather** on Telegram and run `sudo atena-telegram`. The script asks for the token without echoing it, waits for you to send "hi" to the bot and confirms your ID. Only you can talk to her.
4. For private text (`local.processar`), pull the server model: `docker exec ollama ollama pull qwen3:4b-instruct-2507-q4_K_M` (or the one in `ATENA_LOCAL_MODELO`).
5. Voice (optional, needs a GPU): set `ATENA_VOZ=sim` in `atena.conf` and run the installer again. Start the `ai/voz` stack, download the model once with `curl -X POST http://127.0.0.1:8003/v1/models/speaches-ai/Kokoro-82M-v1.0-ONNX` and send `/voice` on Telegram (`on`: voice replies when you send voice; `tts`: always; `off`: turns it off). The default voice is `pf_dora`; other Portuguese voices: `pm_alex` and `pm_santa` (`docker exec -u hermes hermes hermes config set tts.openai.voice pm_alex`).

**Day to day.**

- `/new` on Telegram starts a new conversation (use it after changing the personality or the skills).
- Terminal: `docker exec -it -u hermes hermes hermes`.
- Personality and skills: `/srv/agents/hermes/SOUL.md` and `/srv/agents/hermes/skills/atena/`. The installer keeps a copy before overwriting a file you changed.
- Configuration: `docker exec -u hermes hermes hermes config set <key> <value>`. To go back to the template defaults: `sudo sh hermes/configurar.sh` and `docker restart hermes`.
- Scheduled tasks: `docker exec -u hermes hermes hermes cron list`. If the patrol is gone, run the installer again (with the same options): it creates the patrol and, on updates, keeps its text and skills identical to the template's (with the lab, `servidor-atena` and `lab`). By hand:
  ```bash
  docker exec -u hermes hermes hermes cron create "every 3m" "Ronda do servidor. Siga a seção Ronda das habilidades servidor-atena e lab." \
    --name ronda --monitor-script ronda.py --skill servidor-atena --skill lab --deliver telegram --failure-deliver ntfy
  ```
  (without the lab, drop `--skill lab`). When the AI doesn't answer, the round's failure arrives through ntfy, not through Atena's silent Telegram.
- Good morning: at 8 a.m., with no AI, `bom_dia.py` sends to Telegram how the server woke up (containers, temperatures, the month's spending and Claude Code's night). It arrives even with the AI down. To change the time: `docker exec -u hermes hermes hermes cron edit <id> --schedule "30 7 * * *"`.
- The executor by hand, the way she calls it: `docker exec -u hermes hermes python3 /opt/data/scripts/acao.py status.servicos` (the first line is the HTTP code).
- Memory: `/srv/agents/hermes/memories` (USER.md and MEMORY.md) is hers; the installer only puts the seed from `hermes/memoria` there when none exists. To check whether she kept something that no longer holds: `python3 tests/hermes/teste_memoria.py <folder with a copy of the memory>`.
- Spending: ask her ("how much did we spend this month?").
- Upgrading Hermes: read the release notes, change the image in the compose file and check the generated `config.yaml`. The docs on GitHub describe the development version, which may be newer than yours.

## Lab (Claude Code)

**Install.** Put your Claude Code accounts in `ATENA_CLAUDE_CONTAS` (just names, e.g. `pessoal trabalho`; with only one, Atena doesn't even ask) and run `sudo ./install.sh --hermes --lab` (or `--lab`, if Atena is already installed). Then, for each account:

```bash
sudo atena-claude-conta entrar pessoal    # shows a link: sign in to the account and paste the code
sudo atena-claude-conta estado            # which accounts are ready
```

**Day to day**, ask Atena: "make a shopping list app", "publish shopping-list", "change the button color". She asks for the account (if there's more than one), the model and the effort, sends the job and stops. Your phone gets the start notice (with Cancel), the permission requests and the questions; Atena sends the summary when it's done.

- Projects live in `/srv/lab/projetos/<project>`, each with git (commits are how you undo). To edit them as your user, log out and back in to SSH after installing (`atena-lab` group).
- Your own Claude Code in the lab: `cd /srv/lab && claude`. The sandbox in `/srv/lab/.claude/settings.json` applies, plus the scope guard.
- Published apps: `http://<server-ip>:<port>` (8000-8999) and, with Tailscale, `https://<server>.<tailnet>.ts.net:<port>`. They show up as `lab-<project>` stacks in Dockge.
- Usage limit: the job stops and Atena asks whether to continue later or on another account. For automatic switching, set `ATENA_CLAUDE_TROCA=sim` in `/etc/atena/atena.conf`.
- Power cut in the middle of a job: when the server comes back, the runner starts on its own and closes the job as interrupted (it can be continued). If not even the runner starts, the executor closes it at the deadline (the job's minutes plus 15 min) and frees the project.
- Skills: with `ATENA_CLAUDE_SKILLS=sim` in `atena.conf` and the installer run again, each account's login also installs the plugins and Impeccable. To check or redo it: `sudo atena-claude-conta skills` (with `nao`, the same command removes them).
- Trash: `app.apagar` with `codigo` moves the folder to `/srv/lab/lixeira`; `atena-lab-lixeira.timer` deletes it for good after 30 days.
- Changing the Claude Code version: `ATENA_CLAUDE_VERSAO` in `atena.conf` and run the installer again (it downloads and checks the official checksum). Read the release notes first.
- Logs: `journalctl -u atena-claude` (the runner) and each job's full conversation in `/var/lib/atena-claude/registros`.

## Panel

**Install.** It needs Tailscale logged in on the server and HTTPS enabled on the tailnet (in the Tailscale admin: DNS → HTTPS Certificates). Run `sudo ./install.sh --painel`, then:

```bash
sudo atena-painel-senha    # the login password (in a terminal; it isn't shown)
```

The installer prints the address: `https://<server>.<tailnet>.ts.net:3100`. On the phone, with Tailscale on, open it in Chrome and use the ⋮ menu → **Install app**.

- **On the home network, without Tailscale:** set `ATENA_PAINEL_CASA=sim` in `atena.conf` and run `sudo ./install.sh --painel` again. The panel then also opens at `http://<ATENA_LAN_IP>:3100`, over plain HTTP: the password crosses the Wi-Fi in the clear, and there it can't be installed as an app. To remove it, set it back to `nao` and run the installer again (the `atena-painel-casa` units and the ufw rule are removed).
- **Change the password:** run `sudo atena-painel-senha` again. Every device is signed out.
- **Connected devices:** in the Ajustes (settings) tab, with the Desconectar button.
- **Logs:** `docker logs painel` (the panel and the scheduler) and `journalctl -u atena-executor` (each of its requests, with the `painel` client and the `agendamento` origin for scheduled ones).
- **Schedules:** they live in the panel database (`/srv/core/painel/painel.db`). With the panel stopped, nothing runs; when it comes back, it runs what's late up to each one's tolerance and marks the rest as missed.
- **Take it down:**
  ```bash
  sudo tailscale serve --https=3100 off
  sudo systemctl disable --now atena-painel-casa.socket 2>/dev/null   # if it was on the home network
  cd /opt/atena/stacks/core/painel && docker compose down
  sudo atena-executor token-remover painel
  ```
  The data stays in `/srv/core/painel` until you delete the folder.

## Temperatures and fans

`sistema.sensores` (and Atena, when you ask) reads the CPU, the NVMe and the GPU with no setup. Fans come from the motherboard chip, which usually needs a kernel module: find out which one with `sudo apt install lm-sensors && sudo sensors-detect`, put it in `ATENA_SENSORES_MODULO` (e.g. `nct6683`) and run the installer again. The patrol warns about the CPU above 85 °C, the GPU above 85 °C and the NVMe above 70 °C.

## Home PC

Optional: Atena wakes the PC over the network, uses its model for longer texts and shuts it down when you ask. The step-by-step guide (in Portuguese) is in [`host/windows/LEIAME.md`](../../host/windows/LEIAME.md).

## Upgrade versions

Images are pinned. To upgrade:

1. Read the release notes and the project's **security advisories** (GitHub, Security tab).
2. Prefer versions published at least two weeks ago, unless an important security fix calls for a newer one.
3. Change the version in the compose file and run `docker compose up -d`.
4. **Pascal GPUs (GTX 10xx):** after upgrading Ollama or Whisper, check the logs to confirm the GPU is still in use (`library=CUDA compute=6.1` in Ollama).

The NVIDIA driver updates with the system, always within the same series. **Don't use `apt-mark hold`** (see the [lessons](lessons.md)).

## Upgrade from 0.2 to 0.3

`git pull` and `sudo ./install.sh` (with `--hermes` if you use Atena). The installer updates the executor, the skill and the personality, and reissues Atena's token with the new actions, keeping the zones and the approval rule. Since existing stacks are never overwritten, three steps are yours:

1. **LiteLLM** (for voice): copy `stacks/ai/litellm/ganchos.py` to `/opt/atena/stacks/ai/litellm/`, add the `voz` model and the `callbacks: ganchos.voz` line from the template's `config.yaml` and the `ganchos.py` mount from its `compose.yaml`, then run `docker compose up -d --force-recreate` in that folder.
2. **Atena's key** (for voice): run `sudo atena-hermes-chave [cap]` again so the key includes the `voz` model.
3. **Ollama** (optional): `OLLAMA_KEEP_ALIVE: 2m` in its compose, if the GPU has to share room with Whisper and the voice.

Then send `/new` on Telegram.

## Compare the server with the repository

`sudo ./aplicar --conferir`, in the repository folder, compares the server with what the installer would put on it, without changing anything. The values come from `/etc/atena/atena.conf`, and the options (`--hermes`, `--lab`, `--painel`, `--ssh`) are worked out from what is already installed. For each part (`host`, `executor`, `stacks`, `painel`, `hermes` and `lab`), it lists:
- **difere (differs):** the server's file isn't the repository's, or its mode and owner aren't. "Só nos comentários" means only the comments differ;
- **falta (missing):** the repository puts the file there and the server doesn't have it;
- **sobra (left over):** the file is in a template folder and doesn't come from the repository, like a hand-made drop-in. The template folders are `/usr/local/sbin/atena-*`, the `atena*` units and their drop-ins, the executor and the panel's code;
- **old copies:** the `.antes-*` files that hand changes left behind (`--copias` lists them).

`--diff` shows what would change in each file, from the server to the repository, and `--parte executor,hermes` limits the check to those parts. Without `sudo`, what only root can read shows up as `?`. It exits with 0 when everything matches.

What belongs to the server is left out: the `.env` files, the data in `/srv`, the stacks that don't come from the repository and Atena's memory, which only has to exist. Before a hand change, run `--conferir`. Afterwards, it shows whether the change also has to go into the repository.

## Run the installer again

`sudo ./install.sh` can run as many times as you like:
- **Existing stacks** aren't overwritten. The panel is the exception: with `--painel`, its code always comes from the repository, and the previous compose is kept if it changed.
- **System files that differ from the template** are replaced, and a copy of the previous one is kept next to it (`*.antes-atena-<date>`).
