"""Ajudantes dos testes do executor: carrega o script, fala com ele pelo socket e confere."""
import grp
import http.client
import importlib.machinery
import json
import os
import socket
import sys
import tempfile
import threading

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FALHAS = []


def carregar():
    """O executor como módulo, apontando para uma pasta temporária (sem root, sem /etc).
    ATENA_EXECUTOR=<caminho> testa outro arquivo (ex.: o instalado num servidor)."""
    caminho = os.environ.get("ATENA_EXECUTOR") or os.path.join(RAIZ, "host", "sbin", "atena-executor")
    ex = importlib.machinery.SourceFileLoader("executor", caminho).load_module()
    tmp = tempfile.mkdtemp(prefix="teste-executor-")
    ex.SOCKET, ex.TOKENS, ex.CONF = f"{tmp}/executor.sock", f"{tmp}/tokens.json", f"{tmp}/atena.conf"
    ex.GRUPO_CLIENTES = grp.getgrgid(os.getgid()).gr_name
    ex.log = lambda **campos: None
    ex.shutil.chown = lambda *a, **k: None   # o grupo atena-exec não existe fora do servidor
    return ex, tmp


def token(ex, cliente, acoes, zonas, **extra):
    """Grava um token direto no arquivo (como o token-novo faria) e devolve o token."""
    valor = "atx-teste-" + cliente
    tokens = ex.carregar_tokens()
    tokens[ex.hash_token(valor)] = {"cliente": cliente, "acoes": acoes, "zonas": zonas, **extra}
    with open(ex.TOKENS, "w") as f:
        json.dump(tokens, f)
    return valor


def ligar(ex):
    """Sobe o servidor HTTP do executor no socket temporário, numa thread."""
    servidor = ex.Servidor(ex.SOCKET, ex.Pedido)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


class Conexao(http.client.HTTPConnection):
    def __init__(self, caminho):
        super().__init__("x", timeout=10)
        self.caminho = caminho

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect(self.caminho)


def pedir(ex, metodo, rota, token=None, corpo=None, cru=None):
    """(status, json) de uma chamada ao executor."""
    c = Conexao(ex.SOCKET)
    cabecalhos = {"Content-Type": "application/json"}
    if token:
        cabecalhos["Authorization"] = "Bearer " + token
    dados = cru if cru is not None else (json.dumps(corpo).encode() if corpo is not None else None)
    c.request(metodo, rota, body=dados, headers=cabecalhos)
    r = c.getresponse()
    return r.status, json.loads(r.read() or b"{}")


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def erro(funcao, *args):
    """(status, mensagem) do Erro que a função levanta, ou (None, None)."""
    try:
        funcao(*args)
    except Exception as e:
        if hasattr(e, "status"):
            return e.status, str(e)
        raise
    return None, None


def fim():
    print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
    sys.exit(1 if FALHAS else 0)
