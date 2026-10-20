# Etapa 80: stacks. Copia cada stack para /opt/atena/stacks/<zona>/<nome>, preenche o IP,
# gera os segredos e sobe o núcleo (Dockge e Beszel). As outras ficam prontas para subir.
# Stacks que já existem no servidor não são sobrescritas.

msg "Stacks"
ADMIN=$ATENA_ADMIN_USER

for compose in "$RAIZ"/stacks/*/*/compose.yaml; do
  origem=$(dirname "$compose")
  zona=$(basename "$(dirname "$origem")")
  nome=$(basename "$origem")
  destino=/opt/atena/stacks/$zona/$nome
  # o painel tem etapa própria (85, com --painel), que também atualiza o código dele
  [ "$zona/$nome" = core/painel ] && continue
  if [ -e "$destino/compose.yaml" ]; then
    ok "$zona/$nome já existe, mantida como está"
    continue
  fi
  install -d "$destino"
  cp -a "$origem/." "$destino/"
  # preenche os {{ATENA_*}} do compose e de qualquer outro arquivo da stack (ex.: server.yml do ntfy)
  { grep -rlF '{{ATENA_' "$origem" || true; } | while read -r f; do
    renderizar "$f" "$destino/${f#"$origem"/}"
  done
  if [ "$ATENA_GPU" = none ]; then
    # sem GPU: tira o pedido de GPU e usa as imagens que rodam só na CPU
    sed -i '/^ *gpus: all/d' "$destino/compose.yaml"
    sed -i -e 's|speaches:0.8.3-cuda-12.6.3 .*|speaches:0.8.3-cpu|' \
           -e 's|WHISPER__INFERENCE_DEVICE: cuda|WHISPER__INFERENCE_DEVICE: cpu|' \
           -e 's|henrygd/beszel-agent-nvidia:|henrygd/beszel-agent:|' "$destino/compose.yaml"
  fi
  chown -R "$ADMIN:$ADMIN" "$destino"
  ok "$zona/$nome"
done

# atalhos do Dockge: o .path perde mudanças feitas enquanto a sincronização roda,
# e aqui várias stacks são criadas de uma vez
systemctl start atena-stacks-sync.service

# pastas de dados usadas pelos composes
for d in core/dockge core/beszel/data core/beszel/agent core/beszel/socket core/beszel/disco-srv \
         ai/models/ollama ai/models/huggingface ai/ollama ai/litellm/db ai/litellm/redis \
         apps/arca/uploads apps/arca/data apps/open-webui; do
  install -d -m 750 -o "$ADMIN" -g "$ADMIN" "/srv/$d"
done

# segredos do LiteLLM (a chave da Anthropic é gravada depois, com atena-chave-anthropic)
L=/opt/atena/stacks/ai/litellm
if [ -d "$L" ] && [ ! -f "$L/.env" ]; then
  ( umask 077
    printf '%s\n' "# Segredos do LiteLLM. Não compartilhe este arquivo." \
      "ANTHROPIC_API_KEY=" \
      "LITELLM_MASTER_KEY=sk-atena-$(segredo)" \
      "LITELLM_SALT_KEY=$(segredo)" \
      "POSTGRES_PASSWORD=$(segredo)" \
      "REDIS_PASSWORD=$(segredo)" > "$L/.env" )
  chown "$ADMIN:$ADMIN" "$L/.env"
  ok "segredos do LiteLLM gerados em $L/.env"
fi

# segredo do Open WebUI (a chave do LiteLLM para ele é criada depois, com teto próprio)
W=/opt/atena/stacks/apps/open-webui
if [ -d "$W" ] && [ ! -f "$W/.env" ]; then
  ( umask 077
    printf '%s\n' "# Segredos do Open WebUI. Não compartilhe este arquivo." \
      "WEBUI_SECRET_KEY=$(segredo)" \
      "OPENAI_API_KEYS=" > "$W/.env" )
  chown "$ADMIN:$ADMIN" "$W/.env"
  ok "segredo do Open WebUI gerado em $W/.env"
fi

# núcleo: Dockge e Beszel
( cd /opt/atena/stacks/core/dockge && docker compose up -d --quiet-pull >/dev/null 2>&1 )
ok "Dockge: http://$ATENA_LAN_IP:5001"

B=/opt/atena/stacks/core/beszel
if [ ! -f "$B/.env" ]; then
  ( cd "$B" && docker compose up -d --quiet-pull beszel >/dev/null 2>&1 )
  for _ in $(seq 1 30); do [ -f /srv/core/beszel/data/id_ed25519 ] && break; sleep 2; done
  [ -f /srv/core/beszel/data/id_ed25519 ] || erro "o Beszel não gerou a chave dele"
  ( umask 077; printf 'BESZEL_KEY=%s\n' "$(ssh-keygen -y -f /srv/core/beszel/data/id_ed25519)" > "$B/.env" )
  chown "$ADMIN:$ADMIN" "$B/.env"
fi
( cd "$B" && docker compose up -d --quiet-pull >/dev/null 2>&1 )
ok "Beszel: http://$ATENA_LAN_IP:8090"
