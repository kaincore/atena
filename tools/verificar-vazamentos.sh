#!/usr/bin/env bash
# Procura segredos e dados pessoais antes de publicar. Sai com erro se achar algo.
#
# Uso:
#   tools/verificar-vazamentos.sh            # arquivos versionados + o que está no stage
#   tools/verificar-vazamentos.sh --historico # também todo o histórico do git
#
# Dados pessoais: um padrão (regex do grep -E) por linha em ~/.config/atena/padroes-privados.txt.
# Esse arquivo fica FORA do repositório: dentro, ele mesmo vazaria os dados.
# Os valores dos .env em /opt/atena/stacks também são procurados, se existirem.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PRIVADOS=${ATENA_PADROES_PRIVADOS:-$HOME/.config/atena/padroes-privados.txt}
padroes=$(mktemp); trap 'rm -f "$padroes"' EXIT

# segredos genéricos (o fim da lista: tokens de bot do Telegram, do ntfy e do executor)
cat >> "$padroes" <<'EOF'
sk-ant-[A-Za-z0-9_-]{10,}
sk-atena-[A-Za-z0-9_-]{10,}
-----BEGIN [A-Z ]*PRIVATE KEY-----
gh[pousr]_[A-Za-z0-9]{20,}
AKIA[0-9A-Z]{16}
tskey-[a-z]+-[A-Za-z0-9]+
[0-9]{8,10}:AA[A-Za-z0-9_-]{33}
tk_[a-z0-9]{29}
atx-[A-Za-z0-9_-]{40,}
EOF
# dados pessoais deste servidor
if [ -f "$PRIVADOS" ]; then
  grep -vE '^\s*(#|$)' "$PRIVADOS" >> "$padroes"
else
  echo "aviso: $PRIVADOS não existe; só os segredos genéricos serão procurados" >&2
fi
# valores reais dos .env do servidor (só os que têm 8 caracteres ou mais)
for env in /opt/atena/stacks/*/*/.env; do
  [ -r "$env" ] || continue
  grep -E '^[A-Z_]+=.{8,}$' "$env" | cut -d= -f2- | sed 's/[][\.*^$+?(){}|/]/\\&/g' >> "$padroes"
done

achou=0
if git ls-files -z | xargs -0 grep -nIE -f "$padroes" -- 2>/dev/null; then achou=1; fi
# (com o stage vazio, o xargs não roda o grep e devolve sucesso: por isso o teste antes)
if [ -n "$(git diff --cached --name-only)" ] \
   && git diff --cached --name-only -z | xargs -0 grep -nIE -f "$padroes" -- 2>/dev/null; then achou=1; fi
if git ls-files | grep -E '(^|/)\.env$'; then echo "arquivo .env versionado"; achou=1; fi
if [ "${1:-}" = --historico ] && git log -p --all | grep -nIE -f "$padroes" >/dev/null; then
  echo "o histórico do git contém dados pessoais ou segredos (rode: git log -p --all | grep -nIE -f <padrões>)"
  achou=1
fi

if [ "$achou" = 1 ]; then
  echo "BLOQUEADO: há segredos ou dados pessoais. Nada foi publicado." >&2
  exit 1
fi
echo "Nenhum segredo ou dado pessoal encontrado ($(wc -l < "$padroes") padrões verificados)."
