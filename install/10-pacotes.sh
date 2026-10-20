# Etapa 10: pacotes básicos usados pelas outras etapas.

msg "Instalando pacotes básicos"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg conntrack ufw openssh-client python3 acl >/dev/null
ok "ca-certificates, curl, gnupg, conntrack, ufw, acl"
# executor: YAML (gasto da API) e leitura de PDF, Word e Excel (texto privado para o modelo de casa)
apt-get install -y -qq python3-yaml python3-pypdf python3-docx python3-openpyxl >/dev/null
ok "bibliotecas Python do executor"
