# Etapa 30: zonas. Cada uma tem pasta de configuração, pasta de dados,
# limite de CPU/RAM (slice do systemd) e rede Docker com faixa de IP fixa.

msg "Criando as zonas (pastas, limites de CPU/RAM e redes)"

instalar_arquivo "$CONF" /etc/atena/atena.conf 644

ADMIN=$ATENA_ADMIN_USER
install -d -m 755 /opt/atena /opt/atena/bin /opt/atena/docs
install -d -m 750 -o "$ADMIN" -g "$ADMIN" /opt/atena/stacks /opt/atena/dockge
for z in $ZONAS; do
  modo=750; [ "$z" = prod ] && modo=700
  install -d -m "$modo" -o "$ADMIN" -g "$ADMIN" "/opt/atena/stacks/$z" "/srv/$z"
done
ok "pastas em /opt/atena/stacks/<zona> e /srv/<zona>"

for f in "$RAIZ"/host/systemd/atena*.slice; do
  instalar_arquivo "$f" "/etc/systemd/system/$(basename "$f")"
done
systemctl daemon-reload
for z in $ZONAS; do systemctl start "atena-$z.slice"; done
ok "limites de CPU/RAM: atena-<zona>.slice"

criar_rede() {
  nome=$1; faixa=$2; ponte=$3; shift 3
  if docker network inspect "$nome" >/dev/null 2>&1; then
    ok "rede $nome já existe"
    return
  fi
  # host_binding_ipv4: porta publicada sem IP fica só no servidor (o "ip" do daemon.json só vale na rede padrão)
  docker network create --driver bridge --subnet "$faixa" \
    -o com.docker.network.bridge.name="$ponte" \
    -o com.docker.network.bridge.host_binding_ipv4=127.0.0.1 \
    --label atena.zone="${nome#zone-}" "$@" "$nome" >/dev/null
  ok "rede $nome ($faixa)"
}
criar_rede zone-core   10.10.0.0/24   br-core
criar_rede zone-apps   10.10.10.0/24  br-apps
criar_rede zone-ai     10.10.20.0/24  br-ai
criar_rede zone-agents 10.10.30.0/24  br-agents
criar_rede zone-lab    10.10.40.0/24  br-lab
# rede de serviço: só o LiteLLM e quem pode usá-lo, sem saída para a internet
criar_rede svc-llm     10.10.250.0/24 br-svc-llm --internal
# rede de serviço: o ntfy e quem publica avisos nele (Hermes), sem saída para a internet
criar_rede svc-ntfy    10.10.251.0/24 br-svc-ntfy --internal
