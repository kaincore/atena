"""O acao.py (a Atena chamando o executor, com o código HTTP), contra um executor de mentira (socket unix
temporário)."""
import http.server
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
tmp = tempfile.mkdtemp(prefix="teste-scripts-")
SOCK, TOKEN = f"{tmp}/executor.sock", f"{tmp}/executor.token"
open(TOKEN, "w").write("token-secreto-123\n")

# a cópia do script apontando para o executor de mentira
PASTA = f"{tmp}/scripts"
os.makedirs(PASTA)
for nome in ("acao.py",):
    fonte = open(os.path.join(RAIZ, "hermes", "scripts", nome)).read()
    fonte = fonte.replace('"/run/atena-executor/executor.sock"', repr(SOCK)).replace('"/opt/data/executor.token"', repr(TOKEN))
    open(f"{PASTA}/{nome}", "w").write(fonte)

SERVICOS = [{"container": "litellm", "estado": "running", "status": "Up 2 hours (healthy)"},
            {"container": "ntfy", "estado": "running", "status": "Up 2 hours (healthy)"},
            {"container": "ollama", "estado": "running", "status": "Up 2 hours (healthy)"}]
CENARIO = {}


def cenario(**mudancas):
    CENARIO.clear()
    CENARIO.update({
        "status.servicos": (200, SERVICOS),
        "sistema.sensores": (200, {"cpu": {"temperatura_c": 41.2}, "gpu": {"temperatura_c": 33.0},
                                   "nvme": {"temperatura_c": 30.4}, "avaliacao": "normal"}),
        "gasto.api": (200, {"mes": "2026-10", "total_usd": 1.0349,
                            "por_modelo": [{"modelo": "haiku", "gasto_usd": 1.0345, "teto_usd": 50}]}),
        "claude.trabalhos": (200, {"trabalhos": []}),
    })
    CENARIO.update(mudancas)


PEDIDOS = []


class Executor(http.server.BaseHTTPRequestHandler):
    def address_string(self):
        return "socket"

    def log_message(self, *a):
        pass

    def responder(self, status, corpo):
        dados = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        PEDIDOS.append(("GET", self.path, self.headers.get("Authorization"), None))
        if self.path == "/acoes":
            return self.responder(200, {"acoes": {"status.servicos": "containers"}})
        return self.responder(200, {"pedido": {"id": "abcd1234", "estado": "concluido"}})

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        PEDIDOS.append(("POST", self.path, self.headers.get("Authorization"), corpo))
        nome = self.path.rsplit("/", 1)[-1]
        if nome == "stack.editar":
            return self.responder(422, {"ok": False, "erro": "não gravei: privileged não pode"})
        status, resultado = CENARIO.get(nome, (404, None))
        if status != 200:
            return self.responder(status, {"ok": False, "erro": f"{nome} fora do alcance"})
        return self.responder(200, {"ok": True, "resultado": resultado})


class Servidor(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


servidor = Servidor(SOCK, Executor)
threading.Thread(target=servidor.serve_forever, daemon=True).start()
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def acao(*args):
    PEDIDOS.clear()
    r = subprocess.run([sys.executable, "-I", f"{PASTA}/acao.py", *args], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout, r.stderr


# --- acao.py ---
cenario()
rc, saida, erro = acao("status.servicos")
confere("acao: a primeira linha é o código HTTP, depois o JSON", saida.startswith("HTTP 200\n")
        and json.loads(saida.split("\n", 1)[1])["resultado"][0]["container"] == "litellm" and rc == 0, saida + erro)
confere("acao: pede com o token, origem chat e params vazios", PEDIDOS[0][1] == "/acao/status.servicos"
        and PEDIDOS[0][2] == "Bearer token-secreto-123" and PEDIDOS[0][3] == {"params": {}, "origem": "chat"}, PEDIDOS)
confere("acao: o token nunca aparece na saída", "token-secreto" not in saida + erro)
rc, saida, erro = acao("servico.logs", '{"stack": "litellm", "linhas": 50}')
confere("acao: os parâmetros em JSON vão no pedido", PEDIDOS[0][3]["params"] == {"stack": "litellm", "linhas": 50}, PEDIDOS)
rc, saida, erro = acao("stack.editar", "{}")
confere("acao: recusa do executor sai com 1, com o código e o erro", rc == 1 and saida.startswith("HTTP 422")
        and "privileged" in saida, saida)
rc, saida, erro = acao("servico.logs", "stack=litellm")
confere("acao: parâmetros que não são JSON: sai com 2 sem chamar o executor", rc == 2 and not PEDIDOS and "JSON" in erro, erro)
rc, saida, erro = acao("servico.logs", '["litellm"]')
confere("acao: parâmetros fora de um objeto: sai com 2", rc == 2 and not PEDIDOS, erro)
rc, saida, erro = acao("--acoes")
confere("acao --acoes: GET /acoes", rc == 0 and PEDIDOS[0][:2] == ("GET", "/acoes") and "status.servicos" in saida, saida)
rc, saida, erro = acao("--pedido", "abcd1234", "30")
confere("acao --pedido: espera o tempo pedido", rc == 0 and PEDIDOS[0][1] == "/pedido/abcd1234?esperar=30", PEDIDOS)
rc, saida, erro = acao("--pedido", "abcd1234", "999")
confere("acao --pedido: no máximo 170 s", PEDIDOS[0][1] == "/pedido/abcd1234?esperar=170", PEDIDOS)
rc, saida, erro = acao("--pedido", "abcd1234", "logo")
confere("acao --pedido com espera que não é número: sai com 2", rc == 2 and not PEDIDOS, erro)

servidor.shutdown()
servidor.server_close()
os.unlink(SOCK)
rc, saida, erro = acao("status.servicos")
confere("acao: sem o executor, sai com 2 e explica", rc == 2 and "sem resposta do executor" in erro, erro)

print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
