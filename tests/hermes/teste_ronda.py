"""A ronda contra um executor de mentira (socket unix temporário): só muda a saída quando muda o servidor."""
import http.server
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
tmp = tempfile.mkdtemp(prefix="teste-ronda-")
SOCK, TOKEN = f"{tmp}/executor.sock", f"{tmp}/executor.token"
open(TOKEN, "w").write("token-falso\n")
fonte = open(os.path.join(RAIZ, "hermes", "scripts", "ronda.py")).read()
fonte = fonte.replace('"/run/atena-executor/executor.sock"', repr(SOCK)).replace('"/opt/data/executor.token"', repr(TOKEN))
RONDA = f"{tmp}/ronda.py"
open(RONDA, "w").write(fonte)

CENARIO = {"servicos": [], "falhas": [], "livre": 50, "ram": 8000, "gpu": None, "temperaturas": None, "fora": False,
           "trabalhos": None, "perguntas": []}   # trabalhos None: token sem o lab (403)
PEDIDOS = []


class Executor(http.server.BaseHTTPRequestHandler):
    def address_string(self):
        return "socket"

    def log_message(self, *a):
        pass

    def do_POST(self):
        PEDIDOS.append((self.path, self.headers.get("Authorization"),
                        json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))))
        nome = self.path.rsplit("/", 1)[-1]
        corpo = {"status.servicos": CENARIO["servicos"], "status.sistema": {"falhas": CENARIO["falhas"]},
                 "status.recursos": {"discos": {"/": {"livre_gb": CENARIO["livre"], "total_gb": 100}},
                                     "ram_disponivel_mb": CENARIO["ram"], "ram_total_mb": 16000, "gpu": CENARIO["gpu"],
                                     "temperaturas": CENARIO["temperaturas"]}}
        corpo["claude.trabalhos"] = {"contas": ["pessoal"], "contas_com_login": ["pessoal"], "trabalhos": CENARIO["trabalhos"]}
        corpo["claude.perguntas"] = CENARIO["perguntas"]
        if CENARIO["fora"] or (nome.startswith("claude.") and CENARIO["trabalhos"] is None):
            resposta, status = {"ok": False, "erro": "fora"}, 403
        else:
            resposta, status = {"ok": True, "resultado": corpo[nome]}, 200
        dados = json.dumps(resposta).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


class Servidor(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


threading.Thread(target=Servidor(SOCK, Executor).serve_forever, daemon=True).start()
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def ronda():
    return subprocess.run([sys.executable, "-I", RONDA], capture_output=True, text=True, timeout=30).stdout


confere("servidor bem: tudo normal", ronda() == "tudo normal\n")
confere("usa o token da Atena e marca a origem", PEDIDOS[-1][1] == "Bearer token-falso" and PEDIDOS[-1][2]["origem"] == "ronda")
CENARIO["servicos"] = [
    {"container": "arca", "stack": "arca", "zona": "apps", "estado": "exited", "status": "Exited (1) 2 minutes ago"},
    {"container": "ntfy", "stack": "ntfy", "zona": "core", "estado": "running", "status": "Up 3 hours (unhealthy)"},
    {"container": "ollama", "stack": "ollama", "zona": "ai", "estado": "running", "status": "Up 5 minutes"}]
saida = ronda()
confere("container parado e doente aparecem, o resto não",
        saida == "container arca (stack arca, zona apps): exited\ncontainer ntfy (stack ntfy, zona core): doente (unhealthy)\n", saida)
CENARIO["servicos"][0]["status"] = "Exited (1) 5 minutes ago"
confere("o tempo que passa não muda a saída (não acorda a Atena à toa)", ronda() == saida)
CENARIO["servicos"] = []
CENARIO.update(falhas=["atena-docker-firewall.service"], livre=8, ram=1000, gpu={"temperatura_c": 90})
saida = ronda()
confere("unidade com falha, disco, RAM e GPU", saida.splitlines() == sorted([
    "unidade do systemd com falha: atena-docker-firewall.service", "disco / acima de 90%",
    "RAM disponível abaixo de 10%", "GPU acima de 85 °C"]), saida)
CENARIO.update(falhas=[], livre=50, ram=8000, gpu=None, temperaturas={"cpu_c": 91.5, "nvme_c": 72.0})
saida = ronda()
confere("CPU e NVMe quentes", saida.splitlines() == ["CPU acima de 85 °C", "NVMe acima de 70 °C"], saida)
CENARIO["temperaturas"] = {"cpu_c": 91.0, "nvme_c": 71.0}
confere("a temperatura que oscila acima do limite não muda a saída", ronda() == saida)
CENARIO["temperaturas"] = {"cpu_c": None, "nvme_c": None}
confere("máquina sem sensores (None): tudo normal", ronda() == "tudo normal\n")
CENARIO["temperaturas"] = None


# --- lab: o fim de um trabalho do Claude Code e as perguntas dele ---
def t(id_, estado, projeto="loja"):
    return {"id": id_, "estado": estado, "projeto": projeto}


confere("sem o lab no token: igual à ronda sem lab", ronda() == "tudo normal\n")
CENARIO["trabalhos"] = [t("aaaa0001", "executando")]
confere("trabalho rodando: tudo normal", ronda() == "tudo normal\n")
CENARIO["trabalhos"] = [t("aaaa0001", "concluido")]
saida = ronda()
confere("trabalho terminou: aparece a linha", saida == "tudo normal\nClaude Code: último trabalho terminado = aaaa0001 "
        "(concluido, projeto loja)\n", saida)
CENARIO["trabalhos"] = [t("bbbb0002", "executando"), t("aaaa0001", "concluido")]
confere("outro começou: a linha não muda (não acorda a Atena à toa)", ronda() == saida)
CENARIO["trabalhos"] = [t("bbbb0002", "falhou", "outro"), t("aaaa0001", "concluido")]
confere("outro terminou: a linha muda", "bbbb0002 (falhou, projeto outro)" in ronda())
CENARIO["perguntas"] = [{"id": "cccc0003", "projeto": "loja", "esperando_min": 2}]
confere("pergunta esperando o dono", "Claude Code pergunta cccc0003 (projeto loja): esperando o dono" in ronda())
CENARIO["perguntas"][0]["esperando_min"] = 12
confere("aos 10 min sem resposta, a linha muda", "o dono não respondeu em 10 min" in ronda())
CENARIO.update(trabalhos=None, perguntas=[], fora=True)
saida = ronda()
confere("executor recusando: a ronda avisa em vez de calar", saida.startswith("a ronda não conseguiu falar com o executor"), saida)

print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
