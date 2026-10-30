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
# prompt_caching: o Hermes marca o cache da Anthropic ao longo da conversa (o começo do prompt e as
# últimas mensagens). Pelo nome do modelo ("haiku", sem "claude") ele não sabe que é Claude, e sem
# isto só o prompt de sistema entrava no cache (o ponto que o LiteLLM põe): o histórico e os
# resultados das ferramentas eram cobrados cheios a cada volta.
cfg providers.atena '{"api": "http://litellm:4000/v1", "key_env": "ATENA_LITELLM_KEY", "transport": "openai_chat",
  "session_affinity_header": "x-litellm-session-id", "discover_models": false,
  "models": {"haiku": {"context_length": 100000, "supports_vision": true, "prompt_caching": true},
             "sonnet": {"context_length": 200000, "supports_vision": true, "prompt_caching": true},
             "opus": {"context_length": 200000, "supports_vision": true, "prompt_caching": true},
             "local": {"context_length": 8192}}}'
cfg model.provider atena
cfg model.default haiku

# Voz da Atena: só com ATENA_VOZ=sim no atena.conf (precisa da GPU e da stack ai/voz no ar)
VOZ=$(sed -n 's/^ATENA_VOZ=//p' /etc/atena/atena.conf 2>/dev/null | tr -d '"' | tail -n 1)

# Ferramentas: pesquisa na web, Python e subagentes ficam; navegador, controle do computador,
# imagens e conexões externas saem. A voz sintetizada (tts) só fica com a voz ligada.
if [ "$VOZ" = sim ]; then
  cfg agent.disabled_toolsets '["browser", "computer_use", "image_gen", "connections"]'
else
  cfg agent.disabled_toolsets '["browser", "computer_use", "image_gen", "tts", "connections"]'
fi
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

# Respostas em voz: Kokoro da casa (stack ai/voz), através do LiteLLM, em pedaços de até 150 letras
# (texto maior, cheio de números, estoura uma GPU de 6 GB). O dono liga e desliga com /voice no Telegram.
# Outras vozes em português: pm_alex, pm_santa (hermes config set tts.openai.voice <voz>).
if [ "$VOZ" = sim ]; then
  cfg tts.provider openai
  cfg tts.openai.base_url http://litellm:4000/v1
  cfg tts.openai.model voz
  cfg tts.openai.voice pf_dora
  cfg tts.openai.max_text_length 150
fi

# Quem não é o dono não conversa (nem recebe resposta).
cfg unauthorized_dm_behavior ignore
cfg telegram.unauthorized_dm_behavior ignore

# Agendamentos: o que a ronda entrega entra na conversa do Telegram (a Atena lembra depois).
cfg cron.mirror_delivery true
# Agendamento de uma vez só (um lembrete): depois de rodar, o Hermes guarda o registro por 7 dias. Com
# 1 hora (0,0417 dia), ele some logo, e os diários, semanais e mensais continuam. O "hermes config set"
# diz que não conhece a chave, mas o agendador a lê (cron/jobs.py, _sweep_completed_oneshots).
cfg cron.completed_retention_days 0.0417

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
