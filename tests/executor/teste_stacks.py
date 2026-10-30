"""Stacks de apps pela Atena: editar com foto, conferir as regras da zona e desfazer, com pastas temporárias.
As regras do compose usam o docker compose config de verdade (não precisa de container rodando)."""
import os
import shutil
import subprocess

from comum import carregar, confere, erro, fim, ligar, pedir, token

ex, tmp = carregar()
c = {"cliente": "hermes", "zonas": ["apps", "ai", "agents", "lab", "core"], "acoes": []}
sem_apps = {**c, "zonas": ["ai", "agents", "lab", "core"]}
confere("ações registradas, sem aprovação", all(ex.ACOES[n][2] is None for n in ("stack.editar", "stack.fotos", "stack.desfazer")))
confere("pedido aceita até 1 MB (o arquivo inteiro vai no corpo)", ex.LIMITE_PEDIDO == 1024 * 1024)

with open(ex.CONF, "w") as f:
    f.write("ATENA_LAN_IP=192.168.0.10\n")


def escreve(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "wb" if isinstance(texto, bytes) else "w") as f:
        f.write(texto)


def le(caminho):
    with open(caminho) as f:
        return f.read()


st = f"{tmp}/stacks"
ex.STACKS, ex.DADOS_ZONAS, ex.FOTOS = st, f"{tmp}/srv", f"{tmp}/fotos"
pasta = f"{st}/apps/loja"
os.makedirs(f"{tmp}/srv/apps/loja")
escreve(f"{pasta}/app/Dockerfile", "FROM alpine\n")
escreve(f"{pasta}/app/index.js", "console.log('oi')\n")
escreve(f"{pasta}/.env", "SENHA=x\n")
escreve(f"{st}/core/ntfy/compose.yaml", "services: {}\n")
escreve(f"{st}/core/ntfy/.env", "TOKEN=segredo\n")
escreve(f"{pasta}/compose.yaml", f"""\
services:
  loja:
    build: ./app
    image: atena-apps/loja:1
    container_name: teste-loja
    cgroup_parent: atena-apps.slice
    security_opt: ["no-new-privileges:true"]
    volumes:
      - {tmp}/srv/apps/loja:/data
    ports:
      - "192.168.0.10:3999:3000"
    networks: [zone]
networks:
  zone:
    name: zone-apps
    external: true
""")
confere("compose de base passa nas regras", ex.conferir_stack("apps", "loja", pasta) == [], ex.conferir_stack("apps", "loja", pasta))
inode = os.stat(f"{pasta}/compose.yaml").st_ino
r = ex.acao_stack_editar(c, {"stack": "loja", "arquivo": "compose.yaml",
                             "trocar": [{"de": '"192.168.0.10:3999:3000"', "para": '"192.168.0.10:3998:3000"'}]})
confere("editar com trocar: grava e tira foto", r["mudou"] and r["foto"] and "3998" in le(f"{pasta}/compose.yaml"), r)
confere("editar: mesmo inode (bind mount de arquivo único continua valendo)", os.stat(f"{pasta}/compose.yaml").st_ino == inode)
confere("fotos: 1 edição guardada", [f["arquivo"] for f in ex.acao_stack_fotos(c, {"stack": "loja"})["fotos"]] == ["compose.yaml"])
confere("trecho que não existe: 400", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "compose.yaml",
                                                                     "trocar": [{"de": "nao existe", "para": "x"}]})[0] == 400)
confere("trecho repetido: 400", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "compose.yaml",
                                                               "trocar": [{"de": "loja", "para": "x"}]})[0] == 400)
confere("sem conteudo nem trocar: 400", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "compose.yaml"})[0] == 400)
r = ex.acao_stack_editar(c, {"stack": "loja", "arquivo": "compose.yaml", "conteudo": le(f"{pasta}/compose.yaml")})
confere("conteúdo igual: não muda nem tira foto", r["mudou"] is False and len(ex.fotos_da_stack("loja")) == 1, r)

# --- regras da zona: nada grava, e a foto some ---
BOM = le(f"{pasta}/compose.yaml")
RUINS = {
    "privileged": ("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    privileged: true\n"),
    "cap_add": ("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    cap_add: [SYS_ADMIN]\n"),
    "network_mode host": ("    networks: [zone]\n", "    network_mode: host\n"),
    "pid host": ("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    pid: host\n"),
    "pasta do host /etc": (f"      - {tmp}/srv/apps/loja:/data\n", f"      - {tmp}/srv/apps/loja:/data\n      - /etc:/host-etc\n"),
    "socket do Docker": (f"      - {tmp}/srv/apps/loja:/data\n", f"      - {tmp}/srv/apps/loja:/data\n      - /run/docker.sock:/run/docker.sock\n"),
    "pasta de outra stack": (f"      - {tmp}/srv/apps/loja:/data\n", f"      - {tmp}/srv/apps/loja:/data\n      - ../../core/ntfy:/ntfy\n"),
    "rede de outra zona": ("    name: zone-apps\n", "    name: zone-core\n"),
    "porta sem IP": ('"192.168.0.10:3998:3000"', '"3998:3000"'),
    "porta em 0.0.0.0": ('"192.168.0.10:3998:3000"', '"0.0.0.0:3998:3000"'),
    "sem cgroup_parent": ("    cgroup_parent: atena-apps.slice\n", ""),
    "security_opt unconfined": ('["no-new-privileges:true"]', '["seccomp=unconfined"]'),
    "env_file de outra stack": ("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    env_file: ../../core/ntfy/.env\n"),
    "label_file de outra stack": ("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    label_file: ../../core/ntfy/.env\n"),
    "build fora da stack": ("    build: ./app\n", "    build: ../../core/ntfy\n"),
    "build com rede do host": ("    build: ./app\n", "    build:\n      context: ./app\n      network: host\n"),
    "volumes_from": ("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    volumes_from: [litellm-db]\n"),
    "devices": ("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    devices: [/dev/sda]\n"),
    "use_api_socket": ("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    use_api_socket: true\n"),
    "YAML quebrado": ("services:\n", "services:\n  - [\n"),
    # construir com o nome da imagem de outra stack troca a imagem dela na próxima recriação
    "build com a imagem do LiteLLM": ("    image: atena-apps/loja:1\n", "    image: ghcr.io/berriai/litellm:v1.101.6\n"),
    "build com a imagem do painel": ("    image: atena-apps/loja:1\n", "    image: atena/painel:0.14.1\n"),
    "build com a imagem de outra stack de apps": ("    image: atena-apps/loja:1\n", "    image: atena-apps/lojinha:1\n"),
    "build sem image": ("    image: atena-apps/loja:1\n", ""),
    "build.tags": ("    build: ./app\n", '    build:\n      context: ./app\n      tags: ["ghcr.io/berriai/litellm:v1.101.6"]\n'),
    "build.cache_to": ("    build: ./app\n", '    build:\n      context: ./app\n      cache_to: ["type=local,dest=/etc/x"]\n'),
    "sem build, com a imagem local do painel": ("    build: ./app\n    image: atena-apps/loja:1\n",
                                                "    image: docker.io/atena/painel:0.14.1\n"),
}
for nome, (de, para) in RUINS.items():
    fotos_antes = len(ex.fotos_da_stack("loja"))
    status, msg = erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "compose.yaml", "trocar": [{"de": de, "para": para}]})
    confere(f"compose com {nome}: 422 e o arquivo fica como estava", status == 422 and le(f"{pasta}/compose.yaml") == BOM
            and len(ex.fotos_da_stack("loja")) == fotos_antes, f"{status} {msg}")

BONS = {
    "build com atena-apps/loja-<algo>": ("    image: atena-apps/loja:1\n", "    image: atena-apps/loja-web:2\n"),
    "sem build, imagem de registro": ("    build: ./app\n    image: atena-apps/loja:1\n", "    image: nginx:1.29-alpine\n"),
}
for nome, (de, para) in BONS.items():
    r = ex.acao_stack_editar(c, {"stack": "loja", "arquivo": "compose.yaml", "trocar": [{"de": de, "para": para}]})
    confere(f"compose com {nome}: passa", r["mudou"], r)
    ex.acao_stack_desfazer(c, {"stack": "loja"})
confere("e o desfazer deixa o compose como era", le(f"{pasta}/compose.yaml") == BOM)

VOLUME = BOM + "volumes:\n  dados:\n    driver: local\n    driver_opts: {type: none, o: bind, device: /etc}\n"
VOLUME = VOLUME.replace(f"      - {tmp}/srv/apps/loja:/data\n", f"      - {tmp}/srv/apps/loja:/data\n      - dados:/dados\n")
status, msg = erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "compose.yaml", "conteudo": VOLUME})
confere("volume com driver_opts (bind disfarçado): 422", status == 422 and le(f"{pasta}/compose.yaml") == BOM, msg)
status, msg = erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "compose.yaml", "conteudo": VOLUME.replace(
    "    driver: local\n    driver_opts: {type: none, o: bind, device: /etc}\n", "    external: true\n    name: litellm_db\n")})
confere("volume externo (de outra stack): 422", status == 422, msg)
status, msg = erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "compose.override.yaml",
                                             "conteudo": "services:\n  loja:\n    privileged: true\n"})
confere("override com privileged: 422 e o arquivo novo some", status == 422 and not os.path.exists(f"{pasta}/compose.override.yaml"), msg)
escreve(f"{pasta}/extra/coisa.yaml", "services: {}\n")
escreve(f"{pasta}/compose.yaml", BOM.replace("services:\n", "include: [extra/coisa.yaml]\nservices:\n", 1))
status, msg = erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "extra/coisa.yaml",
                                             "conteudo": "services:\n  outro:\n    image: alpine\n    privileged: true\n"})
confere("arquivo incluído pelo compose também é conferido: 422", status == 422 and le(f"{pasta}/extra/coisa.yaml") == "services: {}\n", msg)
escreve(f"{pasta}/compose.yaml", BOM)
shutil.rmtree(f"{pasta}/extra")

# --- o que nunca se edita ---
confere(".env: 403", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": ".env", "conteudo": "X=1"})[0] == 403)
confere("sair da pasta com ../: 400", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "../../core/ntfy/compose.yaml", "conteudo": "x"})[0] == 400)
confere("caminho absoluto: 400", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": f"{pasta}/compose.yaml", "conteudo": "x"})[0] == 400)
os.symlink(f"{st}/core/ntfy", f"{pasta}/atalho")
confere("atalho para fora da pasta: 400", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "atalho/compose.yaml", "conteudo": "x"})[0] == 400)
os.unlink(f"{pasta}/atalho")
confere("dentro de node_modules: 400", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "app/node_modules/x.js", "conteudo": "x"})[0] == 400)
escreve(f"{pasta}/app/logo.png", b"\x89PNG\0\0")
confere("arquivo binário: 400", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "app/logo.png", "conteudo": "x"})[0] == 400)
confere("stack de outra zona (core): 404", erro(ex.acao_stack_editar, c, {"stack": "ntfy", "arquivo": "compose.yaml", "conteudo": "x"})[0] == 404)
confere("nome de stack inválido: 400", erro(ex.acao_stack_editar, c, {"stack": "../core", "arquivo": "compose.yaml", "conteudo": "x"})[0] == 400)
confere("sem a zona apps: 403", erro(ex.acao_stack_editar, sem_apps, {"stack": "loja", "arquivo": "compose.yaml", "conteudo": "x"})[0] == 403)
CHAVE = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIabc\n"   # em pedaços: o teste não pode parecer um vazamento
confere("chave privada no conteúdo: 403", erro(ex.acao_stack_editar, c, {"stack": "loja", "arquivo": "app/k.txt", "conteudo": CHAVE})[0] == 403)

# --- desfazer ---
r = ex.acao_stack_editar(c, {"stack": "loja", "arquivo": "app/src/novo.js", "conteudo": "export const x = 1\n"})
confere("arquivo novo em pasta nova (sem conferir compose: não é YAML)", r["mudou"] and os.path.isfile(f"{pasta}/app/src/novo.js"), r)
r = ex.acao_stack_desfazer(c, {"stack": "loja"})
confere("desfazer arquivo novo: ele some", r["removido"] and not os.path.exists(f"{pasta}/app/src/novo.js"), r)
r = ex.acao_stack_desfazer(c, {"stack": "loja"})
confere("desfazer a troca de porta: volta como era", r["voltou"] == "compose.yaml" and "3999" in le(f"{pasta}/compose.yaml")
        and r["fotos_restantes"] == 0, r)
confere("nada para desfazer: 404", erro(ex.acao_stack_desfazer, c, {"stack": "loja"})[0] == 404)
ids = [ex.acao_stack_editar(c, {"stack": "loja", "arquivo": "app/index.js", "conteudo": f"// {n}\n"})["foto"] for n in (1, 2, 3)]
ex.acao_stack_desfazer(c, {"stack": "loja", "foto": ids[0]})
confere("desfazer uma foto escolhida: volta àquela versão", le(f"{pasta}/app/index.js") == "console.log('oi')\n"
        and [f["foto"] for f in ex.fotos_da_stack("loja")] == [ids[2], ids[1]])
confere("foto que não existe: 404", erro(ex.acao_stack_desfazer, c, {"stack": "loja", "foto": "19990101-000000-000000"})[0] == 404)
escreve(f"{pasta}/compose.yaml", BOM.replace("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    privileged: true\n"))
ex.acao_stack_editar(c, {"stack": "loja", "arquivo": "compose.yaml", "conteudo": BOM})   # a foto guarda o mexido à mão
ex.acao_stack_editar(c, {"stack": "loja", "arquivo": "app/index.js", "conteudo": "// 4\n"})
ex.acao_stack_desfazer(c, {"stack": "loja"})
r = ex.acao_stack_desfazer(c, {"stack": "loja"})
confere("desfazer para um compose fora das regras (mexido à mão): volta e avisa", "privileged" in r.get("aviso", ""), r)
escreve(f"{pasta}/compose.yaml", BOM)
ex.MAX_FOTOS = 3
for i in range(5):
    ex.acao_stack_editar(c, {"stack": "loja", "arquivo": "app/index.js", "conteudo": f"// v{i}\n"})
confere("guarda no máximo MAX_FOTOS por stack", len(ex.fotos_da_stack("loja")) == 3)
confere("fotos ficam só para o executor (600)", all(oct(os.stat(os.path.join(ex.FOTOS, "loja", n)).st_mode & 0o777) == "0o600"
                                                    for n in os.listdir(f"{ex.FOTOS}/loja")))

# --- aplicar: o docker compose up é falso; o config é o de verdade ---
confere("stack.aplicar vira pedido (roda em segundo plano)", ex.ACOES["stack.aplicar"][2] is not None)
ex.PEDIDOS = f"{tmp}/pedidos.json"
RUN, DORMIR = ex.subprocess.run, ex.time.sleep
SUBIDAS, SAIDA_UP = [], {"codigo": 0, "texto": ""}


def run_falso(argv, **kw):
    if "up" in argv:
        SUBIDAS.append((argv, kw.get("cwd")))
        return subprocess.CompletedProcess(argv, SAIDA_UP["codigo"], SAIDA_UP["texto"], "")
    return RUN(argv, **kw)


ex.subprocess.run, ex.time.sleep = run_falso, lambda s: None
ex.containers = lambda: [{"stack": "loja", "container": "teste-loja", "estado": "running", "status": "Up 3 seconds", "zona": "apps"}]


def esperar(p):
    for _ in range(100):
        if p["estado"] != "executando":
            break
        DORMIR(0.05)
    return p


def aplicar(params):
    titulo, _ = ex.preparar_stack_aplicar(c, params)
    p = ex.criar_pedido(c, "stack.aplicar", params, "teste", titulo)
    ex.mudar(p, estado="executando")
    confere("aplicar responde na hora (segue em segundo plano)", ex.executar(p) is None)
    return esperar(p)


p = aplicar({"stack": "loja"})
confere("aplicar: compose up -d --build na pasta da stack, com o nome do projeto",
        p["estado"] == "concluido" and SUBIDAS[-1] == (["docker", "compose", "-p", "loja", "up", "-d", "--build", "--remove-orphans"], pasta)
        and p["resultado"]["containers"][0]["container"] == "teste-loja" and "problema" not in p["resultado"], (p, SUBIDAS[-1:]))
SAIDA_UP.update(codigo=1, texto="Error: build failed\nSENHA=hunter2\n")
p = aplicar({"stack": "loja"})
confere("aplicar que falha: pedido falhou, com o registro e sem segredo", p["estado"] == "falhou" and "build failed" in p["erro"]
        and "hunter2" not in p["erro"] and "stack.desfazer" in p["erro"], p.get("erro"))
SAIDA_UP.update(codigo=0, texto="")
escreve(f"{pasta}/compose.yaml", BOM.replace("    cgroup_parent: atena-apps.slice\n", "    cgroup_parent: atena-apps.slice\n    privileged: true\n"))
confere("aplicar com compose fora das regras (mexido à mão): 422", erro(ex.preparar_stack_aplicar, c, {"stack": "loja"})[0] == 422)
escreve(f"{pasta}/compose.yaml", BOM)
ex.APLICANDO.add("loja")
confere("aplicar duas vezes a mesma stack: 409", erro(ex.preparar_stack_aplicar, c, {"stack": "loja"})[0] == 409)
ex.APLICANDO.discard("loja")
preso = ex.criar_pedido(c, "stack.aplicar", {"stack": "loja"}, "teste", "aplicar a stack loja")
ex.mudar(preso, estado="executando")
ex.pedidos_interrompidos()
confere("executor que reiniciou no meio: pedido vira falhou", preso["estado"] == "falhou" and "reiniciou" in preso["erro"], preso)

# pelo socket: 202 com o pedido, e o GET /pedido?esperar devolve o resultado
servidor = ligar(ex)
hermes = token(ex, "hermes", ["stack.aplicar"], ["apps"], aprovar=[])
status, r = pedir(ex, "POST", "/acao/stack.aplicar", hermes, {"params": {"stack": "loja"}})
confere("pelo socket: 202 em andamento, com o pedido", status == 202 and r["estado"] in ("executando", "concluido") and r["pedido"], r)
status, r = pedir(ex, "GET", f"/pedido/{r['pedido']}?esperar=5", hermes)
confere("GET /pedido?esperar traz o resultado do compose up", status == 200 and r["pedido"]["estado"] == "concluido"
        and r["pedido"]["resultado"]["aplicado"] == "loja", r)
servidor.shutdown()
ex.subprocess.run, ex.time.sleep = RUN, DORMIR

fim()
