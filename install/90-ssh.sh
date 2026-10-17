# Etapa 90 (só com --ssh): SSH só com chave, sem root e só para o administrador.
# Só aplica se o administrador já tiver uma chave autorizada, para ninguém ficar trancado para fora.

[ "$ENDURECER_SSH" = sim ] || return 0

msg "Endurecendo o SSH"

casa=$(getent passwd "$ATENA_ADMIN_USER" | cut -d: -f6)
if ! grep -qE '^(ssh-|ecdsa-)' "$casa/.ssh/authorized_keys" 2>/dev/null; then
  aviso "$ATENA_ADMIN_USER não tem chave SSH em $casa/.ssh/authorized_keys; SSH não foi alterado"
  return 0
fi

tmp=$(mktemp)
renderizar "$RAIZ/host/ssh/00-atena-hardening.conf" "$tmp"
instalar_arquivo "$tmp" /etc/ssh/sshd_config.d/00-atena-hardening.conf 600
rm -f "$tmp"
sshd -t || erro "configuração do SSH inválida; nada foi recarregado"
systemctl reload ssh
ok "SSH só com chave, sem root, só para $ATENA_ADMIN_USER"
aviso "antes de fechar esta sessão, teste entrar por SSH num terminal novo"
