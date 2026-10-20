"""Publicar apps do lab com o Docker simulado: validação, porta, compose com as travas, falhas,
parar, lista, o link do Tailscale (ligado e desligado no atena.conf) e app.comando."""
import os
import subprocess

from comum import confere, erro as erro_ex, executor, fim

ex, tmp, _ = executor(contas="pessoal", prontas=("pessoal",))
ex.log = lambda **campos: None
ex.time.sleep = lambda s: None
os.makedirs(f"{ex.PROJETOS_LAB}/lista-compras")
with open(f"{ex.PROJETOS_LAB}/lista-compras/Dockerfile", "w") as f:
    f.write("FROM python:3.14-slim\n")
os.makedirs(f"{ex.PROJETOS_LAB}/sem-docker")

CHAMADAS, CENARIO = [], {"up": 0, "atende": True, "ss": "LISTEN 0 4096 0.0.0.0:8000 0.0.0.0:*\n"}


def rodar_falso(argv, tempo=30, cancelavel=None):
    CHAMADAS.append(argv)
    if argv[:1] == ["ss"]:
        return 0, CENARIO["ss"]
    if "up" in argv:
        return CENARIO["up"], "erro: pip install falhou" if CENARIO["up"] else "Started"
    if argv[:2] == ["docker", "logs"]:
        return 0, "Traceback: ouvindo em 127.0.0.1"
    if argv[:2] == ["docker", "ps"]:
        return 0, "lab-lista-compras\t/x\tlab-lista-compras\trunning\tUp 2 minutes\tzone-lab\n"
    return 0, ""


def conexao_falsa(endereco, timeout=None):
    if CENARIO["atende"]:
        class S:
            def close(self):
                pass
        return S()
    raise OSError("recusada")


ex.rodar = rodar_falso
ex.socket.create_connection = conexao_falsa

if hasattr(ex, "link_tailscale"):   # etapa 4: o link do Tailscale não sai do teste
    ex.link_tailscale = lambda porta, ligar: ((f"https://teste.ts.net:{porta}" if ligar else None), None)
    ex.portas_no_tailscale = lambda: set()
    ex.tailscale_host = lambda: None
def erro(funcao, *args):
    return erro_ex(ex, funcao, *args)


hermes = {"cliente": "hermes", "zonas": ["apps", "ai", "agents", "lab", "core"], "acoes": [], "aprovar": ["app.publicar"]}
sem_lab = {"cliente": "painel", "zonas": ["apps"], "acoes": []}

confere("app.publicar pede aprovação no celular", ex.precisa_aprovacao(hermes, "app.publicar"))
confere("app.parar e app.lista rodam direto", ex.ACOES["app.parar"][2] is None and ex.ACOES["app.lista"][2] is None)
confere("fora da zona lab: 403", erro(ex.preparar_app_publicar, sem_lab, {"projeto": "lista-compras"})[0] == 403)
confere("projeto com caminho: 400", erro(ex.preparar_app_publicar, hermes, {"projeto": "../x"})[0] == 400)
confere("projeto inexistente: 404", erro(ex.preparar_app_publicar, hermes, {"projeto": "nada"})[0] == 404)
status, msg = erro(ex.preparar_app_publicar, hermes, {"projeto": "sem-docker"})
confere("sem Dockerfile: 409 explicando o que pedir ao Claude Code", status == 409 and "Dockerfile" in msg)
confere("porta fora da faixa: 400", erro(ex.preparar_app_publicar, hermes, {"projeto": "lista-compras", "porta": 80})[0] == 400)
confere("porta ocupada no servidor: 409", erro(ex.preparar_app_publicar, hermes, {"projeto": "lista-compras", "porta": 8000})[0] == 409)

ex.ESTADO["pedidos"]["aaaa0001"] = {"id": "aaaa0001", "acao": "claude.tarefa", "estado": "executando",
                                    "params": {"projeto": "lista-compras"}, "cliente": "hermes", "criado": 0}
status, msg = erro(ex.preparar_app_publicar, hermes, {"projeto": "lista-compras"})
confere("Claude Code ainda trabalhando no projeto: 409", status == 409 and "aaaa0001" in msg)
ex.ESTADO["pedidos"]["aaaa0001"]["estado"] = "concluido"

params = {"projeto": "lista-compras"}
titulo, texto = ex.preparar_app_publicar(hermes, params)
confere("escolhe a primeira porta livre (8000 ocupada → 8001)", params["porta"] == 8001 and "8001" in titulo, params)


def pedido(params):
    return {"id": "bbbb0001", "zonas": hermes["zonas"], "params": params}


r = ex.acao_app_publicar(pedido(params))
compose = f"{ex.STACKS_LAB}/lab-lista-compras/compose.yaml"
with open(compose) as f:
    texto = f.read()
confere("publicado: endereço na rede de casa", {k: r.get(k) for k in ("endereco", "stack")} == {"endereco": "http://192.168.0.10:8001", "stack": "lab-lista-compras"}, r)
confere("compose na pasta da zona lab, com as travas",
        all(t in texto for t in ['"192.168.0.10:8001:8001"', "cap_drop: [ALL]", "read_only: true",
                                 "no-new-privileges:true", "cgroup_parent: atena-lab.slice", "zone-lab",
                                 f"build: {ex.PROJETOS_LAB}/lista-compras"]))
up = next(c for c in CHAMADAS if "up" in c)
confere("docker compose up --build com o nome da stack", up[:6] == ["docker", "compose", "-f", compose, "-p", "lab-lista-compras"]
        and "--build" in up)

params2 = {"projeto": "lista-compras"}
ex.preparar_app_publicar(hermes, params2)
confere("publicar de novo mantém a porta", params2["porta"] == 8001, params2)

lista = ex.acao_app_lista(hermes, {})
if isinstance(lista, dict):   # etapa 3: projetos + lixeira
    lista = [{"projeto": i["projeto"], "endereco": i["endereco"], "estado": i["app"]}
             for i in lista["projetos"] if i["app"] != "não publicado"]
confere("app.lista mostra endereço e estado", lista == [{"projeto": "lista-compras", "endereco": "http://192.168.0.10:8001",
                                                       "estado": "Up 2 minutes"}], lista)

CENARIO["up"] = 1
status, msg = erro(ex.acao_app_publicar, pedido({"projeto": "lista-compras", "porta": 8001}))
confere("falha na construção: 502 com o fim do registro", status == 502 and "pip install falhou" in msg)
CENARIO["up"], CENARIO["atende"] = 0, False
CHAMADAS.clear()
status, msg = erro(ex.acao_app_publicar, pedido({"projeto": "lista-compras", "porta": 8001}))
confere("app não atende na porta: 502, com log, e tira do ar", status == 502 and "0.0.0.0" in msg
        and "Traceback" in msg and any(c[-1] == "down" for c in CHAMADAS))

r = ex.acao_app_parar(hermes, {"projeto": "lista-compras"})
confere("app.parar faz compose down e mantém o compose", r["parado"] == "lab-lista-compras" and os.path.exists(compose)
        and CHAMADAS[-1][-1] == "down")
confere("parar o que não foi publicado: 404", erro(ex.acao_app_parar, hermes, {"projeto": "sem-docker"})[0] == 404)
confere("app.lista fora da zona lab: 403", erro(ex.acao_app_lista, sem_lab, {})[0] == 403)

confere("sem Tailscale no atena.conf: nada de link de fora de casa", "fora_de_casa" not in r
        and not any(c[:2] == ["systemctl", "start"] for c in CHAMADAS))

# --- com Tailscale: o link liga ao publicar e reiniciar e desliga ao parar ---
ts, tmp_ts, _ = executor(contas="pessoal", prontas=("pessoal",), conf="ATENA_TAILSCALE=sim\n")
os.makedirs(f"{ts.PROJETOS_LAB}/app1")
with open(f"{ts.PROJETOS_LAB}/app1/Dockerfile", "w") as f:
    f.write("FROM x\n")
SERVIDAS, CHAMADAS_TS = {8001}, []


def rodar_ts(argv, tempo=30, cancelavel=None):
    CHAMADAS_TS.append(argv)
    if argv[:2] == ["systemctl", "start"]:
        unidade = argv[-1]
        porta = int(unidade.split("@")[1].split(".")[0])
        (SERVIDAS.add if "-on@" in unidade else SERVIDAS.discard)(porta)
        return 0, ""
    if argv[:2] == ["docker", "ps"]:
        return 0, "lab-app1\t/x\tlab-app1\trunning\tUp 1 minute\tzone-lab\n"
    return 0, ""


ts.rodar = rodar_ts
ts.tailscale_host = lambda: "atena.exemplo.ts.net"
ts.portas_no_tailscale = lambda: set(SERVIDAS)
ts.atende = lambda porta, projeto, segundos=20: True
compose_ts = f"{ts.STACKS_LAB}/lab-app1/compose.yaml"
r = ts.publicar("app1", "lab-app1", f"{ts.PROJETOS_LAB}/app1", compose_ts, 8002)
confere("publicar devolve o link de fora de casa", r.get("fora_de_casa") == "https://atena.exemplo.ts.net:8002"
        and "atena-lab-tailscale-on@8002.service" in CHAMADAS_TS[-1], r)
lista = ts.acao_app_lista(hermes, {})["projetos"]
confere("app.lista mostra o link", lista[0]["fora_de_casa"] == "https://atena.exemplo.ts.net:8002", lista)
ts.acao_app_parar(hermes, {"projeto": "app1"})
confere("parar desliga o link", "atena-lab-tailscale-off@8002.service" in CHAMADAS_TS[-1] and 8002 not in SERVIDAS)
r = ts.acao_app_reiniciar(hermes, {"projeto": "app1"})
confere("reiniciar religa o link", r.get("fora_de_casa") == "https://atena.exemplo.ts.net:8002" and 8002 in SERVIDAS, r)
ts.rodar = lambda argv, tempo=30, cancelavel=None: (1, "Access denied") if argv[:2] == ["systemctl", "start"] else rodar_ts(argv, tempo)
r = ts.publicar("app1", "lab-app1", f"{ts.PROJETOS_LAB}/app1", compose_ts, 8002)
confere("sem o link, o app sobe mesmo assim e diz o motivo", r["endereco"].endswith(":8002")
        and "Access denied" in r["fora_de_casa"], r)

# --- app.comando: roda dentro do app no ar ---
EXEC = []


def rodar_comando(argv, tempo=30, cancelavel=None):
    if argv[:2] == ["docker", "exec"]:
        EXEC.append(argv)
        if "dorme" in argv[-1]:
            raise subprocess.TimeoutExpired(argv, tempo)
        if "nao-tem-sh" in argv[-1]:
            return 127, "exec: \"sh\": executable file not found\n"
        return 0, "arquivos: a b\napi_token: abc123segredo\n"
    return 0, ""


ex.rodar = rodar_comando
ex.containers = lambda: [
    {"stack": "lab-loja", "container": "lab-loja", "estado": "running", "status": "Up 1 hour", "zona": "lab"},
    {"stack": "lab-parado", "container": "lab-parado", "estado": "exited", "status": "Exited (0)", "zona": "lab"},
    {"stack": "outra", "container": "lab-falso", "estado": "running", "status": "Up", "zona": "apps"},
]
r = ex.acao_app_comando(hermes, {"projeto": "loja", "comando": "ls /data"})
confere("texto roda com sh -c dentro do app", EXEC[-1] == ["docker", "exec", "lab-loja", "sh", "-c", "ls /data"], EXEC[-1])
confere("saída com segredos ocultos", r["codigo"] == 0 and "abc123segredo" not in r["saida"] and "arquivos: a b" in r["saida"], r)
ex.acao_app_comando(hermes, {"projeto": "loja", "comando": ["cat", "/data/x.json"], "segundos": 5})
confere("lista vai direto, sem shell", EXEC[-1] == ["docker", "exec", "lab-loja", "cat", "/data/x.json"], EXEC[-1])
r = ex.acao_app_comando(hermes, {"projeto": "loja", "comando": "nao-tem-sh"})
confere("app sem sh: dica de mandar como lista", r["codigo"] == 127 and "lista" in r.get("dica", ""), r)
for nome, params, status in [
        ("comando inválido", {"projeto": "loja", "comando": 5}, 400), ("lista vazia", {"projeto": "loja", "comando": []}, 400),
        ("segundos fora de 1-120", {"projeto": "loja", "comando": "x", "segundos": 500}, 400),
        ("comando grande demais", {"projeto": "loja", "comando": "x" * 4001}, 400),
        ("projeto inválido", {"projeto": "Loja;rm", "comando": "x"}, 400),
        ("app não publicado", {"projeto": "nada", "comando": "x"}, 404),
        ("container lab-* de outra stack ou zona", {"projeto": "falso", "comando": "x"}, 404),
        ("app parado", {"projeto": "parado", "comando": "x"}, 409),
        ("passou do tempo", {"projeto": "loja", "comando": "dorme", "segundos": 1}, 504)]:
    confere(f"app.comando, {nome}: {status}", erro(ex.acao_app_comando, hermes, params)[0] == status)
confere("app.comando sem a zona lab: 403", erro(ex.acao_app_comando, sem_lab, {"projeto": "loja", "comando": "x"})[0] == 403)
ex.PROJETOS_LAB = f"{tmp}/nao-instalado"
confere("lab não instalado: 503", erro(ex.acao_app_lista, hermes, {})[0] == 503
        and erro(ex.preparar_app_publicar, hermes, {"projeto": "loja"})[0] == 503)

fim()
