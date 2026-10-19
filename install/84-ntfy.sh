# Etapa 84: ntfy (avisos e aprovações no celular). Sobe o ntfy, cria os usuários de serviço e
# grava os tokens deles para o executor. O seu usuário do celular: sudo atena-ntfy-celular <nome>.

msg "ntfy (avisos e aprovações no celular)"

instalar_arquivo "$RAIZ/host/sbin/atena-ntfy-celular" /usr/local/sbin/atena-ntfy-celular 755
N=/opt/atena/stacks/core/ntfy
install -d -m 700 -o 65534 -g 65534 /srv/core/ntfy   # o ntfy roda como nobody
( cd "$N" && docker compose up -d --quiet-pull >/dev/null 2>&1 ) || erro "o ntfy não subiu (cd $N && docker compose up)"
for _ in $(seq 1 30); do   # o banco de usuários aparece quando o ntfy termina de subir
  [ -f /srv/core/ntfy/user.db ] && break
  sleep 1
done
[ -f /srv/core/ntfy/user.db ] || erro "o ntfy não criou o banco de usuários (docker logs ntfy)"

# usuários de serviço: a senha é aleatória e ninguém a usa; eles entram só pelo token
usuario_ntfy() {
  docker exec -e NTFY_PASSWORD="$(segredo)" ntfy ntfy user add --ignore-exists "$1" >/dev/null
}
token_ntfy() {   # token_ntfy <usuário> <arquivo>: cria o token só se o arquivo ainda não existe
  [ -s "$2" ] && return 0
  t=$(docker exec ntfy ntfy token add --label atena "$1" 2>&1 | grep -o 'tk_[a-z0-9]*' | head -n 1)
  [ -n "$t" ] || erro "não consegui criar o token do ntfy para $1"
  ( umask 027; printf '%s\n' "$t" > "$2" )
  chgrp atena-exec "$2"
}
usuario_ntfy servidor     # publica alertas e pedidos de aprovação, lê as respostas
usuario_ntfy aprovador    # vai dentro dos botões do celular: só escreve no tópico respostas
docker exec ntfy ntfy access servidor alertas write-only >/dev/null
docker exec ntfy ntfy access servidor aprovacoes write-only >/dev/null
docker exec ntfy ntfy access servidor respostas read-only >/dev/null
docker exec ntfy ntfy access aprovador respostas write-only >/dev/null
token_ntfy servidor /etc/atena/executor/ntfy-servidor.token
token_ntfy aprovador /etc/atena/executor/ntfy-aprovador.token
ok "ntfy: http://$ATENA_LAN_IP:2586, usuários de serviço e tokens em /etc/atena/executor"
