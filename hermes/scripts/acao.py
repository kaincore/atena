"""Chama o executor de ações pelo socket, com o token da Atena, e diz o código HTTP.

  python3 /opt/data/scripts/acao.py <ação> ['{"param": "valor"}']   pede uma ação
  python3 /opt/data/scripts/acao.py --acoes                         o que este token pode pedir, com o risco
  python3 /opt/data/scripts/acao.py --pedido <id> [segundos]        acompanha um pedido (espera até 170 s)

A primeira linha é "HTTP <código>"; depois vem a resposta em JSON. Sai com 0 em 2xx, 1 numa recusa ou
erro do executor (a mensagem está em "erro") e 2 se nem chegou a falar com ele. O token nunca aparece.
Também serve de módulo para os scripts do cron: from acao import pedir.
"""
import http.client
import json
import socket
import sys

SOCKET = "/run/atena-executor/executor.sock"
TOKEN = "/opt/data/executor.token"


class Conexao(http.client.HTTPConnection):
    def __init__(self, prazo):
        super().__init__("executor", timeout=prazo)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(SOCKET)


def pedir(metodo, rota, corpo=None, prazo=60):
    """(código HTTP, resposta em dict). Erros de conexão sobem como OSError."""
    with open(TOKEN) as f:
        token = f.read().strip()
    c = Conexao(prazo)
    try:
        c.request(metodo, rota, body=json.dumps(corpo) if corpo is not None else None,
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        r = c.getresponse()
        dados = r.read()
    finally:
        c.close()
    try:
        resposta = json.loads(dados or b"{}")
    except ValueError:
        resposta = {"ok": False, "erro": dados.decode("utf-8", "replace")[:500]}
    return r.status, resposta


def acao(nome, params=None, origem="chat", prazo=60):
    return pedir("POST", f"/acao/{nome}", {"params": params or {}, "origem": origem}, prazo)


def principal(argv):
    uso = "uso: acao.py <ação> ['{\"param\": \"valor\"}'] | --acoes | --pedido <id> [segundos]"
    if not argv or argv[0] in ("-h", "--help"):
        print(uso)
        return 0 if argv else 2
    try:
        if argv[0] == "--acoes":
            status, resposta = pedir("GET", "/acoes")
        elif argv[0] == "--pedido":
            if len(argv) < 2 or (len(argv) > 2 and not argv[2].isdigit()):
                print(uso, file=sys.stderr)
                return 2
            espera = min(int(argv[2]), 170) if len(argv) > 2 else 170
            status, resposta = pedir("GET", f"/pedido/{argv[1]}?esperar={espera}", prazo=espera + 5)
        else:
            try:
                params = json.loads(argv[1]) if len(argv) > 1 else {}
            except ValueError as e:
                print(f"os parâmetros não são JSON: {e}", file=sys.stderr)
                return 2
            if not isinstance(params, dict):
                print('os parâmetros vão num objeto JSON: \'{"stack": "litellm"}\'', file=sys.stderr)
                return 2
            status, resposta = acao(argv[0], params)
    except (OSError, ValueError) as e:
        print(f"sem resposta do executor ({type(e).__name__}: {e}); ele pode estar reiniciando", file=sys.stderr)
        return 2
    print(f"HTTP {status}")
    print(json.dumps(resposta, ensure_ascii=False, indent=1))
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
