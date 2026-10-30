# Etapa 86 (só com --hermes): a Atena, no Hermes. Cria o usuário hermes, a pasta de dados com a
# personalidade, as habilidades e a ronda, o token do executor e o usuário do ntfy, sobe o container
# e aplica a configuração. Depois, falta você: sudo atena-hermes-chave e sudo atena-telegram.

[ "$INSTALAR_HERMES" = sim ] || return 0

msg "Atena (Hermes)"

for s in atena-telegram atena-hermes-chave; do
  instalar_arquivo "$RAIZ/host/sbin/$s" "/usr/local/sbin/$s" 755
done

# usuário sem login, sem sudo e sem Docker; o grupo atena-acoes dá acesso ao socket do executor
if ! id hermes >/dev/null 2>&1; then
  useradd --system --user-group --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin hermes
fi
usermod -aG atena-acoes hermes
id -nG hermes | grep -qw docker && erro "o usuário hermes está no grupo docker (equivale a root); tire com: gpasswd -d hermes docker"
ok "usuário hermes (sem login, sem sudo, sem Docker)"

D=/srv/agents/hermes
S=/opt/atena/stacks/agents/hermes
install -d -m 700 -o hermes -g atena-acoes "$D"
install -d -m 2750 -o atena-exec -g atena-acoes "$D/entregas"   # o executor escreve; a Atena só lê
# o executor só ganha escrita em entregas se a pasta já existir quando ele sobe (ReadWritePaths=-...)
systemctl restart atena-executor
for p in skills skills/atena skills/atena/servidor-atena skills/atena/notas scripts ferramentas; do
  install -d -m 755 -o hermes -g atena-acoes "$D/$p"
done

# arquivos da Atena: como instalar_arquivo, mas do usuário hermes (o Hermes pode editá-los)
copiar_hermes() {
  src=$RAIZ/hermes/$1; dst=$D/$2
  if [ -f "$dst" ] && ! cmp -s "$src" "$dst"; then
    cp -a "$dst" "$dst.antes-atena-$(date +%Y%m%d%H%M%S)"
    aviso "$dst já existia; cópia guardada ao lado"
  fi
  install -m 644 -o hermes -g atena-acoes "$src" "$dst"
}
copiar_hermes SOUL.md SOUL.md
copiar_hermes skills/atena/servidor-atena/SKILL.md skills/atena/servidor-atena/SKILL.md
copiar_hermes skills/atena/notas/SKILL.md skills/atena/notas/SKILL.md
copiar_hermes scripts/ronda.py scripts/ronda.py
copiar_hermes scripts/acao.py scripts/acao.py
copiar_hermes scripts/bom_dia.py scripts/bom_dia.py
copiar_hermes ferramentas.txt ferramentas/requisitos.txt
ok "personalidade, habilidades servidor-atena e notas, ronda, acao e bom-dia em $D"

# token do executor: todas as consultas, reiniciar, o PC e as stacks de apps, sem a zona prod e
# sem pedir o celular. Para exigir o celular em algo, refaça com o 4º campo (veja docs/pt/operacao.md).
novas=sistema.sensores,stack.editar,stack.aplicar,stack.fotos,stack.desfazer
acoes=status.servicos,status.recursos,status.containers,status.sistema,gasto.api,servico.logs,servico.journal
acoes=$acoes,arquivo.ler,arquivo.procurar,arquivo.entregar,arquivo.buscar,local.processar,sistema.processos
acoes=$acoes,sistema.rede,$novas,servico.reiniciar,pc.estado,pc.ligar,pc.desligar,pc.reiniciar,pc.cancelar
token_atena "$acoes" "$novas"

# o compose usa o UID do hermes e o GID do atena-acoes
if [ ! -f "$S/.env" ]; then
  printf 'HERMES_UID=%s\nHERMES_GID=%s\n' "$(id -u hermes)" "$(getent group atena-acoes | cut -d: -f3)" > "$S/.env"
  chown "$ATENA_ADMIN_USER:$ATENA_ADMIN_USER" "$S/.env"
fi

msg "Subindo o Hermes (a primeira vez baixa uma imagem grande)"
( cd "$S" && docker compose up -d --quiet-pull >/dev/null 2>&1 ) || erro "o Hermes não subiu (cd $S && docker compose up)"
for _ in $(seq 1 60); do   # no primeiro início, o Hermes cria o config.yaml e o .env dele
  [ -f "$D/config.yaml" ] && [ -f "$D/.env" ] && break
  sleep 2
done
[ -f "$D/config.yaml" ] || erro "o Hermes não criou o config.yaml (docker logs hermes)"

# usuário do ntfy da Atena: lê e escreve só no tópico atena
docker exec -e NTFY_PASSWORD="$(segredo)" ntfy ntfy user add --ignore-exists hermes >/dev/null
docker exec ntfy ntfy access hermes atena read-write >/dev/null
if ! grep -q '^NTFY_TOKEN=.' "$D/.env"; then
  t=$(docker exec ntfy ntfy token add --label atena hermes 2>&1 | grep -o 'tk_[a-z0-9]*' | head -n 1)
  [ -n "$t" ] || erro "não consegui criar o token do ntfy para o Hermes"
  tmp=$(mktemp "$D/.env.XXXXXX")
  grep -v '^NTFY_TOKEN=' "$D/.env" > "$tmp" || true
  printf 'NTFY_TOKEN=%s\n' "$t" >> "$tmp"
  chown --reference="$D/.env" "$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$D/.env"
fi

sh "$RAIZ/hermes/configurar.sh" >/dev/null
ok "configuração: LiteLLM (haiku), aprovação smart, ouvir pelo Whisper, ntfy$([ "$ATENA_VOZ" = sim ] && echo ', responder em voz')"

# ferramentas Python da Atena (PDF, Word, Excel), num venv dentro do espaço dela
docker exec -u hermes hermes sh -c '[ -x /opt/data/ferramentas/py/bin/python ] || /opt/hermes/.venv/bin/python -m venv /opt/data/ferramentas/py'
docker exec -u hermes hermes /opt/data/ferramentas/py/bin/pip install -q --disable-pip-version-check \
  -r /opt/data/ferramentas/requisitos.txt >/dev/null || aviso "não consegui instalar as ferramentas Python da Atena"

docker restart hermes >/dev/null
sleep 10
# a ronda: criada uma vez e, nas atualizações, com o texto e as habilidades de agora (com o lab, a
# habilidade lab também, por causa das linhas do Claude Code)
skills_ronda=(--skill servidor-atena)
if [ -f "$D/skills/atena/lab/SKILL.md" ]; then skills_ronda+=(--skill lab); fi
id=$(ronda_id)
if [ -z "$id" ]; then
  docker exec -u hermes hermes hermes cron create "every 3m" "$RONDA" \
    --name ronda --monitor-script ronda.py "${skills_ronda[@]}" --deliver telegram --failure-deliver ntfy >/dev/null \
    || aviso "não consegui criar a ronda; crie depois (veja docs/pt/operacao.md)"
else
  # --failure-deliver ntfy: quando a IA não responde, a falha da ronda chega ao celular pelo ntfy
  docker exec -u hermes hermes hermes cron edit "$id" --prompt "$RONDA" "${skills_ronda[@]}" --failure-deliver ntfy >/dev/null \
    || aviso "não consegui atualizar a ronda (docker exec -u hermes hermes hermes cron list)"
fi
ok "ronda de 3 em 3 minutos (só gasta API quando algo muda)"

# o bom-dia: às 8h, sem IA (--no-agent): o script lê o servidor e a saída vai direto para o Telegram
if [ -z "$(cron_id bom-dia)" ]; then
  docker exec -u hermes hermes hermes cron create "0 8 * * *" --name bom-dia --script bom_dia.py --no-agent \
    --deliver telegram >/dev/null || aviso "não consegui criar o bom-dia (docker exec -u hermes hermes hermes cron list)"
fi
ok "bom-dia às 8h, sem IA"
