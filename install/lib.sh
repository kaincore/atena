# Funções usadas pelas etapas do instalador. Carregado por install.sh; não rode direto.

ZONAS="prod core apps ai agents lab"

msg()   { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
ok()    { printf '    \033[32mok\033[0m %s\n' "$*"; }
aviso() { printf '    \033[33maviso:\033[0m %s\n' "$*" >&2; }
erro()  { printf '\n\033[1;31merro:\033[0m %s\n' "$*" >&2; exit 1; }

# preenche os {{ATENA_*}} de um arquivo modelo com os valores do atena.conf
renderizar() {
  src=$1; dst=$2
  sed -e "s|{{ATENA_LAN_IP}}|$ATENA_LAN_IP|g" \
      -e "s|{{ATENA_LAN_CIDR}}|$ATENA_LAN_CIDR|g" \
      -e "s|{{ATENA_LAN_IF}}|$ATENA_LAN_IF|g" \
      -e "s|{{ATENA_ROUTER_IP}}|$ATENA_ROUTER_IP|g" \
      -e "s|{{ATENA_ADMIN_USER}}|$ATENA_ADMIN_USER|g" \
      "$src" > "$dst"
  if grep -q '{{ATENA_' "$dst"; then
    erro "sobrou um {{ATENA_...}} sem valor em $dst"
  fi
}

# instala um arquivo, guardando uma cópia do anterior se ele já existir e for diferente
instalar_arquivo() {
  src=$1; dst=$2; modo=${3:-644}
  if [ -f "$dst" ] && ! cmp -s "$src" "$dst"; then
    cp -a "$dst" "$dst.antes-atena-$(date +%Y%m%d%H%M%S)"
    aviso "$dst já existia; cópia guardada ao lado"
  fi
  install -D -m "$modo" -o root -g root "$src" "$dst"
}

segredo() { head -c 32 /dev/urandom | base64 | tr -d '/+=\n' | cut -c1-40; }
