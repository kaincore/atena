#!/usr/bin/env bash
# Roda aqui os mesmos jobs do CI (.github/workflows/verificar.yml), em containers, sobre o que está
# commitado (o que o GitHub vê). Rode antes de cada push.
#
#   tools/ci-local.sh            o HEAD
#   tools/ci-local.sh --arvore   os arquivos como estão agora (rastreados e novos não ignorados)
#
# Precisa de Docker (com o plugin compose) e de rede para baixar as imagens e o python3-yaml.
set -euo pipefail

RAIZ=$(git rev-parse --show-toplevel)
cd "$RAIZ"
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
copia="$tmp/repo"
mkdir "$copia"
if [ "${1:-}" = --arvore ]; then
  git ls-files -z --cached --others --exclude-standard | xargs -0 cp --parents -t "$copia"
else
  git archive HEAD | tar -x -C "$copia"
fi
compose=
for c in /usr/libexec/docker/cli-plugins/docker-compose /usr/lib/docker/cli-plugins/docker-compose \
         /usr/local/lib/docker/cli-plugins/docker-compose; do
  if [ -x "$c" ]; then compose=$c; break; fi
done
[ -n "$compose" ] || { echo "não achei o plugin docker compose" >&2; exit 1; }

falhas=()
job() {   # job <nome> <comando...>: roda e anota a falha sem parar os outros
  local nome=$1
  shift
  echo "== $nome"
  if "$@"; then echo "ok   $nome"; else echo "FALHA $nome"; falhas+=("$nome"); fi
}

# a lista de arquivos vem do grep e se divide em palavras de propósito
# shellcheck disable=SC2046
shellcheck_bash() (
  cd "$copia"
  docker run --rm -v "$copia:/mnt:ro" -w /mnt koalaman/shellcheck:v0.10.0 -x -s bash \
    install.sh install/*.sh tools/verificar-vazamentos.sh tools/ci-local.sh \
    $(grep -lE '^#!(/bin/bash|/usr/bin/env bash)' host/sbin/*)
)

# shellcheck disable=SC2046
shellcheck_sh() (
  cd "$copia"
  docker run --rm -v "$copia:/mnt:ro" -w /mnt koalaman/shellcheck:v0.10.0 -s sh \
    host/lab/atena-tela $(grep -l '^#!/bin/sh' host/sbin/* tools/hooks/* hermes/*.sh)
)

# shellcheck disable=SC2046
ruff() (
  cd "$copia"
  docker run --rm -v "$copia:/repo:ro" -w /repo ghcr.io/astral-sh/ruff:0.16.10 check --no-cache \
    $(grep -l '^#!.*python' host/sbin/*) aplicar install/estado.py host/executor host/lab hermes/scripts tests
)

composes() (
  cd "$copia"
  set -a
  # shellcheck disable=SC1091
  . ./atena.conf.example
  set +a
  for f in stacks/*/*/compose.yaml; do
    d=$(mktemp -d -p "$tmp")
    cp -r "$(dirname "$f")/." "$d/"
    sed -e "s|{{ATENA_LAN_IP}}|$ATENA_LAN_IP|g" -e "s|{{ATENA_TZ}}|$ATENA_TZ|g" \
        -e "s|{{ATENA_NTFY_URL}}|$ATENA_NTFY_URL|g" -e "s|{{ATENA_PAINEL_CASA}}|$ATENA_PAINEL_CASA|g" \
        "$f" > "$d/compose.yaml"
    if [ -f "$d/.env.example" ]; then cp "$d/.env.example" "$d/.env"; fi
    docker compose -f "$d/compose.yaml" config --quiet || { echo "compose inválido: $f"; return 1; }
  done
)

# como no runner do GitHub: Ubuntu 24.04, usuário comum, docker e compose do host, python3-yaml e git
testes_python() {
  docker run --rm -v "$copia:/repo:ro" -v /usr/bin/docker:/usr/bin/docker:ro -v "$compose:$compose:ro" ubuntu:24.04 bash -c '
    apt-get update -qq >/dev/null && apt-get install -y -qq python3-yaml git >/dev/null 2>&1 || exit 1
    mkdir -p /srv && useradd -m runner && cp -r /repo /home/runner/repo && chown -R runner /home/runner/repo
    su runner -c "cd /home/runner/repo
      for f in host/sbin/atena-executor host/sbin/atena-telegram host/sbin/atena-claude-runner \
               host/sbin/atena-painel-senha host/lab/dono.py host/lab/guarda_escopo.py hermes/scripts/ronda.py \
               host/executor/atena_executor/*.py aplicar install/estado.py; do
        python3 -c \"import ast, sys; ast.parse(open(sys.argv[1]).read(), sys.argv[1])\" \$f || exit 1
      done
      falharam=
      for t in tests/executor/teste_*.py tests/hermes/teste_*.py tests/host/teste_*.py tests/install/teste_*.py tests/lab/teste_*.py; do
        (cd \$(dirname \$t) && /usr/bin/python3 \$(basename \$t)) > /tmp/saida 2>&1 || { falharam=\"\$falharam \$t\"; cat /tmp/saida; }
      done
      [ -z \"\$falharam\" ] || { echo \"falharam:\$falharam\"; exit 1; }"'
}

tipos_painel() {
  docker run --rm -v "$copia/stacks/core/painel/app:/app:ro" -w /app node:22.23.4-alpine3.24 sh -c \
    'npm install --prefix /tmp/tsc --no-audit --no-fund --loglevel=error typescript@6.0.3 @types/node@22.20.5 >/dev/null \
     && /tmp/tsc/node_modules/.bin/tsc -p /app --typeRoots /tmp/tsc/node_modules/@types'
}

testes_painel() {
  docker run --rm --network none -v "$copia/stacks/core/painel/app:/app:ro" -w /app node:22.23.4-alpine3.24 npm test
}

gitleaks() {
  docker run --rm -v "$RAIZ:/repo:ro" zricethezav/gitleaks:v8.21.2 git /repo --redact
}

job "shellcheck (bash)" shellcheck_bash
job "shellcheck (sh)" shellcheck_sh
job "ruff" ruff
job "composes válidos" composes
job "tipos do painel" tipos_painel
job "testes do painel" testes_painel
job "testes (executor, Hermes e lab)" testes_python
job "gitleaks" gitleaks

echo
if [ ${#falhas[@]} -gt 0 ]; then
  echo "Falharam: ${falhas[*]}"
  exit 1
fi
echo "Todos os jobs do CI passaram."
