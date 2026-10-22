# Etapa 85 (só com --painel): o painel do servidor no navegador e no celular (PWA), pelo Tailscale e,
# com ATENA_PAINEL_CASA=sim, também na rede de casa, em HTTP.
# O container não tem rede: o tailscale serve entrega as visitas por um socket, e o painel pede as
# ações ao executor por outro, com um token só dele (38 ações; só apaga apps do lab e só edita stacks de apps, confirmando na tela).
# O código do painel é atualizado a cada execução. Depois, falta você: sudo atena-painel-senha.

[ "$INSTALAR_PAINEL" = sim ] || return 0

msg "Painel (navegador e celular, pelo Tailscale)"
[ "$ATENA_TAILSCALE" = sim ] || erro "o painel só abre pelo Tailscale: ponha ATENA_TAILSCALE=sim no atena.conf"
ADMIN=$ATENA_ADMIN_USER
P=/opt/atena/stacks/core/painel
D=/srv/core/painel
PORTA_PAINEL=3100
ACOES_PAINEL=status.servicos,status.recursos,status.containers,status.sistema,sistema.sensores,gasto.api
ACOES_PAINEL=$ACOES_PAINEL,servico.logs,servico.reiniciar,pc.estado,pc.ligar,pc.desligar,pc.reiniciar,pc.cancelar
ACOES_PAINEL=$ACOES_PAINEL,app.lista,app.reiniciar,app.parar
ACOES_PAINEL=$ACOES_PAINEL,aprovacoes.lista,aprovacoes.decidir,atividade.lista   # a central
ACOES_PAINEL=$ACOES_PAINEL,sistema.processos,sistema.rede,servico.journal        # a aba Sistema
ACOES_PAINEL=$ACOES_PAINEL,app.publicar,app.cancelar,app.apagar,app.restaurar,app.comando   # o lab
ACOES_PAINEL=$ACOES_PAINEL,claude.tarefa,claude.trabalhos,claude.cancelar                   # o Claude Code
ACOES_PAINEL=$ACOES_PAINEL,stack.editar,stack.aplicar,stack.fotos,stack.desfazer            # o editor de stacks
ACOES_PAINEL=$ACOES_PAINEL,arquivo.ler,arquivo.procurar,arquivo.buscar,aviso.celular        # arquivos e os avisos da agenda
ZONAS_PAINEL=core,apps,ai,agents,lab

# atena-painel: sem login, sem sudo, sem Docker; o grupo atena-acoes dá acesso ao socket do executor
if ! id atena-painel >/dev/null 2>&1; then
  useradd --system --user-group --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin atena-painel
fi
usermod -aG atena-acoes atena-painel
id -nG atena-painel | grep -qw docker && erro "o usuário atena-painel está no grupo docker (equivale a root); tire com: gpasswd -d atena-painel docker"
ok "usuário atena-painel (sem login, sem sudo, sem Docker)"

# dados (banco, hash da senha, token) só para ele; o socket do tailscale serve fica em run/
install -d -m 700 -o atena-painel -g atena-painel "$D"
install -d -m 750 -o atena-painel -g atena-painel "$D/run"
instalar_arquivo "$RAIZ/host/sbin/atena-painel-senha" /usr/local/sbin/atena-painel-senha 755

# a stack: o código vem sempre do repositório; o compose antigo fica guardado se mudou
install -d "$P"
rm -rf "$P/app"
cp -a "$RAIZ/stacks/core/painel/app" "$P/app"
novo=$(mktemp)
renderizar "$RAIZ/stacks/core/painel/compose.yaml" "$novo"
if [ -f "$P/compose.yaml" ] && ! cmp -s "$novo" "$P/compose.yaml"; then
  cp -a "$P/compose.yaml" "$P/compose.yaml.antes-atena-$(date +%Y%m%d%H%M%S)"
  aviso "$P/compose.yaml mudou; cópia do anterior guardada ao lado"
fi
mv "$novo" "$P/compose.yaml"
chmod 644 "$P/compose.yaml"
( umask 077
  printf '%s\n' "# Preenchido pelo instalador: os números do usuário atena-painel e do grupo atena-acoes" \
    "PAINEL_UID=$(id -u atena-painel)" "PAINEL_GID=$(id -g atena-painel)" \
    "ACOES_GID=$(getent group atena-acoes | cut -d: -f3)" > "$P/.env" )
chown -R "$ADMIN:$ADMIN" "$P"
systemctl start atena-stacks-sync.service   # atalho no Dockge
ok "stack core/painel"

# token do executor: refeito só quando falta ou não bate com as ações e zonas acima
if ! python3 -I - "$D/executor.token" "$ACOES_PAINEL" "$ZONAS_PAINEL" <<'PY'
import hashlib, json, sys
arquivo, acoes, zonas = sys.argv[1], sys.argv[2].split(","), sys.argv[3].split(",")
try:
    with open(arquivo) as f:
        atual = hashlib.sha256(f.read().strip().encode()).hexdigest()
    with open("/etc/atena/executor/tokens.json") as f:
        t = json.load(f).get(atual)
except (OSError, ValueError):
    sys.exit(1)
sys.exit(0 if t and t["cliente"] == "painel" and sorted(t["acoes"]) == sorted(acoes)
         and sorted(t["zonas"]) == sorted(zonas) and t.get("aprovar") == [] else 1)
PY
then
  # arquivo novo e mv: o install do uutils não copia de /dev/stdin por cima de um arquivo existente
  ( umask 077; atena-executor token-novo painel "$ACOES_PAINEL" "$ZONAS_PAINEL" nenhuma > "$D/executor.token.novo" )
  chown atena-painel:atena-painel "$D/executor.token.novo"
  mv "$D/executor.token.novo" "$D/executor.token"
fi
ok "token do executor (sem aprovação no celular: quem confirma é você, na tela do painel)"

( cd "$P" && docker compose up -d --build --quiet-pull >/dev/null 2>&1 ) \
  || erro "o painel não subiu (cd $P && docker compose up -d --build)"
for _ in $(seq 1 30); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' painel 2>/dev/null)" = healthy ] && break
  sleep 2
done
[ "$(docker inspect -f '{{.State.Health.Status}}' painel 2>/dev/null)" = healthy ] \
  || erro "o painel subiu, mas não respondeu (docker logs painel)"
ok "painel no ar, sem rede, no socket $D/run/painel.sock"

# a entrada pelo Tailscale: HTTPS na porta do painel, entregue no socket
ufw allow in on tailscale0 to any port "$PORTA_PAINEL" proto tcp comment 'painel (tailscale serve)' >/dev/null
PAINEL_ENDERECO="https://<servidor>.<seu-tailnet>.ts.net:$PORTA_PAINEL"
if tailscale status >/dev/null 2>&1; then
  # o timeout: sem o HTTPS ligado no tailnet, o tailscale serve fica esperando
  if timeout 30 tailscale serve --bg --yes --https="$PORTA_PAINEL" "unix:$D/run/painel.sock" >/dev/null 2>&1; then
    PAINEL_ENDERECO="https://$(tailscale status --json | python3 -c 'import json, sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))'):$PORTA_PAINEL"
    ok "painel: $PAINEL_ENDERECO"
  else
    aviso "o tailscale serve não ligou. Ative o HTTPS no painel do Tailscale (DNS → HTTPS Certificates) e rode:"
    aviso "sudo tailscale serve --bg --https=$PORTA_PAINEL unix:$D/run/painel.sock"
  fi
else
  aviso "o Tailscale ainda não está logado. Depois do tailscale up, rode:"
  aviso "sudo tailscale serve --bg --https=$PORTA_PAINEL unix:$D/run/painel.sock"
fi
# a entrada da rede de casa (ATENA_PAINEL_CASA=sim): HTTP na mesma porta, só no IP de casa. O systemd
# escuta e entrega cada visita ao segundo socket do painel; desligada, as unidades e a regra saem.
REGRA_CASA=(in on "$ATENA_LAN_IF" from "$ATENA_LAN_CIDR" to "$ATENA_LAN_IP" port "$PORTA_PAINEL" proto tcp)
PAINEL_CASA_ENDERECO=
if [ "$ATENA_PAINEL_CASA" = sim ]; then
  for u in atena-painel-casa.socket atena-painel-casa.service; do
    tmp=$(mktemp)
    renderizar "$RAIZ/host/systemd/$u" "$tmp"
    instalar_arquivo "$tmp" "/etc/systemd/system/$u"
    rm -f "$tmp"
  done
  systemctl daemon-reload
  systemctl enable atena-painel-casa.socket >/dev/null 2>&1
  systemctl stop atena-painel-casa.service     # o repassador volta na próxima visita, com a unidade nova
  systemctl restart atena-painel-casa.socket   # pega um IP novo do atena.conf
  ufw allow "${REGRA_CASA[@]}" comment 'painel na rede de casa (http)' >/dev/null
  PAINEL_CASA_ENDERECO="http://$ATENA_LAN_IP:$PORTA_PAINEL"
  ok "painel na rede de casa: $PAINEL_CASA_ENDERECO (HTTP: a senha passa aberta no Wi-Fi)"
elif [ -f /etc/systemd/system/atena-painel-casa.socket ]; then
  systemctl disable --now atena-painel-casa.socket atena-painel-casa.service >/dev/null 2>&1 || true
  rm -f /etc/systemd/system/atena-painel-casa.socket /etc/systemd/system/atena-painel-casa.service
  systemctl daemon-reload
  ufw delete allow "${REGRA_CASA[@]}" >/dev/null 2>&1 || true
  ok "painel fora da rede de casa (ATENA_PAINEL_CASA=nao)"
fi
[ -s "$D/senha" ] || aviso "falta a senha do painel: sudo atena-painel-senha"
