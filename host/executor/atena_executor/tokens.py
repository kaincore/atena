"""Os tokens dos clientes: cada um tem as ações e as zonas dele; só o hash fica guardado."""

import hashlib
import json

from .base import Erro


TOKENS = "/etc/atena/executor/tokens.json"


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def carregar_tokens():
    try:
        with open(TOKENS) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def cliente_do_token(cabecalho):
    if not cabecalho or not cabecalho.startswith("Bearer "):
        raise Erro(401, "falta o token")
    cliente = carregar_tokens().get(hash_token(cabecalho[7:].strip()))
    if not cliente:
        raise Erro(401, "token inválido")
    return cliente
