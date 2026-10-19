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

CENARIO = {"servicos": [], "falhas": [], "livre": 50, "ram": 8000, "gpu": None, "fora": False}
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
                                     "ram_disponivel_mb": CENARIO["ram"], "ram_total_mb": 16000, "gpu": CENARIO["gpu"]}}
        resposta, status = ({"ok": False, "erro": "fora"}, 403) if CENARIO["fora"] else ({"ok": True, "resultado": corpo[nome]}, 200)
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
CENARIO.update(falhas=[], livre=50, ram=8000, gpu=None, fora=True)
saida = ronda()
confere("executor recusando: a ronda avisa em vez de calar", saida.startswith("a ronda não conseguiu falar com o executor"), saida)

print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
