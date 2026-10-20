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
- **Monthly reset:** key caps (`1mo`) reset on their own on the 1st at 00:00 UTC. Per-model caps are reset at the same time by `atena-litellm-virada-mes.timer`.
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
    | sudo install -m 600 -o hermes -g hermes /dev/stdin /srv/agents/hermes/executor.token
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
- Scheduled tasks: `docker exec -u hermes hermes hermes cron list`. If the patrol is gone, create it again:
  ```bash
  docker exec -u hermes hermes hermes cron create "every 3m" "Ronda do servidor. Siga a seção Ronda da habilidade servidor-atena." \
    --name ronda --monitor-script ronda.py --skill servidor-atena --deliver telegram
  ```
- Spending: ask her ("how much did we spend this month?").
- Upgrading Hermes: read the release notes, change the image in the compose file and check the generated `config.yaml`. The docs on GitHub describe the development version, which may be newer than yours.

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

## Run the installer again

`sudo ./install.sh` can run as many times as you like:
- **Existing stacks** aren't overwritten.
- **System files that differ from the template** are replaced, and a copy of the previous one is kept next to it (`*.antes-atena-<date>`).
