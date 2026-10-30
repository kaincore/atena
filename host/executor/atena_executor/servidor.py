"""Atena: executor de ações do servidor (o socket, o protocolo e a linha de comando).

Protocolo: HTTP no socket /run/atena-executor/executor.sock (permissão 660, grupo atena-acoes)
  GET  /acoes                     o catálogo do que o token pode pedir: {nome: {ajuda, risco, pedido,
                                  aprovacao}}; risco é consulta, muda ou destrutivo
  POST /acao/<nome>               corpo JSON {"params": {...}, "origem": "manual|agendamento|..."}
                                  responde 202 {"pedido": id} quando a ação fica esperando algo
                                  (aprovação, o Claude Code ou um trabalho em segundo plano)
  GET  /pedido/<id>[?esperar=s]   estado de um pedido (só do cliente que pediu); com esperar, segura
                                  a resposta até o pedido terminar ou passar s segundos (até 170);
                                  com versao=n também, até ele mudar depois da versão n (o chat do painel)
  Cabeçalho: Authorization: Bearer <token>

Linha de comando:
  atena-executor servir           o serviço (atena-executor.service)
  atena-executor acoes <perfil>   as ações do token de painel, atena ou atena-lab (para o instalador)
Administração (como root):
  atena-executor token-novo <cliente> <acoes> <zonas> [aprovar]
      listas separadas por vírgula; aprovar = ações que pedem o celular, além das destrutivas
      ("nenhuma": nem as destrutivas; é o painel, onde quem confirma é o dono)
      imprime o token uma única vez; só o hash fica guardado
  atena-executor token-remover <cliente>   revoga o token do cliente
  atena-executor tokens   lista os clientes cadastrados
"""

import http.server
import json
import os
import re
import secrets
import shutil
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse

from .acoes import ACOES, do_perfil
from .base import Erro, ZONAS, log
from .claude import acompanhar
from .pedidos import (ESTADO, MUDOU, TERMINADOS, carregar_estado, criar_pedido, executar, mudar,
                      ouvir_respostas, pedidos_interrompidos, pedir_aprovacao, precisa_aprovacao, publico)
from .tokens import TOKENS, carregar_tokens, cliente_do_token, hash_token


SOCKET = "/run/atena-executor/executor.sock"
GRUPO_CLIENTES = "atena-acoes"
LIMITE_PEDIDO = 1024 * 1024   # stack.editar manda o arquivo inteiro
DESCARTE_MAXIMO = 8 * 1024 * 1024   # quanto de um pedido grande demais é lido (e jogado fora) antes do 413
ESPERA_MAXIMA = 170         # GET /pedido?esperar: abaixo do limite de 180 s do terminal do Hermes


class Pedido(http.server.BaseHTTPRequestHandler):
    server_version = "atena-executor"

    def address_string(self):
        return "socket"

    def log_message(self, *args):
        pass  # o registro útil é o log() de cada ação

    def responder(self, status, corpo):
        dados = json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        try:
            cliente = cliente_do_token(self.headers.get("Authorization"))
            url = urllib.parse.urlsplit(self.path)
            m = re.fullmatch(r"/pedido/([0-9a-f]{8})", url.path)
            if url.path == "/acoes":
                # o catálogo do que este token pode pedir: o painel e a Atena leem daqui
                self.responder(200, {"cliente": cliente["cliente"], "zonas": cliente["zonas"], "acoes": {
                    n: {"ajuda": ACOES[n].ajuda, "risco": ACOES[n].risco, "pedido": ACOES[n].preparar is not None,
                        "aprovacao": precisa_aprovacao(cliente, n)}
                    for n in cliente["acoes"] if n in ACOES}})
            elif m:
                consulta = urllib.parse.parse_qs(url.query)
                esperar = consulta.get("esperar", ["0"])[0]
                versao = consulta.get("versao", [""])[0]
                limite = time.monotonic() + min(int(esperar) if esperar.isdigit() else 0, ESPERA_MAXIMA)
                with MUDOU:
                    p = ESTADO["pedidos"].get(m.group(1))
                    if not p or p["cliente"] != cliente["cliente"]:
                        raise Erro(404, "pedido não encontrado")
                    while (p["estado"] not in TERMINADOS and time.monotonic() < limite
                           and (not versao.isdigit() or p.get("versao", 0) <= int(versao))):
                        MUDOU.wait(limite - time.monotonic())
                    corpo = {"ok": True, "pedido": publico(p)}
                self.responder(200, corpo)
            else:
                raise Erro(404, "rota desconhecida")
        except Erro as e:
            self.responder(e.status, {"ok": False, "erro": str(e)})

    def do_POST(self):
        inicio = time.monotonic()
        nome, cliente, origem, params = None, None, None, {}
        try:
            cliente = cliente_do_token(self.headers.get("Authorization"))
            m = re.fullmatch(r"/acao/([a-z.]+)", self.path)
            if not m or m.group(1) not in ACOES:
                raise Erro(404, "ação desconhecida")
            nome = m.group(1)
            if nome not in cliente["acoes"]:
                raise Erro(403, f"o cliente {cliente['cliente']} não pode pedir {nome}")
            tamanho = int(self.headers.get("Content-Length") or 0)
            if tamanho > LIMITE_PEDIDO:
                # lê e joga fora o corpo antes de recusar: fechar com ele ainda por ler faz o cliente
                # receber "conexão encerrada" (broken pipe) em vez do 413
                falta = min(tamanho, DESCARTE_MAXIMO)
                while falta > 0:
                    pedaco = self.rfile.read(min(falta, 65536))
                    if not pedaco:
                        break
                    falta -= len(pedaco)
                raise Erro(413, "pedido grande demais")
            corpo = json.loads(self.rfile.read(tamanho) or b"{}")
            params = corpo.get("params") or {}
            origem = str(corpo.get("origem", "manual"))[:32]
            if not isinstance(params, dict):
                raise Erro(400, "params deve ser um objeto")
            funcao, preparar = ACOES[nome].funcao, ACOES[nome].preparar
            if not preparar:
                resultado = funcao(cliente, params)
                log(cliente=cliente["cliente"], origem=origem, acao=nome, params=params, ok=True,
                    segundos=round(time.monotonic() - inicio, 2))
                self.responder(200, {"ok": True, "acao": nome, "resultado": resultado})
                return
            titulo, texto = preparar(cliente, params)
            p = criar_pedido(cliente, nome, params, origem, titulo)
            if precisa_aprovacao(cliente, nome):
                pedir_aprovacao(p, f"{cliente['cliente']} pede: {titulo}", texto)
                log(cliente=cliente["cliente"], origem=origem, acao=nome, params=params, pedido=p["id"],
                    ok=True, aprovacao="pedida")
                self.responder(202, {"ok": True, "acao": nome, "pedido": p["id"], "estado": "aguardando",
                                     "mensagem": "pedido enviado ao celular do dono; consulte GET /pedido/<id>"})
                return
            mudar(p, estado="executando")
            resultado = executar(p)
            log(cliente=cliente["cliente"], origem=origem, acao=nome, params=params, pedido=p["id"], ok=True,
                segundos=round(time.monotonic() - inicio, 2))
            if resultado is None:
                self.responder(202, {"ok": True, "acao": nome, "pedido": p["id"], "estado": p["estado"],
                                     "mensagem": "em andamento; acompanhe em GET /pedido/<id>?esperar=170"})
            else:
                self.responder(200, {"ok": True, "acao": nome, "pedido": p["id"], "resultado": resultado})
        except subprocess.TimeoutExpired:
            log(cliente=cliente and cliente["cliente"], origem=origem, acao=nome, params=params, ok=False, erro="tempo esgotado")
            self.responder(504, {"ok": False, "erro": "a ação passou do tempo máximo"})
        except (Erro, json.JSONDecodeError, ValueError) as e:
            status = e.status if isinstance(e, Erro) else 400
            log(cliente=cliente and cliente["cliente"], origem=origem, acao=nome, params=params, ok=False, erro=str(e))
            self.responder(status, {"ok": False, "erro": str(e)})
        except Exception as e:   # erro inesperado: responde em vez de derrubar a conexão
            log(cliente=cliente and cliente["cliente"], origem=origem, acao=nome, params=params, ok=False, erro=repr(e))
            self.responder(500, {"ok": False, "erro": "erro interno; veja journalctl -u atena-executor"})


class Servidor(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def servir():
    carregar_estado()
    pedidos_interrompidos()
    if os.path.exists(SOCKET):
        os.unlink(SOCKET)
    servidor = Servidor(SOCKET, Pedido)
    import grp
    os.chown(SOCKET, -1, grp.getgrnam(GRUPO_CLIENTES).gr_gid)
    os.chmod(SOCKET, 0o660)
    threading.Thread(target=ouvir_respostas, daemon=True).start()
    threading.Thread(target=acompanhar, daemon=True).start()
    log(evento="executor no ar", socket=SOCKET, acoes=sorted(ACOES))
    servidor.serve_forever()


def gravar_tokens(tokens):
    os.makedirs(os.path.dirname(TOKENS), exist_ok=True)
    temporario = TOKENS + ".novo"
    with open(temporario, "w") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)
    os.chmod(temporario, 0o640)
    shutil.chown(temporario, group="atena-exec")  # só o executor lê; os clientes não
    os.replace(temporario, TOKENS)


def token_novo(cliente, acoes, zonas, aprovar=None):
    acoes = [a for a in acoes.split(",") if a]
    zonas = [z for z in zonas.split(",") if z]
    lista_aprovar = None if aprovar is None else [a for a in aprovar.split(",") if a and a != "nenhuma"]
    desconhecidas = ([a for a in acoes + (lista_aprovar or []) if a not in ACOES]
                     + [z for z in zonas if z not in ZONAS])
    if desconhecidas:
        sys.exit(f"desconhecido: {', '.join(desconhecidas)}")
    # um token por cliente: criar de novo revoga o anterior
    tokens = {h: c for h, c in carregar_tokens().items() if c["cliente"] != cliente}
    token = "atx-" + secrets.token_urlsafe(32)
    dados = {"cliente": cliente, "acoes": acoes, "zonas": zonas}
    if lista_aprovar is not None:
        dados["aprovar"] = lista_aprovar
    tokens[hash_token(token)] = dados
    gravar_tokens(tokens)
    print(token)


def token_remover(cliente):
    tokens = carregar_tokens()
    restantes = {h: c for h, c in tokens.items() if c["cliente"] != cliente}
    if len(restantes) == len(tokens):
        sys.exit(f"o cliente {cliente} não tem token")
    gravar_tokens(restantes)
    print(f"token de {cliente} revogado")


def principal():
    """A linha de comando: servir ou administrar os tokens."""
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    if comando == "servir":
        servir()
    elif comando == "token-novo" and len(sys.argv) in (5, 6):
        token_novo(*sys.argv[2:])
    elif comando == "token-remover" and len(sys.argv) == 3:
        token_remover(sys.argv[2])
    elif comando == "acoes" and len(sys.argv) == 3 and sys.argv[2] in ("painel", "atena", "atena-lab"):
        # para o instalador: as ações do token de um perfil, separadas por vírgula
        print(",".join(do_perfil(sys.argv[2])))
    elif comando == "tokens":
        for c in carregar_tokens().values():
            aprovar = ",".join(c["aprovar"]) or "nenhuma" if "aprovar" in c else "todas que podem"
            print(f"{c['cliente']:12} zonas: {','.join(c['zonas']):28} aprovação: {aprovar:16} ações: {','.join(c['acoes'])}")
    else:
        sys.exit(__doc__)
