# Etapa 88 (só com --lab): o lab do Claude Code. O usuário atena-claude (sem sudo, sem Docker) roda os
# trabalhos que a Atena pede ao executor, em /srv/lab/projetos, no sandbox do Claude Code; os pedidos
# de permissão e as perguntas vão ao celular. Os apps prontos vão para a zona lab (app.publicar).
# Depois, falta você: sudo atena-claude-conta entrar <conta>, para cada conta de ATENA_CLAUDE_CONTAS
# (com ATENA_CLAUDE_SKILLS=sim, o login já põe os plugins e o Impeccable na conta).

[ "$INSTALAR_LAB" = sim ] || return 0

msg "Lab (Claude Code)"
ADMIN=$ATENA_ADMIN_USER
B=/var/lib/atena-claude
L=/usr/local/lib/atena-claude

# o sandbox do Claude Code (bubblewrap, socat) e o que ele usa para programar
# NEEDRESTART_SUSPEND: o needrestart reiniciaria serviços (o executor no meio da instalação) e encheria a tela
NEEDRESTART_SUSPEND=1 apt-get install -y -qq bubblewrap socat git python3-venv python3-pip nodejs npm >/dev/null
ok "bubblewrap, socat, git, Python (venv, pip), Node (node, npm)"

# atena-claude: sem login, sem sudo e sem Docker. atena-fila: quem fala com a fila (ele e o executor).
# atena-lab: quem escreve nos projetos (ele, o executor e você)
for g in atena-fila atena-lab; do getent group "$g" >/dev/null || groupadd --system "$g"; done
if ! id atena-claude >/dev/null 2>&1; then
  useradd --system --user-group --no-create-home --home-dir "$B" --shell /usr/sbin/nologin atena-claude
fi
usermod -aG atena-fila,atena-lab atena-claude
usermod -aG atena-fila,atena-lab atena-exec
usermod -aG atena-lab "$ADMIN"
id -nG atena-claude | grep -qw docker && erro "o usuário atena-claude está no grupo docker (equivale a root); tire com: gpasswd -d atena-claude docker"
ok "usuário atena-claude (sem login, sem sudo, sem Docker)"

# fila (o executor e o runner escrevem), resultados (o runner escreve, o executor lê), contas e registros
# (só o runner), projetos (o runner, o executor e você), lixeira (o executor) e as stacks dos apps do lab
install -d -m 711 -o atena-claude -g atena-claude "$B"
install -d -m 700 -o atena-claude -g atena-claude "$B/contas" "$B/registros"
install -d -m 755 -o atena-claude -g atena-claude "$B/.npm" "$B/.cache"
install -d -m 2770 -o root -g atena-fila "$B/fila"
install -d -m 2750 -o atena-claude -g atena-fila "$B/resultados"
install -m 644 -o root -g root "$RAIZ/host/lab/gitconfig" "$B/.gitconfig"
chgrp atena-lab /srv/lab
chmod 2750 /srv/lab
install -d -m 2775 -o atena-claude -g atena-lab /srv/lab/projetos
install -d -m 2750 -o atena-exec -g atena-lab /srv/lab/lixeira
chgrp atena-exec /opt/atena/stacks/lab
chmod 2770 /opt/atena/stacks/lab
ok "pastas: $B, /srv/lab/projetos, /srv/lab/lixeira e /opt/atena/stacks/lab"

# Claude Code, numa versão fixa, baixado do repositório oficial e conferido pelo checksum do manifesto.
# Não se atualiza sozinho: para trocar, mude ATENA_CLAUDE_VERSAO e rode o instalador de novo.
install -d -m 755 "$L"
if [ "$("$L/claude" --version 2>/dev/null | cut -d' ' -f1)" != "$ATENA_CLAUDE_VERSAO" ]; then
  case "$(uname -m)" in
    x86_64) plataforma=linux-x64 ;;
    aarch64) plataforma=linux-arm64 ;;
    *) erro "o Claude Code não tem versão para $(uname -m)" ;;
  esac
  origem=https://downloads.claude.ai/claude-code-releases/$ATENA_CLAUDE_VERSAO
  baixado=$(mktemp -d)
  curl -fsSL -o "$baixado/manifest.json" "$origem/manifest.json" \
    || erro "não achei o Claude Code $ATENA_CLAUDE_VERSAO em downloads.claude.ai"
  soma=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["platforms"][sys.argv[2]]["checksum"])' \
    "$baixado/manifest.json" "$plataforma")
  curl -fsSL -o "$baixado/claude" "$origem/$plataforma/claude" || erro "não consegui baixar o Claude Code"
  echo "$soma  $baixado/claude" | sha256sum -c --quiet - || erro "o Claude Code baixado não confere com o checksum oficial"
  install -m 755 -o root -g root "$baixado/claude" "$L/claude"
  rm -f "$baixado/claude" "$baixado/manifest.json"
  rmdir "$baixado"
fi
ok "Claude Code $ATENA_CLAUDE_VERSAO em $L/claude"

# runner, ponte, contas, lixeira e a configuração do trabalhador. O lab.json esconde do sandbox a
# credencial de cada conta do atena.conf.
for s in atena-claude-runner atena-claude-conta atena-lab-lixeira atena-lab-tailscale; do
  instalar_arquivo "$RAIZ/host/sbin/$s" "/usr/local/sbin/$s" 755
done
instalar_arquivo "$RAIZ/host/lab/dono.py" "$L/dono.py"
lab_json=$(mktemp)
python3 - "$RAIZ/host/lab/lab.json" "$lab_json" "$ATENA_CLAUDE_CONTAS" <<'PY'
import json, re, sys
cfg = json.load(open(sys.argv[1]))
contas = [c for c in dict.fromkeys(re.split(r"[\s,]+", sys.argv[3])) if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,19}", c)]
cfg["sandbox"]["filesystem"]["denyRead"] += [f"/var/lib/atena-claude/contas/{c}/.credentials.json" for c in contas]
with open(sys.argv[2], "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
instalar_arquivo "$lab_json" "$L/lab.json"
rm -f "$lab_json"
for u in atena-claude.path atena-claude.service atena-lab-lixeira.service atena-lab-lixeira.timer \
         atena-executor.service.d/lab.conf atena-lab.slice.d/50-lab.conf; do
  instalar_arquivo "$RAIZ/host/systemd/$u" "/etc/systemd/system/$u"
done
ok "runner, ponte, lixeira e o sandbox do trabalhador (contas: $ATENA_CLAUDE_CONTAS)"

# skills do Claude Code (ATENA_CLAUDE_SKILLS=sim): o catálogo que a Atena usa, o Impeccable (só o texto:
# sem o lançador, que baixa um binário, e sem os hooks), numa versão fixa e conferida, e as ferramentas do
# trabalhador: atena-tela (print de uma página local, com um Chromium sem tela) e os servidores de
# linguagem dos plugins pyright-lsp e typescript-lsp, nas versões do package-lock.json. Os plugins entram
# em cada conta pelo atena-claude-conta, porque precisam do login.
IMPECCABLE_COMMIT=08d5b470495d242ca0470f4aeae1956c3a074f83   # versão 4.6.0
IMPECCABLE_SOMA=7f33df64049dad1a20160305b5b9e5dc15d45dbdcc689a56cc89440f6c22ac1a   # dos arquivos copiados
soma_impeccable() (   # o sha256 da lista de sha256 dos arquivos que vão para as contas
  cd "$1" && find SKILL.md reference LICENSE NOTICE.md -type f -print0 | LC_ALL=C sort -z \
    | xargs -0 sha256sum | sha256sum | cut -d' ' -f1
)
instalar_arquivo "$RAIZ/host/lab/skills.json" "$L/skills.json"
if [ "$ATENA_CLAUDE_SKILLS" = sim ]; then
  F=$L/ferramentas
  install -d -m 755 "$F" "$F/bin"
  install -m 644 "$RAIZ/host/lab/ferramentas/package.json" "$RAIZ/host/lab/ferramentas/package-lock.json" "$F/"
  ( cd "$F" && npm ci --ignore-scripts --no-audit --no-fund --loglevel=error >/dev/null ) \
    || erro "não consegui instalar as ferramentas do lab (cd $F && npm ci)"
  # o Chromium sem tela e as bibliotecas do Ubuntu que ele usa
  NEEDRESTART_SUSPEND=1 DEBIAN_FRONTEND=noninteractive PLAYWRIGHT_BROWSERS_PATH="$F/navegadores" \
    node "$F/node_modules/playwright-core/cli.js" install --with-deps --only-shell chromium >/dev/null 2>&1 \
    || erro "não consegui instalar o Chromium sem tela do atena-tela"
  install -m 644 "$RAIZ/host/lab/tela.js" "$F/tela.js"
  install -m 755 "$RAIZ/host/lab/atena-tela" "$F/bin/atena-tela"
  chmod -R a+rX "$F"
  imp=$L/skills/impeccable
  if [ ! -d "$imp" ] || [ "$(soma_impeccable "$imp")" != "$IMPECCABLE_SOMA" ]; then
    baixado=$(mktemp -d)
    curl -fsSL "https://codeload.github.com/pbakaus/impeccable/tar.gz/$IMPECCABLE_COMMIT" \
      | tar -xz --no-same-owner -C "$baixado" || erro "não consegui baixar o Impeccable do GitHub"
    r=$baixado/impeccable-$IMPECCABLE_COMMIT
    install -d -m 755 "$baixado/impeccable"
    cp -r "$r/plugin/skills/impeccable/SKILL.md" "$r/plugin/skills/impeccable/reference" "$r/LICENSE" "$r/NOTICE.md" \
      "$baixado/impeccable/"
    [ "$(soma_impeccable "$baixado/impeccable")" = "$IMPECCABLE_SOMA" ] \
      || erro "o Impeccable baixado não confere com a versão esperada ($IMPECCABLE_COMMIT)"
    cat > "$baixado/impeccable/ORIGEM.md" <<EOF
# Origem desta cópia

- Fonte: https://github.com/pbakaus/impeccable (Apache-2.0), commit $IMPECCABLE_COMMIT (versão 4.6.0).
- Só o texto: SKILL.md, reference/, LICENSE e NOTICE.md. Ficaram de fora o lançador (scripts/, que
  baixa um binário), os hooks do plugin e a telemetria; o SKILL.md segue sem o lançador e lê
  PRODUCT.md e DESIGN.md direto.
- Instalado pelo instalador da Atena (ATENA_CLAUDE_SKILLS=sim).
EOF
    rm -rf "$imp"
    install -d -m 755 "$L/skills"
    mv "$baixado/impeccable" "$imp"
    chown -R root:root "$imp"
    chmod -R u=rwX,go=rX "$imp"
    rm -rf "$baixado"
  fi
  ok "skills do Claude Code: catálogo, Impeccable, atena-tela e servidores de linguagem"
fi

# com Tailscale, os apps publicados ganham o link de fora de casa. O polkit deixa o executor iniciar só
# as unidades atena-lab-tailscale-on@/off@<porta>
if [ "$ATENA_TAILSCALE" = sim ]; then
  NEEDRESTART_SUSPEND=1 apt-get install -y -qq polkitd >/dev/null
  for u in atena-lab-tailscale-on@.service atena-lab-tailscale-off@.service; do
    instalar_arquivo "$RAIZ/host/systemd/$u" "/etc/systemd/system/$u"
  done
  instalar_arquivo "$RAIZ/host/polkit/50-atena-lab-tailscale.rules" /etc/polkit-1/rules.d/50-atena-lab-tailscale.rules
  ok "apps do lab também fora de casa (Tailscale Serve, só na sua tailnet)"
fi

# o seu Claude Code em /srv/lab: o mesmo sandbox, mais o guarda de escopo
install -d -m 755 -o "$ADMIN" -g "$ADMIN" /srv/lab/.claude /srv/lab/.claude/hooks
for par in "lab-interativo.json settings.json" "guarda_escopo.py hooks/guarda_escopo.py"; do
  read -r de para <<< "$par"
  if [ -f "/srv/lab/.claude/$para" ] && ! cmp -s "$RAIZ/host/lab/$de" "/srv/lab/.claude/$para"; then
    cp -a "/srv/lab/.claude/$para" "/srv/lab/.claude/$para.antes-atena-$(date +%Y%m%d%H%M%S)"
    aviso "/srv/lab/.claude/$para já existia; cópia guardada ao lado"
  fi
  install -m 644 -o "$ADMIN" -g "$ADMIN" "$RAIZ/host/lab/$de" "/srv/lab/.claude/$para"
done
ok "lab interativo: rode claude dentro de /srv/lab (sandbox e guarda de escopo)"

systemctl daemon-reload
systemctl enable --now atena-claude.path atena-lab-lixeira.timer >/dev/null 2>&1
systemctl restart atena-executor.service   # grupos e pastas novas do lab
sleep 1
systemctl is-active --quiet atena-executor || erro "o executor não subiu: journalctl -u atena-executor"
systemctl is-active --quiet atena-claude.path || erro "a fila do Claude Code não subiu: journalctl -u atena-claude.path"
ok "fila do Claude Code no ar (atena-claude.path)"
if [ "$ATENA_CLAUDE_SKILLS" = sim ]; then   # os plugins e o Impeccable nas contas que já têm login
  atena-claude-conta skills | sed 's/^/    /'
fi

# a Atena no lab, se ela estiver instalada: a habilidade, as ações no token, e os projetos no terminal
# dela (mesmo caminho do servidor e do Claude Code), com escrita por ACL
D=/srv/agents/hermes
S=/opt/atena/stacks/agents/hermes
if [ -d "$D" ] && id hermes >/dev/null 2>&1; then
  install -d -m 755 -o hermes -g atena-acoes "$D/skills/atena/lab"
  install -m 644 -o hermes -g atena-acoes "$RAIZ/hermes/skills/atena/lab/SKILL.md" "$D/skills/atena/lab/SKILL.md"
  install -m 644 -o hermes -g atena-acoes "$RAIZ/host/lab/gitconfig-atena" "$D/.gitconfig"
  lab=claude.tarefa,claude.trabalhos,claude.perguntas,claude.responder,claude.cancelar
  lab=$lab,app.publicar,app.parar,app.reiniciar,app.cancelar,app.apagar,app.restaurar,app.comando,app.lista
  token_atena "" "$lab" app.publicar,app.apagar
  setfacl -R -m u:hermes:rwX /srv/lab/projetos
  find /srv/lab/projetos -type d -exec setfacl -m d:u:hermes:rwX,d:u:atena-claude:rwX,d:g:atena-lab:rwX {} +
  instalar_arquivo "$RAIZ/host/lab/hermes-compose.override.yaml" "$S/compose.override.yaml"
  chown "$ADMIN:$ADMIN" "$S/compose.override.yaml"
  ( cd "$S" && docker compose up -d --quiet-pull >/dev/null 2>&1 ) || erro "o Hermes não subiu com os projetos do lab (cd $S && docker compose up)"
  ok "Atena no lab: habilidade lab, ações no token e /srv/lab/projetos no terminal dela"
fi
