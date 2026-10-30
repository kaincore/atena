"""O acao.py (a Atena chamando o executor, com o código HTTP) e o bom-dia sem IA, contra um executor de
mentira (socket unix temporário) e um LiteLLM de mentira."""
import datetime as dt
import http.server
import importlib.util
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
LITELLM_PRONTO = [True]


class Litellm(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200 if LITELLM_PRONTO[0] else 503)
        self.send_header("Content-Length", "0")
        self.end_headers()


litellm = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Litellm)
threading.Thread(target=litellm.serve_forever, daemon=True).start()

# cópias dos scripts apontando para o executor e o LiteLLM de mentira, na mesma pasta (o bom-dia importa o acao)
PASTA = f"{tmp}/scripts"
os.makedirs(PASTA)
for nome in ("acao.py", "bom_dia.py"):
    fonte = open(os.path.join(RAIZ, "hermes", "scripts", nome)).read()
    fonte = fonte.replace('"/run/atena-executor/executor.sock"', repr(SOCK)).replace('"/opt/data/executor.token"', repr(TOKEN))
    fonte = fonte.replace('"http://litellm:4000/health/readiness"', repr(f"http://127.0.0.1:{litellm.server_port}/"))
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

# --- bom-dia ---
spec = importlib.util.spec_from_file_location("bom_dia", f"{PASTA}/bom_dia.py")
bd = importlib.util.module_from_spec(spec)
sys.path.insert(0, PASTA)
spec.loader.exec_module(bd)
SEXTA = dt.datetime(2026, 10, 30, 8, 0)

cenario()
texto = bd.montar(SEXTA)
linhas = texto.split("\n")
confere("bom-dia: o dia certo", linhas[0] == "Bom dia! Sexta, 30 de outubro.", linhas[0])
confere("bom-dia: tudo em ordem, com a contagem", "Servidor: tudo em ordem, 3 containers no ar." in linhas, texto)
confere("bom-dia: as temperaturas arredondadas", "Temperaturas: CPU 41 °C, GPU 33 °C, NVMe 30 °C." in linhas, texto)
confere("bom-dia: o gasto do mês e o teto do Haiku", "IA em outubro: US$ 1,03, com o Haiku em 2% do teto de US$ 50,00." in linhas, texto)
confere("bom-dia: sem trabalho do Claude Code, nada sobre ele", not any(l.startswith("Claude Code") for l in linhas), texto)
confere("bom-dia: tudo calmo, 4 linhas", len(linhas) == 4, texto)
confere("bom-dia: origem bom-dia nos pedidos", all(p[3]["origem"] == "bom-dia" for p in PEDIDOS if p[0] == "POST"))

doente = [dict(SERVICOS[0], status="Up 1 hour (unhealthy)"), SERVICOS[1], dict(SERVICOS[2], estado="exited")]
cenario(**{"status.servicos": (200, doente)})
texto = bd.montar(SEXTA)
confere("bom-dia: o que pede atenção, doente e parado", "Servidor: 2 de 3 containers pedem atenção: litellm (doente), "
        "ollama (exited)." in texto, texto)

cenario(**{"sistema.sensores": (200, {"cpu": {"temperatura_c": 91.0}, "avaliacao": "CPU quente (91 °C)"})})
texto = bd.montar(SEXTA)
confere("bom-dia: temperatura quente avisa", "Temperaturas: CPU 91 °C. Atenção: CPU quente (91 °C)." in texto, texto)

trabalhos = [{"projeto": "loja", "estado": "executando", "criado": "2026-10-30 07:40"},
             {"projeto": "site", "estado": "concluido", "criado": "2026-10-29 23:10"},
             {"projeto": "velho", "estado": "concluido", "criado": "2026-10-28 10:00"}]
cenario(**{"claude.trabalhos": (200, {"trabalhos": trabalhos})})
texto = bd.montar(SEXTA)
confere("bom-dia: o Claude Code rodando e o que terminou de noite (o de dois dias atrás não)",
        "Claude Code: 1 rodando (loja); da noite: site (concluido)." in texto, texto)
cenario(**{"claude.trabalhos": (403, None)})
confere("bom-dia: sem o lab, sem linha do Claude Code", "Claude Code" not in bd.montar(SEXTA))

cenario(**{"gasto.api": (500, None)})
texto = bd.montar(SEXTA)
confere("bom-dia: uma parte que falha vira uma linha dizendo qual", "Não consegui ler o gasto de IA (RuntimeError)." in texto
        and "Temperaturas" in texto, texto)

LITELLM_PRONTO[0] = False
cenario()
texto = bd.montar(SEXTA)
confere("bom-dia: a IA fora avisa logo depois do dia", texto.split("\n")[1].startswith("A IA da Atena (LiteLLM) não está"), texto)
LITELLM_PRONTO[0] = True

servidor.shutdown()
servidor.server_close()
os.unlink(SOCK)
texto = bd.montar(SEXTA)
confere("bom-dia: sem o executor, ainda dá bom-dia e diz o que houve", texto.startswith("Bom dia!")
        and "Não consegui falar com o executor" in texto, texto)
rc, saida, erro = acao("status.servicos")
confere("acao: sem o executor, sai com 2 e explica", rc == 2 and "sem resposta do executor" in erro, erro)

print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
