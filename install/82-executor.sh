# Etapa 82: executor de ações e avisos no celular. O executor é o único caminho dos clientes
# (Hermes, painel) até o servidor: lista fechada de ações, token por cliente, sem shell.

msg "Executor de ações e avisos"

# atena-acoes: quem pode falar com o socket do executor. atena-exec: o usuário do executor.
getent group atena-acoes >/dev/null || groupadd --system atena-acoes
if ! id atena-exec >/dev/null 2>&1; then
  useradd --system --user-group --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin atena-exec
fi
usermod -aG docker,atena-acoes atena-exec
ok "usuário atena-exec (sem login) e grupo atena-acoes"

install -d -m 750 -o root -g atena-exec /etc/atena/executor
for s in atena-executor atena-avisar; do
  instalar_arquivo "$RAIZ/host/sbin/$s" "/usr/local/sbin/$s" 755
done
for u in atena-executor.service atena-avisar@.service atena-vigia.service atena-vigia.timer \
         atena-.service.d/50-avisar.conf atena-avisar@.service.d/99-sem-laco.conf; do
  instalar_arquivo "$RAIZ/host/systemd/$u" "/etc/systemd/system/$u"
done

# chave da Atena para o PC da rede de casa (só serve depois de configurar o PC: host/windows/LEIAME.md)
if [ ! -f /etc/atena/executor/pc-chave ]; then
  ssh-keygen -q -t ed25519 -N '' -C atena-pc -f /etc/atena/executor/pc-chave
  chgrp atena-exec /etc/atena/executor/pc-chave /etc/atena/executor/pc-chave.pub
  chmod 640 /etc/atena/executor/pc-chave
fi

systemctl daemon-reload
systemctl enable --now atena-executor.service atena-vigia.timer >/dev/null 2>&1
systemctl restart atena-executor.service   # numa atualização, pega a versão nova
sleep 1
systemctl is-active --quiet atena-executor || erro "o executor não subiu: journalctl -u atena-executor"
ok "executor no ar em /run/atena-executor/executor.sock (clientes: sudo atena-executor tokens)"
ok "avisos no celular: unidades atena-* com falha e containers parados (de 5 em 5 min)"
