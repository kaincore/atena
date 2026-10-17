# Etapa 90 (só com --ssh): SSH só com chave, sem root e só para o administrador.
# Só aplica se o administrador já tiver uma chave autorizada, para ninguém ficar trancado para fora.

[ "$ENDURECER_SSH" = sim ] || return 0

msg "Endurecendo o SSH"

casa=$(getent passwd "$ATENA_ADMIN_USER" | cut -d: -f6)
if ! grep -qE '^(ssh-|ecdsa-)' "$casa/.ssh/authorized_keys" 2>/dev/null; then
  aviso "$ATENA_ADMIN_USER não tem chave SSH em $casa/.ssh/authorized_keys; SSH não foi alterado"
  return 0
fi

destino=/etc/ssh/sshd_config.d/00-atena-hardening.conf
anterior=$(mktemp); novo=$(mktemp)
tem_anterior=nao
if [ -f "$destino" ]; then cp -a "$destino" "$anterior"; tem_anterior=sim; fi
renderizar "$RAIZ/host/ssh/00-atena-hardening.conf" "$novo"
install -m 600 -o root -g root "$novo" "$destino"

# no Ubuntu 26.04 o SSH sobe sob demanda: sem ele rodando, falta a pasta que o "sshd -t" exige
install -d -m 0755 /run/sshd
if ! sshd -t; then
  if [ "$tem_anterior" = sim ]; then cp -a "$anterior" "$destino"; else rm -f "$destino"; fi
  rm -f "$anterior" "$novo"
  erro "a configuração nova do SSH é inválida; a anterior foi mantida"
fi
rm -f "$anterior" "$novo"

# com o SSH sob demanda, a próxima conexão já lê a configuração nova
if systemctl is-active --quiet ssh; then systemctl reload ssh; fi
ok "SSH só com chave, sem root, só para $ATENA_ADMIN_USER"
aviso "antes de fechar esta sessão, teste entrar por SSH num terminal novo"
