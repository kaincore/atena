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

## Upgrade versions

Images are pinned. To upgrade:

1. Read the release notes and the project's **security advisories** (GitHub, Security tab).
2. Prefer versions published at least two weeks ago, unless an important security fix calls for a newer one.
3. Change the version in the compose file and run `docker compose up -d`.
4. **Pascal GPUs (GTX 10xx):** after upgrading Ollama or Whisper, check the logs to confirm the GPU is still in use (`library=CUDA compute=6.1` in Ollama).

The NVIDIA driver updates with the system, always within the same series. **Don't use `apt-mark hold`** (see the [lessons](lessons.md)).

## Run the installer again

`sudo ./install.sh` can run as many times as you like:
- **Existing stacks** aren't overwritten.
- **System files that differ from the template** are replaced, and a copy of the previous one is kept next to it (`*.antes-atena-<date>`).
