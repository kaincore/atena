# Etapa 40: firewall. O ufw protege o próprio servidor; o atena-docker-firewall
# protege os containers (o ufw não enxerga portas do Docker).

msg "Firewall do servidor (ufw) e dos containers"

instalar_arquivo "$RAIZ/host/sbin/atena-docker-firewall" /usr/local/sbin/atena-docker-firewall 755
instalar_arquivo "$RAIZ/host/systemd/atena-docker-firewall.service" /etc/systemd/system/atena-docker-firewall.service
systemctl daemon-reload
systemctl enable atena-docker-firewall.service >/dev/null 2>&1
systemctl restart atena-docker-firewall.service
ok "firewall dos containers ativo (saída só para a internet; entrada só da rede de casa)"

ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow from "$ATENA_LAN_CIDR" to any port 22 proto tcp comment 'SSH so da rede de casa' >/dev/null
if ufw status | grep -qE '^(22|OpenSSH)[^ ]* +ALLOW +Anywhere'; then
  aviso "existe uma regra liberando SSH para qualquer lugar; confira com 'sudo ufw status numbered' e apague se não precisar"
fi
ufw --force enable >/dev/null
ok "ufw ativo: SSH só da rede de casa ($ATENA_LAN_CIDR)"
