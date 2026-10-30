# Funções usadas pelas etapas do instalador. Carregado por install.sh; não rode direto.

ZONAS="prod core apps ai agents lab"

msg()   { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
ok()    { printf '    \033[32mok\033[0m %s\n' "$*"; }
aviso() { printf '    \033[33maviso:\033[0m %s\n' "$*" >&2; }
erro()  { printf '\n\033[1;31merro:\033[0m %s\n' "$*" >&2; exit 1; }

# preenche os {{ATENA_*}} de um arquivo modelo com os valores do atena.conf
renderizar() {
  src=$1; dst=$2
  sed -e "s|{{ATENA_LAN_IP}}|$ATENA_LAN_IP|g" \
      -e "s|{{ATENA_LAN_CIDR}}|$ATENA_LAN_CIDR|g" \
      -e "s|{{ATENA_LAN_IF}}|$ATENA_LAN_IF|g" \
      -e "s|{{ATENA_ROUTER_IP}}|$ATENA_ROUTER_IP|g" \
      -e "s|{{ATENA_ADMIN_USER}}|$ATENA_ADMIN_USER|g" \
      -e "s|{{ATENA_TZ}}|$ATENA_TZ|g" \
      -e "s|{{ATENA_NTFY_URL}}|$ATENA_NTFY_URL|g" \
      -e "s|{{ATENA_PAINEL_CASA}}|$ATENA_PAINEL_CASA|g" \
      "$src" > "$dst"
  if grep -q '{{ATENA_' "$dst"; then
    erro "sobrou um {{ATENA_...}} sem valor em $dst"
  fi
}

# instala um arquivo, guardando uma cópia do anterior se ele já existir e for diferente
instalar_arquivo() {
  src=$1; dst=$2; modo=${3:-644}
  if [ -f "$dst" ] && ! cmp -s "$src" "$dst"; then
    cp -a "$dst" "$dst.antes-atena-$(date +%Y%m%d%H%M%S)"
    aviso "$dst já existia; cópia guardada ao lado"
  fi
  install -D -m "$modo" -o root -g root "$src" "$dst"
}

# a ronda da Atena: o texto da tarefa agendada (as regras ficam na seção Ronda das habilidades)
RONDA="Ronda do servidor (e do Claude Code, se houver o lab). O bloco MONITOR CHANGE DETECTED mostra o que mudou na lista (ela diz tudo normal quando o servidor não tem problema; as linhas do Claude Code vêm no fim). Fale só do que mudou: as linhas iguais nas duas versões você já contou ao dono. Siga a seção Ronda das habilidades servidor-atena e lab: investigue e resolva o que for reversível no servidor (reiniciar uma vez o que caiu), repasse ao dono as perguntas do Claude Code e resuma os trabalhos que terminaram. Escreva curto e limpo, no seu tom. Quando a habilidade disser que não há nada a dizer, responda exatamente [SILENT]. Nada destrutivo."

# o id da tarefa "ronda" no Hermes, ou nada se ela não existe. Lê o arquivo, e não o "hermes cron list":
# logo depois de reiniciar, o Hermes ainda não responde.
cron_id() {   # o id de um job do cron da Atena pelo nome (vazio se não existe)
  python3 -c 'import json, sys
print(next((j["id"] for j in json.load(open(sys.argv[1])).get("jobs", []) if j.get("name") == sys.argv[2]), ""))' \
    /srv/agents/hermes/cron/jobs.json "$1" 2>/dev/null || true
}
ronda_id() { cron_id ronda; }

# token do executor para a Atena (/srv/agents/hermes/executor.token). Refaz o token quando ele não
# existe, quando o do arquivo não vale mais ou quando falta alguma das ações exigidas. Um token refeito
# mantém as zonas e a regra de aprovação que você tiver ajustado; as ações de aprovar_novas entram na
# regra de aprovação quando chegam ao token pela primeira vez.
# Uso: token_atena <ações de um token novo> <ações exigidas> [aprovar_novas]
token_atena() {
  local arquivo=/srv/agents/hermes/executor.token refazer r_acoes r_zonas r_aprovar tmp
  refazer=$(python3 - "$arquivo" "$1" "$2" "${3:-}" <<'PY'
import hashlib, json, sys
arquivo, acoes, exigidas = sys.argv[1], sys.argv[2].split(","), sys.argv[3].split(",")
aprovar_novas = [a for a in sys.argv[4].split(",") if a]
try:
    with open("/etc/atena/executor/tokens.json") as f:
        tokens = json.load(f)
except (OSError, ValueError):
    tokens = {}
try:
    with open(arquivo) as f:
        atual = hashlib.sha256(f.read().strip().encode()).hexdigest()
except OSError:
    atual = None
t = next((c for c in tokens.values() if c.get("cliente") == "hermes"), None)
if t is None:
    if acoes != [""]:
        print(",".join(acoes), "apps,ai,agents,lab,core", ",".join(aprovar_novas) or "nenhuma")
elif tokens.get(atual) is not t or not all(a in t["acoes"] for a in exigidas):
    faltam = [a for a in exigidas if a not in t["acoes"]]
    aprovar = ""
    if "aprovar" in t:
        aprovar = ",".join(t["aprovar"] + [a for a in aprovar_novas if a in faltam and a not in t["aprovar"]]) or "nenhuma"
    print(",".join(t["acoes"] + faltam), ",".join(t["zonas"]), aprovar)
PY
  )
  [ -n "$refazer" ] || return 0
  read -r r_acoes r_zonas r_aprovar <<< "$refazer"
  # num arquivo novo e depois no lugar: o install do Ubuntu 26.04 (uutils) não copia de /dev/stdin por
  # cima de um arquivo que já existe, e o token sai da tela direto para o arquivo
  tmp=$(mktemp "$arquivo.XXXXXX")
  /usr/local/sbin/atena-executor token-novo hermes "$r_acoes" "$r_zonas" ${r_aprovar:+"$r_aprovar"} > "$tmp" \
    || { rm -f "$tmp"; erro "não consegui criar o token do executor para a Atena"; }
  chown hermes:hermes "$tmp"
  mv "$tmp" "$arquivo"
  ok "token do executor para a Atena, novo ou refeito (sudo atena-executor tokens)"
}

segredo() { head -c 32 /dev/urandom | base64 | tr -d '/+=\n' | cut -c1-40; }
