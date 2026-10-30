# Etapa 00: confere a máquina e o atena.conf antes de mudar qualquer coisa.

msg "Verificando a máquina e o atena.conf"

[ "$(id -u)" -eq 0 ] || erro "rode com sudo: sudo ./install.sh"

. /etc/os-release
[ "$ID" = ubuntu ] || erro "este instalador é para Ubuntu (encontrado: $ID)"
case "$VERSION_ID" in
  26.04) ok "Ubuntu $VERSION_ID" ;;
  *) aviso "Ubuntu $VERSION_ID ainda não foi testado (testado: 26.04)" ;;
esac

for v in ATENA_LAN_IF ATENA_LAN_IP ATENA_LAN_CIDR ATENA_ROUTER_IP ATENA_ADMIN_USER ATENA_GPU ATENA_TAILSCALE; do
  eval "valor=\${$v:-}"
  [ -n "$valor" ] || erro "$v está vazio no atena.conf"
done

# chaves que chegaram na versão 0.2: um atena.conf mais antigo fica com o padrão
: "${ATENA_TZ:=America/Sao_Paulo}"
: "${ATENA_NTFY_URL:=http://$ATENA_LAN_IP:2586}"
[ -f "/usr/share/zoneinfo/$ATENA_TZ" ] || erro "ATENA_TZ=$ATENA_TZ não é um fuso horário válido (ex.: America/Sao_Paulo)"
case "$ATENA_NTFY_URL" in http://*|https://*) ;; *) erro "ATENA_NTFY_URL deve começar com http:// ou https://" ;; esac
# chaves da versão 0.3
: "${ATENA_SENSORES_MODULO:=}"
: "${ATENA_VOZ:=nao}"
case "$ATENA_VOZ" in sim|nao) ;; *) erro "ATENA_VOZ deve ser sim ou nao" ;; esac
[ "$ATENA_VOZ" = nao ] || [ "$ATENA_GPU" = nvidia ] \
  || erro "ATENA_VOZ=sim precisa de ATENA_GPU=nvidia (na CPU a voz fica lenta demais para o Telegram)"
# chaves da versão 0.4 (lab)
: "${ATENA_CLAUDE_CONTAS:=principal}"
: "${ATENA_CLAUDE_TROCA:=nao}"
: "${ATENA_CLAUDE_VERSAO:=2.1.302}"
: "${ATENA_CLAUDE_SKILLS:=nao}"
for c in ${ATENA_CLAUDE_CONTAS//,/ }; do
  [[ $c =~ ^[a-z0-9][a-z0-9-]{0,19}$ ]] \
    || erro "ATENA_CLAUDE_CONTAS: \"$c\" não vale como nome de conta (minúsculas, números e hífen, até 20)"
done
case "$ATENA_CLAUDE_TROCA" in sim|nao) ;; *) erro "ATENA_CLAUDE_TROCA deve ser sim ou nao" ;; esac
case "$ATENA_CLAUDE_SKILLS" in sim|nao) ;; *) erro "ATENA_CLAUDE_SKILLS deve ser sim ou nao" ;; esac
[[ $ATENA_CLAUDE_VERSAO =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || erro "ATENA_CLAUDE_VERSAO deve ser uma versão, como 2.1.302"
case "$ATENA_SENSORES_MODULO" in
  *[!a-z0-9_]*) erro "ATENA_SENSORES_MODULO deve ser o nome de um módulo do kernel (ex.: nct6683) ou vazio" ;;
esac
# chave da versão 0.17 (o painel também na rede de casa)
: "${ATENA_PAINEL_CASA:=nao}"
case "$ATENA_PAINEL_CASA" in sim|nao) ;; *) erro "ATENA_PAINEL_CASA deve ser sim ou nao" ;; esac
# chaves da versão 0.27 (o PC da rede de casa no LiteLLM e no firewall dos containers)
: "${ATENA_PC_IP:=}"
: "${ATENA_PC_PORTA:=1234}"
: "${ATENA_PC_MODELO:=qwen3-14b}"
: "${ATENA_PC_RESERVA:=}"
[ -z "$ATENA_PC_IP" ] || [[ $ATENA_PC_IP =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] \
  || erro "ATENA_PC_IP deve ser o IP do PC na rede de casa (ex.: 192.168.0.50) ou vazio"
[[ $ATENA_PC_PORTA =~ ^[0-9]{1,5}$ ]] || erro "ATENA_PC_PORTA deve ser um número de porta (ex.: 1234)"
[[ $ATENA_PC_MODELO =~ ^[A-Za-z0-9._:/-]+$ ]] \
  || erro "ATENA_PC_MODELO deve ser o nome do modelo no LM Studio (ex.: qwen3-14b)"
case "$ATENA_PC_RESERVA" in
  "") ;;
  haiku|sonnet|opus|local) [ -n "$ATENA_PC_IP" ] || erro "ATENA_PC_RESERVA só vale com ATENA_PC_IP" ;;
  *) erro "ATENA_PC_RESERVA deve ser vazio ou um modelo do LiteLLM: haiku, sonnet, opus ou local" ;;
esac

ip link show "$ATENA_LAN_IF" >/dev/null 2>&1 \
  || erro "a interface $ATENA_LAN_IF não existe (veja as interfaces com: ip -br link)"
ip -4 addr show "$ATENA_LAN_IF" | grep -q "inet $ATENA_LAN_IP/" \
  || aviso "$ATENA_LAN_IF não está com o IP $ATENA_LAN_IP agora; configure o IP fixo antes de usar os serviços"
id "$ATENA_ADMIN_USER" >/dev/null 2>&1 || erro "o usuário $ATENA_ADMIN_USER não existe"

case "$ATENA_GPU" in nvidia|none) ;; *) erro "ATENA_GPU deve ser nvidia ou none" ;; esac
case "$ATENA_TAILSCALE" in sim|nao) ;; *) erro "ATENA_TAILSCALE deve ser sim ou nao" ;; esac
if [ "$ATENA_GPU" = nvidia ]; then
  lspci | grep -qi nvidia || erro "ATENA_GPU=nvidia, mas nenhuma placa NVIDIA foi encontrada"
fi

ok "atena.conf válido ($CONF)"
