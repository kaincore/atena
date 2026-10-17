# Lessons learned

Pitfalls found while building the first Atena server. Each one cost a failed test, or worse, a test that passed without proving anything.

## Network and firewall

**`"ip": "127.0.0.1"` in `daemon.json` only applies to Docker's default network.**
The first test used the default network and passed. But the zone networks published on `0.0.0.0`, and a service was visible on the home network for a few minutes. The fix uses three layers: an explicit IP in compose files, `host_binding_ipv4=127.0.0.1` on the networks, and an inbound firewall.

**ufw doesn't protect Docker's ports.**
Docker writes its own NAT and forwarding rules, which bypass ufw. Use the `DOCKER-USER` chain.

**A new rule doesn't cut an open connection.**
A ping to the router kept getting through after the block, because the connection was already tracked (conntrack) and every test kept it alive. The firewall now runs `conntrack -D` when applied, and loads before Docker.

**A test run from the server itself is misleading.**
Traffic the server generates doesn't go through the same rules as traffic from another machine. To test inbound traffic, simulate another machine with a network namespace (`ip netns`) or test from another device.

**`tailscale serve` listens through the kernel.**
Without a ufw rule for the `tailscale0` interface, other devices are blocked. From the server itself, though, the test passes.

## GPU (Pascal cards such as the GTX 1060)

**CUDA 13 doesn't support Pascal.**
Recent Ollama skips the CUDA 13 libraries for this card and falls back to CUDA 12. Use CUDA 12-based images, and after every upgrade check the logs to confirm the GPU is still in use.

**With Secure Boot, `apt-mark hold` on the driver breaks the GPU.**
The signed kernel modules follow the driver's version. Holding the driver separates the two on the next kernel update. The package is already per series (`-580`), and apt never switches series on its own.

**Pascal is slow at float16.**
In Whisper (faster-whisper/CTranslate2), use `int8`. The GTX 1060 supports DP4A, so int8 runs fast.

## LiteLLM and the Claude API

**Haiku, Sonnet and Opus 5.5 reject non-default `temperature`, `top_p` and `top_k`** (error 400). Many clients send them. Use `additional_drop_params` on each model.

**Per-model caps on keys (`model_max_budget`) are a paid LiteLLM feature.**
On the free version, use `max_budget` + `budget_duration` on each model. You also need **Redis**: without it, spend lives only in memory and resets on every restart.

**A model's `id` can't equal its `model_name`.**
If it does, LiteLLM treats the call as a "specific deployment" and **skips the cap**. The test showed spend above the limit and calls still going through.

**Per-model caps count from the first spend, not from the 1st of the month.**
A systemd timer resets the counters on the 1st. Key caps use `budget_duration: 1mo`, which already resets on the 1st.

**New models may be missing from LiteLLM's price map.**
Without a price, recorded cost is zero and the cap never blocks. Put the prices in `model_info`.

**Test caps with a cap smaller than a single call.**
On the first try, each call cost US$ 0.0000037 and the cap was US$ 0.00002: the test "passed" without proving anything.

## Docker and Compose

**`sed -i` replaces the file, and a single-file bind mount keeps seeing the old one.**
After editing a file mounted on its own (such as `config.yaml`), use `docker compose up -d --force-recreate`, not `restart`.

**Dockge doesn't read subfolders** (the project's request #687). The fix is a folder of symlinks maintained by a systemd `.path` unit.

**The first person to open Dockge, Beszel or Open WebUI becomes the admin.** Create the accounts right after starting them.

## Apps

**File uploads with Express (`express-fileupload`):**
- Without `defParamCharset: 'utf8'`, accented file names arrive garbled ("ação" becomes "aÃ§Ã£o").
- Without `abortOnLimit: true`, a file over the limit is **saved truncated** and the response says "success".
- A file name inserted into the HTML without escaping allows code injection.

## About tests

**A test must be able to fail.** Three times a test "passed" for the wrong reason:
- a test server with no pages returned 404, and that was counted as "blocked";
- `xargs -r` with no input returns success;
- the LiteLLM cap was larger than the test calls could ever spend.

Whenever you can, also run the same test **with the protection turned off** and confirm it catches the failure.
