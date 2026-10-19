#!/usr/bin/env bash
# Instalador do servidor Atena.
#
# Uso:
#   cp atena.conf.example atena.conf   # e ajuste os valores
#   sudo ./install.sh                  # instala ou atualiza
#   sudo ./install.sh --ssh            # também endurece o SSH (só chave, sem root)
#   sudo ./install.sh --hermes         # também instala a Atena (Hermes, pelo Telegram)
#
# Pode rodar de novo quando quiser: o que já existe é mantido ou atualizado.
set -euo pipefail

RAIZ=$(cd "$(dirname "$0")" && pwd)
CONF=$RAIZ/atena.conf
. "$RAIZ/install/lib.sh"

ENDURECER_SSH=nao
INSTALAR_HERMES=nao
for arg in "$@"; do
  case "$arg" in
    --ssh) ENDURECER_SSH=sim ;;
    --hermes) INSTALAR_HERMES=sim ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) erro "opção desconhecida: $arg (veja: ./install.sh --help)" ;;
  esac
done

[ -f "$CONF" ] || erro "falta o atena.conf. Crie com: cp atena.conf.example atena.conf (e ajuste os valores)"
# shellcheck source=atena.conf.example
. "$CONF"

REINICIAR=0
for etapa in "$RAIZ"/install/[0-9][0-9]-*.sh; do
  # shellcheck source=/dev/null
  . "$etapa"
done

msg "Pronto"
cat <<EOF
    Dockge (stacks):      http://$ATENA_LAN_IP:5001   -> crie a conta de administrador agora
    Beszel (monitor):     http://$ATENA_LAN_IP:8090   -> crie a conta e adicione o sistema
                                                         com o host /beszel_socket/beszel.sock
    Outras stacks:        /opt/atena/stacks/<zona>/<nome> (suba pelo Dockge)
    Chave da Anthropic:   atena-chave-anthropic (para o LiteLLM)
    Avisos no celular:    sudo atena-ntfy-celular <seu-usuario> (app ntfy, em $ATENA_NTFY_URL)
    Executor de ações:    sudo atena-executor tokens (quem pode pedir o quê)
    Regras do servidor:   docs/ neste repositório
EOF
if [ "$INSTALAR_HERMES" = sim ]; then
  cat <<EOF
    Atena (Hermes):       1. suba o LiteLLM (stack ai/litellm) e grave a chave da Anthropic
                          2. sudo atena-hermes-chave      (chave da Atena no LiteLLM, com teto)
                          3. sudo atena-telegram          (bot do Telegram; só você conversa)
EOF
fi
if [ "$REINICIAR" = 1 ]; then
  aviso "reinicie o servidor para terminar (driver da NVIDIA): sudo reboot"
fi
