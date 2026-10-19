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

ok "atena.conf válido"
