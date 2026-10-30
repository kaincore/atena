"""O hermes/configurar.sh contra um docker de mentira: o que ele grava no Hermes, com e sem o PC da rede
de casa (o modelo pc entra na lista da Atena só com ATENA_PC_IP) e com e sem a voz."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
tmp = tempfile.mkdtemp(prefix="teste-configurar-")
CONF, CHAMADAS, BIN = f"{tmp}/atena.conf", f"{tmp}/chamadas.json", f"{tmp}/bin"
os.makedirs(BIN)
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


# a cópia do script: lê o atena.conf temporário e roda sem root
fonte = open(os.path.join(RAIZ, "hermes", "configurar.sh")).read()
fonte = fonte.replace("/etc/atena/atena.conf", CONF).replace('[ "$(id -u)" = 0 ]', "true")
open(f"{tmp}/configurar.sh", "w").write(fonte)
# o docker de mentira anota cada "hermes config set <chave> <valor>"
open(f"{BIN}/docker", "w").write(f'''#!{sys.executable}
import json, sys
a = sys.argv[1:]
if "config" in a and "set" in a:
    i = a.index("set")
    with open({CHAMADAS!r}, "a") as f:
        f.write(json.dumps([a[i + 1], a[i + 2]]) + "\\n")
''')
os.chmod(f"{BIN}/docker", 0o755)


def configurar(**conf):
    open(CONF, "w").write("".join(f"{k}={v}\n" for k, v in conf.items()))
    if os.path.exists(CHAMADAS):
        os.remove(CHAMADAS)
    r = subprocess.run(["sh", f"{tmp}/configurar.sh"], capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, PATH=f"{BIN}:{os.environ['PATH']}"))
    gravado = {}
    for linha in open(CHAMADAS):
        chave, valor = json.loads(linha)
        gravado[chave] = valor
    return r.returncode, gravado, r.stderr


rc, g, erro = configurar(ATENA_VOZ="nao")
modelos = json.loads(g["providers.atena"])["models"]
confere("sem o PC: roda, e a lista da Atena é haiku, sonnet, opus e local", rc == 0
        and sorted(modelos) == ["haiku", "local", "opus", "sonnet"], (rc, erro, modelos))
confere("o cache da conversa nos modelos Claude", all(modelos[m].get("prompt_caching") for m in ("haiku", "sonnet", "opus")))
confere("lembrete de uma vez só some 1 hora depois", g.get("cron.completed_retention_days") == "0.0417", g)

rc, g, erro = configurar(ATENA_VOZ="nao", ATENA_PC_IP="192.168.0.50", ATENA_PC_CONTEXTO="32768")
modelos = json.loads(g["providers.atena"])["models"]
confere("com o PC: o modelo pc, com o contexto do atena.conf", modelos.get("pc") == {"context_length": 32768}, modelos)
rc, g, erro = configurar(ATENA_VOZ="nao", ATENA_PC_IP='"192.168.0.50"', ATENA_PC_CONTEXTO="muito")
modelos = json.loads(g["providers.atena"])["models"]
confere("com aspas no IP e um contexto que não é número: o pc com 16384", modelos.get("pc") == {"context_length": 16384},
        modelos)

shutil.rmtree(tmp)
print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
