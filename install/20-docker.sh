# Etapa 20: Docker do repositório oficial, já com a configuração da Atena.

msg "Instalando o Docker (repositório oficial)"
. /etc/os-release

install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $VERSION_CODENAME
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

# a configuração entra antes de o Docker subir pela primeira vez;
# se já existir, só as chaves da Atena são atualizadas (o runtime da NVIDIA, por exemplo, fica)
install -d -m 0755 /etc/docker
python3 - "$RAIZ/host/docker/daemon.json" /etc/docker/daemon.json <<'EOF'
import json, os, sys
modelo, destino = sys.argv[1], sys.argv[2]
atual = json.load(open(destino)) if os.path.exists(destino) else {}
atual.update(json.load(open(modelo)))
json.dump(atual, open(destino, "w"), indent=2)
EOF

apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
systemctl restart docker
usermod -aG docker "$ATENA_ADMIN_USER"
ok "$(docker --version)"
ok "$ATENA_ADMIN_USER no grupo docker (vale a partir do próximo login)"
