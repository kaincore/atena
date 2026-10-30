# Etapa 88 (só com --lab): o lab do Claude Code. O usuário atena-claude (sem sudo, sem Docker) roda os
# trabalhos que a Atena pede ao executor, em /srv/lab/projetos, no sandbox do Claude Code; os pedidos
# de permissão e as perguntas vão ao celular. Os apps prontos vão para a zona lab (app.publicar). Com as
# skills, também as receitas de estilo: o coletor (um container sem IA, na rede lab-coletor) abre o site
# e o Claude Code escreve a receita em /srv/lab/receitas.
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

# o Node do lab, numa versão fixa, do nodejs.org e conferido pelo checksum guardado aqui. O Claude Code do
# lab usa ele na frente do Node do sistema (o do Ubuntu fica como está), e o REA das receitas pede
# 22.23.4+ ou 24.22.1+. Para trocar, mude a versão e as duas somas (SHASUMS256.txt da versão nova).
NODE_LAB=24.22.1
case "$(uname -m)" in
  x86_64) node_plataforma=linux-x64; node_soma=6c172a9ab6718f7b801fb5a7bd486af2ee5e32758086a04b84fcce2aa77095e6 ;;
  aarch64) node_plataforma=linux-arm64; node_soma=dbabf7a1cbf947e6059ffad2c27b80041db97dea1e553b62afdee7f13fca336e ;;
  *) erro "o Node do lab não tem versão para $(uname -m)" ;;
esac
if [ "$("$L/node/bin/node" --version 2>/dev/null)" != "v$NODE_LAB" ]; then
  baixado=$(mktemp -d)
  curl -fsSL -o "$baixado/node.tar.xz" "https://nodejs.org/dist/v$NODE_LAB/node-v$NODE_LAB-$node_plataforma.tar.xz" \
    || erro "não consegui baixar o Node $NODE_LAB do nodejs.org"
  echo "$node_soma  $baixado/node.tar.xz" | sha256sum -c --quiet - \
    || erro "o Node baixado não confere com o checksum oficial da versão $NODE_LAB"
  install -d -m 755 "$baixado/node"
  tar -xJf "$baixado/node.tar.xz" -C "$baixado/node" --strip-components=1 --no-same-owner
  chown -R root:root "$baixado/node"
  chmod -R u=rwX,go=rX "$baixado/node"
  rm -rf "$L/node.antes"
  if [ -d "$L/node" ]; then mv "$L/node" "$L/node.antes"; fi
  mv "$baixado/node" "$L/node"
  rm -rf "$L/node.antes" "$baixado"
fi
ok "Node $NODE_LAB do lab em $L/node"

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
COLETOR=atena/coletor:1.0.0   # a imagem do coletor das receitas (a mesma do receitas.py do executor)
# os descompiladores do REA, nas versões que o rea-agents 6.8.0 espera (o Ghidra pelo SHA-256 da página da
# versão no GitHub da NSA; a ponte do JADX pelo SHA-256 que o próprio REA fixa)
GHIDRA_VERSAO=12.1.4
GHIDRA_ZIP=ghidra_12.1.4_PUBLIC_20260921.zip
GHIDRA_SOMA=ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db
JADX_PONTE=0.7.1
JADX_SOMA=6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75
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
  ( cd "$F" && PATH="$L/node/bin:$PATH" npm ci --ignore-scripts --no-audit --no-fund --loglevel=error >/dev/null ) \
    || erro "não consegui instalar as ferramentas do lab (cd $F && npm ci)"
  # o Chromium sem tela e as bibliotecas do Ubuntu que ele usa
  NEEDRESTART_SUSPEND=1 DEBIAN_FRONTEND=noninteractive PLAYWRIGHT_BROWSERS_PATH="$F/navegadores" \
    "$L/node/bin/node" "$F/node_modules/playwright-core/cli.js" install --with-deps --only-shell chromium >/dev/null 2>&1 \
    || erro "não consegui instalar o Chromium sem tela do atena-tela"
  install -m 644 "$RAIZ/host/lab/tela.js" "$F/tela.js"
  install -m 755 "$RAIZ/host/lab/atena-tela" "$F/bin/atena-tela"
  install -m 755 "$RAIZ/host/lab/rea" "$F/bin/rea"
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

  # receitas de estilo: a skill receita (vai para as contas com as outras), o REA (nas ferramentas, acima),
  # a pasta das receitas prontas (só o executor escreve; o trabalhador lê pelo grupo) e o coletor: a
  # imagem e a rede dele, que alcança a internet e não a rede de casa nem o servidor (atena-docker-firewall
  # barra as redes privadas de toda ponte br-*), sem conversa entre containers
  install -d -m 755 "$L/skills/receita"
  install -m 644 "$RAIZ/host/lab/skills/receita/SKILL.md" "$L/skills/receita/SKILL.md"
  install -d -m 2750 -o atena-exec -g atena-lab /srv/lab/receitas
  if ! docker network inspect lab-coletor >/dev/null 2>&1; then
    docker network create --driver bridge --subnet 10.10.41.0/24 -o com.docker.network.bridge.name=br-coletor \
      -o com.docker.network.bridge.enable_icc=false -o com.docker.network.bridge.host_binding_ipv4=127.0.0.1 \
      lab-coletor >/dev/null || erro "não consegui criar a rede lab-coletor"
  fi
  if ! docker image inspect "$COLETOR" >/dev/null 2>&1; then
    docker build -q -t "$COLETOR" "$RAIZ/host/lab/coletor" >/dev/null \
      || erro "não consegui construir o coletor das receitas (docker build -t $COLETOR $RAIZ/host/lab/coletor)"
  fi
  ok "receitas de estilo: skill receita, REA, $COLETOR na rede lab-coletor e /srv/lab/receitas"

  # receitas de programas: os descompiladores do REA. O JDK 21 e o Apktool vêm do Ubuntu (atualizações de
  # segurança com o resto); o Ghidra e a ponte do JADX, em versões fixas e conferidas. O rea do lab aponta
  # para eles (GHIDRA_INSTALL_DIR, JAVA_HOME, REA_JADX_MCP_JAR, REA_APKTOOL_COMMAND). Os pagos (IDA,
  # Hopper, JEB) ficam de fora. A skill do REA (reverse-engineer-anything, só o texto, do próprio pacote)
  # vai para as contas com as outras.
  NEEDRESTART_SUSPEND=1 apt-get install -y -qq openjdk-21-jdk-headless apktool unzip >/dev/null
  ln -sfn "/usr/lib/jvm/java-21-openjdk-$(dpkg --print-architecture)" "$L/java"
  [ -x "$L/java/bin/javac" ] || erro "o JDK 21 não ficou em $L/java (apt-get install openjdk-21-jdk-headless)"
  if ! grep -qx "application.version=$GHIDRA_VERSAO" "$L/ghidra/Ghidra/application.properties" 2>/dev/null; then
    baixado=$(mktemp -d)
    curl -fsSL -o "$baixado/ghidra.zip" \
      "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSAO}_build/$GHIDRA_ZIP" \
      || erro "não consegui baixar o Ghidra $GHIDRA_VERSAO do GitHub"
    echo "$GHIDRA_SOMA  $baixado/ghidra.zip" | sha256sum -c --quiet - \
      || erro "o Ghidra baixado não confere com o SHA-256 da versão $GHIDRA_VERSAO"
    unzip -q "$baixado/ghidra.zip" -d "$baixado"
    chown -R root:root "$baixado/ghidra_${GHIDRA_VERSAO}_PUBLIC"
    chmod -R u=rwX,go=rX "$baixado/ghidra_${GHIDRA_VERSAO}_PUBLIC"
    rm -rf "$L/ghidra.antes"
    if [ -d "$L/ghidra" ]; then mv "$L/ghidra" "$L/ghidra.antes"; fi
    mv "$baixado/ghidra_${GHIDRA_VERSAO}_PUBLIC" "$L/ghidra"
    rm -rf "$L/ghidra.antes" "$baixado"
  fi
  install -d -m 755 "$F/jadx"
  jadx=$F/jadx/jadx-headless-mcp-$JADX_PONTE-all.jar
  if ! echo "$JADX_SOMA  $jadx" | sha256sum -c --quiet - 2>/dev/null; then
    curl -fsSL -o "$jadx.novo" \
      "https://github.com/1013503897/jadx-headless-mcp/releases/download/v$JADX_PONTE/jadx-headless-mcp-$JADX_PONTE-all.jar" \
      || erro "não consegui baixar a ponte do JADX ($JADX_PONTE) do GitHub"
    echo "$JADX_SOMA  $jadx.novo" | sha256sum -c --quiet - \
      || { rm -f "$jadx.novo"; erro "a ponte do JADX baixada não confere com o SHA-256 que o REA fixa"; }
    chmod 644 "$jadx.novo"
    mv "$jadx.novo" "$jadx"
  fi
  rm -rf "$L/skills/reverse-engineer-anything"
  cp -r "$F/node_modules/rea-agents/skills/reverse-engineer-anything" "$L/skills/reverse-engineer-anything"
  chown -R root:root "$L/skills/reverse-engineer-anything"
  chmod -R u=rwX,go=rX "$L/skills/reverse-engineer-anything"
  ok "descompiladores do REA: Ghidra $GHIDRA_VERSAO (JDK 21), JADX (ponte $JADX_PONTE), Apktool e a skill do REA"
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
  # as ações do lab para a Atena (o perfil atena-lab no catálogo). Publicar um app pede o celular (ele
  # fica na rede de casa); apagar também, por ser destrutivo
  token_atena "" "$(atena-executor acoes atena-lab)" app.publicar
  setfacl -R -m u:hermes:rwX /srv/lab/projetos
  find /srv/lab/projetos -type d -exec setfacl -m d:u:hermes:rwX,d:u:atena-claude:rwX,d:g:atena-lab:rwX {} +
  instalar_arquivo "$RAIZ/host/lab/hermes-compose.override.yaml" "$S/compose.override.yaml"
  chown "$ADMIN:$ADMIN" "$S/compose.override.yaml"
  ( cd "$S" && docker compose up -d --quiet-pull >/dev/null 2>&1 ) || erro "o Hermes não subiu com os projetos do lab (cd $S && docker compose up)"
  # a ronda lê a habilidade lab também (as linhas do Claude Code)
  id=$(ronda_id)
  if [ -n "$id" ]; then
    docker exec -u hermes hermes hermes cron edit "$id" --prompt "$RONDA" --skill servidor-atena --skill lab >/dev/null \
      || aviso "não consegui pôr a habilidade lab na ronda (docker exec -u hermes hermes hermes cron list)"
  fi
  ok "Atena no lab: habilidade lab, ações no token e /srv/lab/projetos no terminal dela"
fi
