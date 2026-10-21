"""O que existe no servidor: os containers, com a zona de cada um, as stacks e o IP de casa."""

import re

from .base import Erro, ZONAS, ler_conf, rodar


# na dúvida, vale a zona mais restrita
PRIORIDADE_ZONAS = ["prod", "core", "agents", "ai", "apps", "lab"]


def containers():
    """Containers do Docker com stack e zona.

    A zona vem da pasta do compose (/opt/atena/stacks/<zona>/<stack>). Se a stack foi iniciada pelo
    Dockge, a pasta aparece como o atalho /opt/atena/dockge/<stack>; aí a zona vem das redes zone-*.
    """
    formato = "\t".join([
        '{{.Label "com.docker.compose.project"}}',
        '{{.Label "com.docker.compose.project.working_dir"}}',
        "{{.Names}}", "{{.State}}", "{{.Status}}", "{{.Networks}}",
    ])
    codigo, saida = rodar(["docker", "ps", "-a", "--format", formato])
    if codigo != 0:
        raise Erro(500, "não consegui consultar o Docker")
    lista, zonas_da_stack = [], {}
    for linha in saida.splitlines():
        partes = linha.split("\t")
        if len(partes) != 6 or not partes[0]:
            continue
        stack, pasta, nome, estado, status, redes = partes
        candidatas = set()
        m = re.fullmatch(r"/opt/atena/stacks/([a-z]+)/[^/]+", pasta)
        if m and m.group(1) in ZONAS:
            candidatas.add(m.group(1))
        for rede in redes.split(","):
            r = re.fullmatch(r"zone-([a-z]+)(-.+)?", rede)
            if r and r.group(1) in ZONAS:
                candidatas.add(r.group(1))
        zonas_da_stack.setdefault(stack, set()).update(candidatas)
        lista.append({"stack": stack, "container": nome, "estado": estado, "status": status})
    for c in lista:
        candidatas = zonas_da_stack[c["stack"]]
        c["zona"] = next((z for z in PRIORIDADE_ZONAS if z in candidatas), "?")
    return lista


def stack_permitida(cliente, stack):
    if not isinstance(stack, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", stack):
        raise Erro(400, "nome de stack inválido")
    doks = [c for c in containers() if c["stack"] == stack]
    if not doks:
        raise Erro(404, f"a stack {stack} não existe")
    if doks[0]["zona"] not in cliente["zonas"]:
        raise Erro(403, f"a stack {stack} está fora das zonas deste cliente")
    return [c["container"] for c in doks]


def ip_casa():
    return ler_conf().get("ATENA_LAN_IP") or "127.0.0.1"
