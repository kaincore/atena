# Etapa 50: serviços da Atena: atalhos das stacks para o Dockge,
# gravação da chave da Anthropic e virada do mês dos tetos do LiteLLM.

msg "Serviços da Atena"

for s in atena-stacks-sync atena-chave-anthropic atena-litellm-virada-mes; do
  instalar_arquivo "$RAIZ/host/sbin/$s" "/usr/local/sbin/$s" 755
done
for u in atena-stacks-sync.service atena-stacks-sync.path \
         atena-litellm-virada-mes.service atena-litellm-virada-mes.timer; do
  instalar_arquivo "$RAIZ/host/systemd/$u" "/etc/systemd/system/$u"
done
systemctl daemon-reload
systemctl enable --now atena-stacks-sync.path atena-litellm-virada-mes.timer >/dev/null 2>&1
systemctl start atena-stacks-sync.service
ok "atalhos do Dockge se atualizam sozinhos"
ok "tetos do LiteLLM zeram todo dia 1º às 00:00 UTC (e no boot, se estava desligado)"
