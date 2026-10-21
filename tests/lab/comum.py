"""Ajudantes dos testes do lab: carregam o runner, a ponte e o executor apontando para pastas temporárias."""
import grp
import http.client
import importlib.machinery
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "tests"))
from pacote_executor import carregar_executor  # noqa: E402
FALHAS = []
SESSAO = "11111111-2222-3333-4444-555555555555"


def carregar(nome, *caminho):
    sys.dont_write_bytecode = True
    return importlib.machinery.SourceFileLoader(nome, os.path.join(RAIZ, *caminho)).load_module()


def runner(contas="pessoal trabalho", troca=None):
    """O runner como módulo, com a base, os projetos e o atena.conf numa pasta temporária."""
    rn = carregar("runner", "host", "sbin", "atena-claude-runner")
    tmp = tempfile.mkdtemp(prefix="teste-lab-")
    base, projetos = f"{tmp}/base", f"{tmp}/projetos"
    for d in ("fila", "resultados", "registros", *(f"contas/{c}" for c in contas.replace(",", " ").split())):
        os.makedirs(f"{base}/{d}", exist_ok=True)
    os.makedirs(projetos)
    os.chmod(projetos, 0o2775)   # como o instalador cria /srv/lab/projetos
    shutil.copy(os.path.join(RAIZ, "host", "lab", "gitconfig"), f"{base}/.gitconfig")
    with open(f"{tmp}/atena.conf", "w") as f:
        f.write(f'ATENA_CLAUDE_CONTAS="{contas}"\nATENA_TZ=America/Sao_Paulo\n'
                + (f"ATENA_CLAUDE_TROCA={troca}\n" if troca else ""))
    rn.BASE, rn.PROJETOS, rn.CONF = base, projetos, f"{tmp}/atena.conf"
    return rn, tmp


def executor(contas="pessoal trabalho", prontas=("pessoal",), conf=""):
    """O executor como módulo, com a fila do Claude Code, o lab e o atena.conf numa pasta temporária.
    Devolve (executor, pasta, avisos mandados ao celular)."""
    ex = carregar_executor()
    tmp = tempfile.mkdtemp(prefix="teste-lab-ex-")
    for d in ("fila", "resultados", "projetos", "lixeira", "stacks/lab"):
        os.makedirs(f"{tmp}/{d}")
    ex.SOCKET, ex.TOKENS, ex.CONF, ex.PEDIDOS = (f"{tmp}/executor.sock", f"{tmp}/tokens.json", f"{tmp}/atena.conf",
                                                 f"{tmp}/pedidos.json")
    ex.CLAUDE, ex.PROJETOS_LAB, ex.LIXEIRA_LAB, ex.STACKS_LAB = tmp, f"{tmp}/projetos", f"{tmp}/lixeira", f"{tmp}/stacks/lab"
    ex.GRUPO_CLIENTES = grp.getgrgid(os.getgid()).gr_name
    with open(ex.CONF, "w") as f:
        f.write(f'ATENA_LAN_IP=192.168.0.10\nATENA_NTFY_URL=https://ntfy.exemplo\nATENA_CLAUDE_CONTAS="{contas}"\n'
                f"ATENA_TAILSCALE=nao\n{conf}")
    with open(f"{tmp}/contas.json", "w") as f:
        json.dump({c: c in prontas for c in contas.split()}, f)
    ex.ler = lambda caminho: "token-falso"   # tokens do ntfy
    ex.log = lambda **campos: None
    ex.shutil.chown = lambda *a, **k: None
    avisos = []
    ex.ntfy = lambda topico, titulo, texto, prioridade=3, tags=(), acoes=(): avisos.append(
        {"topico": topico, "titulo": titulo, "texto": texto, "acoes": list(acoes)})
    return ex, tmp, avisos


def erro(ex, funcao, *args):
    """(status, mensagem) do Erro do executor que a função levanta, ou (None, None)."""
    try:
        funcao(*args)
    except ex.Erro as e:
        return e.status, str(e)
    return None, None


def uma_volta(ex):
    """Uma volta do acompanhar() do executor (um laço infinito com sleep de 3 s)."""
    class Para(Exception):
        pass
    voltas = {"n": 0}

    def sono(_):
        voltas["n"] += 1
        if voltas["n"] > 1:
            raise Para()
    original, ex.time.sleep = ex.time.sleep, sono
    try:
        ex.acompanhar()
    except Para:
        pass
    finally:
        ex.time.sleep = original


def esperar(condicao, segundos=3):
    limite = time.time() + segundos
    while time.time() < limite:
        if condicao():
            return True
        time.sleep(0.05)
    return False


def botao(aviso, rotulo):
    """O código secreto dentro do botão de uma notificação."""
    return next(a["body"] for a in aviso["acoes"] if a["label"] == rotulo).split()[2]


class Conexao(http.client.HTTPConnection):
    def __init__(self, caminho):
        super().__init__("x", timeout=10)
        self.caminho = caminho

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect(self.caminho)


def ligar(ex):
    """Sobe o servidor HTTP do executor no socket temporário, numa thread."""
    servidor = ex.Servidor(ex.SOCKET, ex.Pedido)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


def token(ex, cliente, acoes, zonas, **extra):
    valor = "atx-teste-" + cliente
    tokens = ex.carregar_tokens()
    tokens[ex.hash_token(valor)] = {"cliente": cliente, "acoes": acoes, "zonas": zonas, **extra}
    with open(ex.TOKENS, "w") as f:
        json.dump(tokens, f)
    return valor


def pedir(ex, metodo, rota, token=None, corpo=None):
    c = Conexao(ex.SOCKET)
    cabecalhos = {"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})}
    c.request(metodo, rota, body=json.dumps(corpo).encode() if corpo is not None else None, headers=cabecalhos)
    r = c.getresponse()
    return r.status, json.loads(r.read() or b"{}")


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def fim():
    print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
    sys.exit(1 if FALHAS else 0)
