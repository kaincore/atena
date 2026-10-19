#!/bin/sh
# Atena: aplica a configuração do Hermes (config.yaml e .env em /srv/agents/hermes) pelo próprio
# "hermes config set", que valida cada chave. Pode rodar de novo: o resultado é o mesmo.
# Uso: sudo sh hermes/configurar.sh   (o container hermes precisa estar no ar)
set -eu
C=${HERMES_CONTAINER:-hermes}
[ "$(id -u)" = 0 ] || { echo "Rode com sudo." >&2; exit 1; }
docker exec "$C" true 2>/dev/null || { echo "O container $C não está no ar." >&2; exit 1; }

cfg() {
  if ! docker exec -u hermes "$C" hermes config set "$1" "$2" >/dev/null; then
    echo "não consegui gravar $1 no Hermes" >&2
    exit 1
  fi
}

# Modelos: tudo pelo LiteLLM (chave própria, com teto). Haiku por padrão; local roda em casa.
cfg providers.atena '{"api": "http://litellm:4000/v1", "key_env": "ATENA_LITELLM_KEY", "transport": "openai_chat",
  "session_affinity_header": "x-litellm-session-id", "discover_models": false,
  "models": {"haiku": {"context_length": 100000, "supports_vision": true},
             "sonnet": {"context_length": 200000, "supports_vision": true},
             "opus": {"context_length": 200000, "supports_vision": true},
             "local": {"context_length": 8192}}}'
cfg model.provider atena
cfg model.default haiku

# Ferramentas: pesquisa na web, Python e subagentes ficam; navegador, controle do computador,
# imagens, voz sintetizada e conexões externas saem.
cfg agent.disabled_toolsets '["browser", "computer_use", "image_gen", "tts", "connections"]'
cfg delegation.max_concurrent_children 4
cfg security.allow_lazy_installs false

# Aprovação: um modelo auxiliar libera o que é seguro; o destrutivo sempre vai para o dono.
cfg approvals.mode smart
cfg approvals.timeout 300
cfg approvals.smart_policy "This agent runs unprivileged inside a container; its own data lives in /opt/data. \
The owner's rule: anything destructive needs the owner's explicit OK. \
ESCALATE (never APPROVE) any command that deletes, overwrites, truncates, empties or moves away files or \
directories; drops or alters databases; kills processes; rewrites git history; uploads, sends or publishes \
data to outside services; or changes permissions, credentials, keys or security settings. \
Prefer ESCALATE over DENY so the owner can decide. \
APPROVE read-only commands and clearly additive ones (creating new files, downloading into a new folder, \
installing into a virtualenv)."

# Mensagens de voz: transcritas pelo Whisper da casa, através do LiteLLM.
cfg stt.provider openai
cfg stt.language pt
cfg stt.openai.model whisper
cfg stt.openai.language pt
cfg STT_OPENAI_BASE_URL http://litellm:4000/v1
cfg STT_OPENAI_MODEL whisper
cfg HERMES_LOCAL_STT_LANGUAGE pt

# Quem não é o dono não conversa (nem recebe resposta).
cfg unauthorized_dm_behavior ignore
cfg telegram.unauthorized_dm_behavior ignore

# Agendamentos: o que a ronda entrega entra na conversa do Telegram (a Atena lembra depois).
cfg cron.mirror_delivery true

# Avisos da Atena no celular pelo ntfy (tópico atena). O token vem do instalador.
cfg NTFY_SERVER_URL http://ntfy:2586
cfg NTFY_TOPIC atena
cfg NTFY_PUBLISH_TOPIC atena
cfg NTFY_HOME_CHANNEL atena
cfg NTFY_HOME_CHANNEL_NAME Celular
cfg NTFY_MARKDOWN true

# Habilidades que vêm com o Hermes e não fazem sentido aqui (outros serviços, Apple, programação,
# que é trabalho para outro agente). Menos habilidades, menos texto em cada conversa.
cfg skills.disabled '["airtable", "apple-notes", "apple-reminders", "architecture-diagram", "ascii-video",
  "baoyu-infographic", "blocked-page-recovery", "box", "claude-code", "claude-design", "codebase-inspection",
  "codex", "competitor-news-monitor", "computer-use", "design-md", "document-to-action-items", "dogfood",
  "email-inbox-triage", "findmy", "gif-search", "github", "google-workspace", "hermes-agent",
  "hermes-agent-skill-authoring", "himalaya", "humanizer", "imessage", "inspecting-hermes-desktop-dom",
  "llm-wiki", "manim-video", "maps", "meeting-action-items", "node-inspect-debugger", "notion", "obsidian",
  "opencode", "p5js", "popular-web-designs", "powerpoint", "product-price-monitor", "python-debugpy",
  "requesting-code-review", "sdlc-review", "security-reviewer", "simplify-code", "songsee",
  "songwriting-and-ai-music", "spike", "teams-meeting-pipeline", "test-driven-development",
  "weekly-review-planning", "xurl", "youtube-content"]'

echo "Configuração do Hermes aplicada."
