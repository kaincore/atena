# Etapa 10: pacotes básicos usados pelas outras etapas.

msg "Instalando pacotes básicos"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg conntrack ufw openssh-client python3 >/dev/null
ok "ca-certificates, curl, gnupg, conntrack, ufw"
