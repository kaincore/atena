"""O reconciliador contra um docker de mentira: conserta só na primeira volta do boot, só o que está no ar,
avisa uma vez por problema e nunca liga nem cria container."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
tmp = tempfile.mkdtemp(prefix="teste-reconciliar-")
STACKS, ESTADO, BIN = f"{tmp}/stacks", f"{tmp}/run", f"{tmp}/bin"
CENARIO, CHAMADAS, AVISOS = f"{tmp}/cenario.json", f"{tmp}/chamadas.log", f"{tmp}/avisos.log"
os.makedirs(BIN)

fonte = open(os.path.join(RAIZ, "host", "sbin", "atena-reconciliar")).read()
fonte = fonte.replace('"/opt/atena/stacks"', repr(STACKS)).replace('"/run/atena-reconciliar"', repr(ESTADO))
fonte = fonte.replace('"/usr/local/sbin/atena-avisar"', repr(f"{BIN}/avisar"))
RECONCILIAR = f"{tmp}/atena-reconciliar"
open(RECONCILIAR, "w").write(fonte)

# o docker de mentira: responde pelo cenário e anota cada chamada
open(f"{BIN}/docker", "w").write(f'''#!{sys.executable}
import json, os, sys
c = json.load(open({CENARIO!r}))
a = sys.argv[1:]
open({CHAMADAS!r}, "a").write(" ".join(a) + "\\n")
if a[:1] == ["compose"]:
    projeto = os.path.basename(a[2])
    if a[3] == "config":
        if projeto not in c["config"]:
            print("compose.yaml: services.x deve ser um mapa", file=sys.stderr); sys.exit(15)
        print(json.dumps(c["config"][projeto])); sys.exit(0)
    if a[3] == "up":
        nome = c["config"][projeto]["services"][a[-1]].get("container_name") or projeto + "-" + a[-1] + "-1"
        c["containers"][nome] = c["consertado"][nome]
        json.dump(c, open({CENARIO!r}, "w")); sys.exit(0)
if a[:1] == ["inspect"]:
    x = c["containers"].get(a[1])
    if x is None:
        print("Error: No such object: " + a[1], file=sys.stderr); sys.exit(1)
    portas = {{}}
    for ip, porta in x["portas"]:
        portas.setdefault(porta + "/tcp", []).append({{"HostIp": ip, "HostPort": porta}})
    print(json.dumps([{{"State": {{"Status": x["estado"]}},
                       "NetworkSettings": {{"Networks": {{n: {{}} for n in x["redes"]}}, "Ports": portas}}}}]))
    sys.exit(0)
sys.exit(2)
''')
open(f"{BIN}/avisar", "w").write(f'''#!{sys.executable}
import sys
open({AVISOS!r}, "a").write(sys.argv[1] + " | " + sys.argv[2].replace("\\n", " / ") + "\\n")
''')
for f in ("docker", "avisar"):
    os.chmod(f"{BIN}/{f}", 0o755)


def svc(redes=("zona",), portas=(), container=None, modo=None):
    s = {"networks": {r: None for r in redes}, "ports": [{"host_ip": ip, "published": p} for ip, p in portas]}
    if container:
        s["container_name"] = container
    if modo:
        s["network_mode"] = modo
        del s["networks"]
    return s


def stack(zona, nome, servicos, redes):
    os.makedirs(f"{STACKS}/{zona}/{nome}", exist_ok=True)
    open(f"{STACKS}/{zona}/{nome}/compose.yaml", "w").write("# o cenário é o que vale\n")
    return {"name": nome, "services": servicos, "networks": redes}


def ok(redes, portas=()):
    return {"estado": "running", "redes": list(redes), "portas": [list(p) for p in portas]}


base = {
    "config": {
        "litellm": stack("ai", "litellm", {
            "litellm": svc(("zona", "svc", "backend"), [("127.0.0.1", "4000"), ("192.168.0.10", "4000")], "litellm"),
            "redis": svc(("backend",), container="litellm-redis")},
            {"zona": {"name": "zone-ai"}, "svc": {"name": "svc-llm"}, "backend": {}}),
        "painel": stack("core", "painel", {"painel": svc(modo="none", container="painel")}, {}),
        "arca": stack("apps", "arca", {"arca": svc(portas=[("", "3002")], container="arca")}, {"zona": {"name": "zone-apps"}}),
        "tetris": stack("lab", "tetris", {"app": svc(container="lab-tetris")}, {"zona": {"name": "zone-lab"}}),
    },
    "containers": {
        "litellm": ok(["zone-ai", "svc-llm", "litellm_backend"], [("127.0.0.1", "4000"), ("192.168.0.10", "4000")]),
        "litellm-redis": ok(["litellm_backend"]),
        "painel": ok([]),
        "arca": ok(["zone-apps"], [("127.0.0.1", "3002")]),
        "lab-tetris": ok(["zone-lab"]),
    },
}
base["consertado"] = dict(base["containers"])
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def cenario(**mudancas):
    c = json.loads(json.dumps(base))
    for nome, x in mudancas.items():
        if x is None:
            del c["containers"][nome]
        else:
            c["containers"][nome] = x
    json.dump(c, open(CENARIO, "w"))


def rodar(*args):
    for f in (CHAMADAS, AVISOS):
        open(f, "w").close()
    env = dict(os.environ, PATH=f"{BIN}:{os.environ['PATH']}")
    r = subprocess.run([sys.executable, "-I", RECONCILIAR, *args], capture_output=True, text=True, env=env, timeout=60)
    return r.stdout, open(CHAMADAS).read(), open(AVISOS).read(), r.returncode


def boot():
    shutil.rmtree(ESTADO, ignore_errors=True)


boot()
cenario()
saida, chamadas, avisos, rc = rodar()
confere("tudo como o compose: nada a dizer, nada recriado", saida == "" and avisos == "" and " up " not in chamadas
        and rc == 0, saida + avisos)
confere("a primeira volta deixa a marca do boot", os.path.exists(f"{ESTADO}/consertou-neste-boot"))

# 26/10: o LiteLLM voltou só nas redes internas, sem a da zona e sem as portas
boot()
cenario(litellm=ok(["svc-llm", "litellm_backend"]))
saida, chamadas, avisos, rc = rodar()
confere("no boot, o que voltou sem rede e porta aparece", "litellm: sem a rede zone-ai" in saida
        and "litellm: sem a porta 127.0.0.1:4000" in saida, saida)
confere("no boot, recria só o serviço que voltou errado", chamadas.count(" up ") == 1
        and "up -d --force-recreate --no-deps litellm" in chamadas, chamadas)
confere("e avisa o conserto, dizendo que ficou como o compose", "recriados no boot" in avisos
        and "Tudo como o compose" in avisos, avisos)
saida, chamadas, avisos, rc = rodar()
confere("na volta seguinte, já consertado: nada", saida == "" and avisos == "", saida + avisos)

# depois da primeira volta: só avisa, uma vez
cenario(arca=ok([], [("127.0.0.1", "3002")]))
saida, chamadas, avisos, rc = rodar()
confere("fora da primeira volta, não recria", " up " not in chamadas, chamadas)
confere("e avisa a diferença", "Container diferente do compose" in avisos and "arca: sem a rede zone-apps" in avisos, avisos)
saida, chamadas, avisos, rc = rodar()
confere("o mesmo problema não avisa de novo", avisos == "", avisos)
cenario()
rodar()
cenario(arca=ok([], [("127.0.0.1", "3002")]))
saida, chamadas, avisos, rc = rodar()
confere("se some e volta, avisa de novo", "arca: sem a rede zone-apps" in avisos, avisos)

# o que está parado é do dono; o que sumiu ou não subiu, só avisa
boot()
cenario(**{"lab-tetris": {"estado": "exited", "redes": [], "portas": []}, "litellm-redis": None,
           "arca": {"estado": "created", "redes": ["zone-apps"], "portas": []}})
saida, chamadas, avisos, rc = rodar()
confere("parado: nem aparece, nem é ligado", "lab-tetris" not in saida and " up " not in chamadas, saida + chamadas)
confere("sumiu: aparece e não é criado", "litellm-redis: sumiu" in saida and " up " not in chamadas, saida)
confere("criado e nunca subiu: aparece", "arca: criado, mas nunca subiu" in saida, saida)

# porta sem IP no compose: vale o número, em qualquer IP
boot()
cenario(arca=ok(["zone-apps"], [("0.0.0.0", "3002")]))
saida, *_ = rodar()
confere("porta sem IP no compose: qualquer IP serve", "arca" not in saida, saida)
cenario(arca=ok(["zone-apps"], []))
saida, *_ = rodar("--so-ver")
confere("porta sem IP no compose, e não publicada: aparece", "arca: sem a porta 3002" in saida, saida)

# --so-ver: não conserta, não avisa, não marca o boot
boot()
cenario(litellm=ok(["svc-llm", "litellm_backend"]))
saida, chamadas, avisos, rc = rodar("--so-ver")
confere("--so-ver mostra", "litellm: sem a rede zone-ai" in saida, saida)
confere("--so-ver não recria, não avisa, não marca o boot", " up " not in chamadas and avisos == ""
        and not os.path.exists(f"{ESTADO}/consertou-neste-boot"), chamadas + avisos)

# compose que não se lê
boot()
cenario()
c = json.load(open(CENARIO))
del c["config"]["tetris"]
json.dump(c, open(CENARIO, "w"))
saida, chamadas, avisos, rc = rodar()
confere("compose que não se lê: aparece com o motivo e avisa", "tetris: não consegui ler o compose" in saida
        and "services.x deve ser um mapa" in saida and "tetris" in avisos and rc == 0, saida + avisos)

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
