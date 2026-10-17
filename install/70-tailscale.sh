# Etapa 70 (opcional): Tailscale para acessar o servidor fora de casa.

[ "$ATENA_TAILSCALE" = sim ] || return 0

msg "Tailscale (acesso fora de casa)"
. /etc/os-release

if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL "https://pkgs.tailscale.com/stable/ubuntu/$VERSION_CODENAME.noarmor.gpg" \
    -o /usr/share/keyrings/tailscale-archive-keyring.gpg
  curl -fsSL "https://pkgs.tailscale.com/stable/ubuntu/$VERSION_CODENAME.tailscale-keyring.list" \
    -o /etc/apt/sources.list.d/tailscale.list
  apt-get update -qq
  apt-get install -y -qq tailscale >/dev/null
fi
ok "$(tailscale version | head -1)"

ufw allow in on tailscale0 to any port 22 proto tcp comment 'SSH via Tailscale' >/dev/null
ok "SSH liberado pela interface do Tailscale"

if ! tailscale status >/dev/null 2>&1; then
  aviso "falta entrar na sua conta: sudo tailscale up --hostname=$(hostname)"
  aviso "depois, no painel do Tailscale, desative a expiração da chave deste servidor"
fi
