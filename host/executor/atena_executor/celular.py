"""Avisos e aprovações no celular, pelo ntfy."""

import json
import threading
import time
import urllib.error
import urllib.request

from .base import ler, ler_conf, log


NTFY = "http://127.0.0.1:2586"
NTFY_TOKEN = "/etc/atena/executor/ntfy-servidor.token"         # publica pedidos, lê as respostas
NTFY_TOKEN_BOTAO = "/etc/atena/executor/ntfy-aprovador.token"  # vai dentro dos botões do celular
REPETIR_AVISO = 30          # s entre as tentativas de um aviso que não pode se perder
ESPERA_AVISO = 60 * 60      # por quanto tempo ele tenta


def ntfy(topico, titulo, texto, prioridade=3, tags=(), acoes=()):
    corpo = {"topic": topico, "title": titulo, "message": texto[:3800], "priority": prioridade,
             "tags": list(tags)}
    if acoes:
        corpo["actions"] = list(acoes)
    pedido = urllib.request.Request(NTFY + "/", data=json.dumps(corpo).encode(), method="POST",
                                    headers={"Authorization": "Bearer " + ler(NTFY_TOKEN),
                                             "Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=10) as r:
        r.read()


def avisar(titulo, texto, tags=(), acoes=()):
    """Aviso para o dono; falha do ntfy não derruba o resto."""
    try:
        ntfy("aprovacoes", titulo, texto, tags=tags, acoes=acoes)
    except (OSError, urllib.error.URLError) as e:
        log(evento="ntfy fora do ar", erro=str(e))


def avisar_quando_der(titulo, texto, tags=()):
    """Aviso que não pode se perder: numa thread à parte, tenta de novo até o ntfy receber. É para o que
    o executor acha ao subir: ele sobe logo depois do Docker, e o ntfy (um container) pode ainda não
    estar no ar."""
    def tentar():
        limite = time.monotonic() + ESPERA_AVISO
        while True:
            try:
                ntfy("aprovacoes", titulo, texto, tags=tags)
                return
            except (OSError, urllib.error.URLError) as e:
                if time.monotonic() > limite:
                    log(evento="aviso perdido: o ntfy não voltou", titulo=titulo, erro=str(e))
                    return
            time.sleep(REPETIR_AVISO)
    threading.Thread(target=tentar, daemon=True).start()


def endereco_ntfy():
    """O endereço do ntfy que o celular alcança (os botões chamam esse endereço)."""
    conf = ler_conf()
    return (conf.get("ATENA_NTFY_URL") or f"http://{conf.get('ATENA_LAN_IP')}:2586").rstrip("/")


def botao(rotulo, decisao, p, segredo):
    """Botão de notificação: o celular publica a decisão no tópico respostas."""
    return {"action": "http", "label": rotulo, "method": "POST", "clear": True,
            "url": endereco_ntfy() + "/respostas",
            "headers": {"Authorization": "Bearer " + ler(NTFY_TOKEN_BOTAO)},
            "body": f"{decisao} {p['id']} {segredo}"}


def legivel(resultado):
    if isinstance(resultado, dict):
        return "\n".join(f"{k}: {', '.join(map(str, v)) if isinstance(v, list) else v}"
                         for k, v in resultado.items())
    return str(resultado)
