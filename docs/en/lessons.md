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

**For the voice (Kokoro, ONNX) it's the opposite: use the full version (fp32).**
The int8 one falls back to the CPU on Pascal cards and gets about 5 times slower.

**The voice's GPU memory grows with the text.**
Numbers and percentages turn into many phonemes: 837 characters went past 3.4 GB and hung the request on a 6 GB card, and 300 characters reached 4.2 GB. In chunks of 150 characters the voice stays at ~2.2 GB. That's why Hermes speaks in chunks (`tts.openai.max_text_length 150`) and LiteLLM gives up after 10 s, without retrying.

**Three models don't fit together in 6 GB.**
Ollama (3.2 GB), Whisper (1.1 GB) and the voice (2.2 GB) go over the limit. Each one leaves the GPU on its own after sitting idle: the voice after 60 s, Ollama after 2 min and Whisper after 10 min (fast listening matters more).

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

**`docker compose config` merges `env_file` into `environment`, and the path disappears.**
To check where variables come from (and block an `.env` from another stack), read the compose a second time with `--no-interpolate`: it's the only way that shows the path on every version. `--no-env-resolution` only works on Compose v5; on 2.x the path disappears even with it, and the rule let another stack's `.env` through. GitHub's CI, which runs a Compose 2.x, caught it.

## Executor, ntfy and Hermes

**Mount the socket's folder, not the socket file.**
The executor socket is recreated on every restart. With the file mounted, the Hermes container kept looking at the old socket. Mount the `/run/atena-executor` folder and set `RuntimeDirectoryPreserve=yes` on the unit, or systemd recreates the folder and the container loses the path.

**Hermes needs `command: ["gateway", "run"]`.**
Without it, the container opens the interactive chat, exits and restarts forever.

**The Hermes docs on GitHub describe the development version.**
Some keys didn't exist yet in the installed version. Check the `config.yaml` it generates, and configure it with `hermes config set`, which validates every key.

**ntfy: lowercase topics, and the phone must subscribe to all of them.**
Phone keyboards capitalize on their own (`Aprovacoes` is a different topic). And whoever subscribes only to `atena` never sees the approval requests, which go to `aprovacoes`.

**The approval button calls the address the phone can reach.**
The executor publishes to ntfy over `127.0.0.1`, but the button travels to the phone: it needs the home network or Tailscale address (`ATENA_NTFY_URL`).

**An accepted action is not a finished action.**
Atena used to say "restarted" while the request was still waiting for the phone. `SOUL.md` now tells her to check the result before stating it, and the executor answers 202 while the request waits.

**Private text doesn't go through LiteLLM.**
LiteLLM can fall back to a cloud model when the home model doesn't answer. `local.processar` talks straight to Ollama or LM Studio.

**The "thinking" qwen3 4B writes its reasoning before the answer and burns the output limit.**
Use the instruct version (`qwen3:4b-instruct-2507`) and send `/no_think`.

**On Ubuntu 26.04, `install` can't copy from `/dev/stdin` over a file that already exists.**
`install` is now uutils (coreutils in Rust) and only says "No such file or directory". A new file works, which is why Atena's first token was saved and the swap during an upgrade failed, leaving an already-revoked token in the file. Write to a new file and move it, or use `tee` on a file that already exists. Found in the 0.3 VM test.

**After shutting down, the PC still looks "on" in the neighbor table for a few minutes.**
The executor treats "no route to host" over SSH as "off" instead of an error.

**Look for the PEM block header, not just "PRIVATE KEY".**
Refusing any text containing "PRIVATE KEY-----" blocked files that merely mention it, such as the executor itself. What identifies a key is `-----BEGIN ... PRIVATE KEY-----`.

**The executor writes in place, without replacing the file.**
A stack may mount a single file, and the app may rewrite its own files while it runs. Writing a new file and renaming it would change the owner and the inode; `stack.editar` writes to the same file.

**Speaches doesn't produce opus.**
Hermes asks for the voice in opus (Telegram's voice message format) and Speaches answers 422. A LiteLLM hook switches the request to mp3, and Hermes converts it back with ffmpeg. Hermes sends the voice before the text, so the text waits for the speech to be ready.

## Lab (Claude Code)

**On Ubuntu 26.04, Claude Code's sandbox needs `allowAllUnixSockets`.**
AppArmor drops the capabilities of everything running inside bubblewrap, and Claude Code's seccomp helper (which blocks local sockets) aborts. Every command failed in the sandbox, was retried outside it and became a permission request. Without the helper, the dangerous sockets (Docker, executor, D-Bus, systemd) are hidden with `denyRead`.

**A test server left running in the background keeps `claude -p` open.**
The final summary was already out, but the process didn't exit, and the job would only end at the time limit, as an error. The runner closes Claude Code 30 s after the final summary, and the rules say nothing may stay running in the background.

**After switching accounts, read only the new round of the log.**
The previous account's "limit reached" notice was still in the log; if the new round didn't send a fresh one, the job stopped for nothing.

**If anyone besides Claude Code writes to the projects, the project can't configure anything that runs outside the sandbox.**
`--setting-sources user` (no project hooks and no `apiKeyHelper`) and git with `core.fsmonitor=false` and `core.hooksPath=/dev/null` in the environment. A `.git/config` with an fsmonitor would run a program from the project in the runner itself.

**Moving to the trash is a rename.** With separate `ReadWritePaths` for the projects and the trash, systemd mounts them apart and the rename fails (`EXDEV`). A single `ReadWritePaths=/srv/lab` fixes it.

**On Ubuntu 26.04, `/usr/bin/test` (uutils) ignores ACLs.**
`sudo -u atena-claude test -w file` said a file granted through an ACL wasn't writable, and it was. Bash's built-in `test` and Python's `os.access` get it right. Found in the 0.4 VM test.

**To continue a conversation on another account, copy the session.** `--resume` looks for the conversation in the account's folder (`projects/*/<session>.jsonl`); the runner copies the file, and the subagents folder, before continuing.

**Claude Code's MCP servers run outside the sandbox.** The sandbox covers Bash; an MCP server is a process of Claude Code itself, with the user's network and disk. That's why the recipes' REA comes in through the command line (`rea ...` in Bash), under the same walls as everything else, and not as an MCP server.

**REA gives up on a site's whole scripts folder.** `analyze-javascript-application` on a site's 393 scripts hit the 5-minute per-source limit and stopped with no result. With up to 5 scripts at a time it takes seconds, and the network log (`inspect-web-network-capture` on the HAR) takes 3 s. The `receita` skill says to pick the scripts first.

**REA needs a newer Node than Ubuntu's.** `rea-agents` 6.8.0 wants 22.23.4+ or 24.22.1+, and Ubuntu 26.04 ships 22.22.1. The lab got its own Node (pinned, from nodejs.org, checked against the checksum) at the front of the worker's PATH, without touching the system one.

## Panel

**`tailscale serve` can deliver to a Unix socket** (`unix:/path/to.sock`). That leaves the panel container with no network at all (`network_mode: none`) and still with HTTPS from away. ufw still has to allow the port on `tailscale0`.

**Ubuntu 26.04's Node doesn't run TypeScript directly.** Since 22.18, official Node runs `.ts` without compiling and ships `node:sqlite`, which left the panel without a single npm package. Ubuntu's `nodejs` package (22.22) answers `ERR_UNKNOWN_FILE_EXTENSION`: use the official Node image.

**On Node 22, `node --test folder/` doesn't work.** It tries to open the folder as a file. Pass the pattern: `node --test 'test/*.test.ts'`.

**The `hidden` attribute loses to a class's `display`.** The login screen showed up below the panel, because `.entrada { display: grid }` beat `hidden`. `[hidden] { display: none !important; }` fixes it.

**A CSP without `'unsafe-inline'` blocks the `style` attribute.** Bar widths have to go through `element.style.width`, which the CSP allows.

**A `grep` with no match in a pipeline with `pipefail` ends the script silently.** The leak checker blocked every commit when a server `.env` only had short values. `{ grep ... || true; }` fixes it.

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
