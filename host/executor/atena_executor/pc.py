"""PC da rede de casa (opcional, ATENA_PC_* no atena.conf): pc.ligar manda o Wake-on-LAN; pc.desligar,
pc.reiniciar e pc.cancelar usam uma chave SSH que, no Windows, só roda o atena-pc.ps1 (aceita só esses
três pedidos)."""

import ipaddress
import os
import re
import socket

from .base import Erro, ler_conf, rodar


PC_CHAVE = "/etc/atena/executor/pc-chave"     # no Windows, essa chave só desliga, reinicia ou cancela
PC_HOSTS = "/etc/atena/executor/pc-known-hosts"


def pc_conf():
    conf = ler_conf()
    if not conf.get("ATENA_PC_IP") or not conf.get("ATENA_PC_MAC"):
        raise Erro(404, "PC não configurado no atena.conf (ATENA_PC_IP e ATENA_PC_MAC)")
    return conf


def acao_pc_estado(cliente, params):
    conf = pc_conf()
    ip, porta = conf["ATENA_PC_IP"], int(conf.get("ATENA_PC_PORTA") or "1234")
    api = False
    try:
        with socket.create_connection((ip, porta), timeout=2):
            api = True
    except OSError:
        pass
    # a tentativa acima força o ARP; se a placa de rede respondeu, o PC está ligado
    _, vizinho = rodar(["ip", "neigh", "show", ip], 5)
    ligado = api or bool(re.search(r"\b(REACHABLE|DELAY|PROBE|STALE)\b", vizinho))
    return {"ligado": ligado, "lm_studio": api}


def acao_pc_ligar(cliente, params):
    conf = pc_conf()
    mac = bytes.fromhex(conf["ATENA_PC_MAC"].replace(":", "").replace("-", ""))
    if len(mac) != 6:
        raise Erro(500, "MAC do PC inválido no atena.conf")
    broadcast = str(ipaddress.ip_network(conf["ATENA_LAN_CIDR"], strict=False).broadcast_address)
    pacote = b"\xff" * 6 + mac * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for porta in (7, 9, 7, 9):
            s.sendto(pacote, (broadcast, porta))
    return {"enviado": True, "dica": "o PC costuma ligar em ~25 s; consulte pc.estado"}


def pc_comando(cliente, params, comando):
    """Manda um pedido ao PC pela chave restrita. No Windows, a chave só roda o atena-pc.ps1, que
    aceita desligar, reiniciar e cancelar e responde "atena-pc: <pedido>". False: o PC está desligado."""
    conf = pc_conf()
    if not conf.get("ATENA_PC_USUARIO") or not os.path.exists(PC_HOSTS):
        raise Erro(404, "o controle do PC ainda não foi configurado no Windows (veja host/windows/LEIAME.md)")
    if not acao_pc_estado(cliente, params)["ligado"]:
        return False
    codigo, texto = rodar(["ssh", "-i", PC_CHAVE, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                           "-o", f"UserKnownHostsFile={PC_HOSTS}", "-o", "ConnectTimeout=5",
                           f"{conf['ATENA_PC_USUARIO']}@{conf['ATENA_PC_IP']}", comando], 20)
    # logo depois de desligar, a memória de rede ainda diz "ligado" por alguns minutos
    if codigo == 255 and re.search(r"No route to host|timed out|Connection refused|Network is unreachable|Host is down", texto):
        return False
    if codigo != 0 or f"atena-pc: {comando}" not in texto:
        raise Erro(502, f"o PC não aceitou o pedido ({comando}): " + texto.strip()[-200:])
    return True


def acao_pc_desligar(cliente, params):
    if not pc_comando(cliente, params, "desligar"):
        return {"desligando": False, "motivo": "o PC já está desligado"}
    return {"desligando": True, "em_segundos": 60, "dica": "dá para cancelar com pc.cancelar (ou, no PC, shutdown /a)"}


def acao_pc_reiniciar(cliente, params):
    if not pc_comando(cliente, params, "reiniciar"):
        return {"reiniciando": False, "motivo": "o PC está desligado; para ligar, use pc.ligar"}
    return {"reiniciando": True, "em_segundos": 60, "dica": "dá para cancelar com pc.cancelar (ou, no PC, shutdown /a)"}


def acao_pc_cancelar(cliente, params):
    if not pc_comando(cliente, params, "cancelar"):
        return {"cancelado": False, "motivo": "o PC já está desligado"}
    return {"cancelado": True, "dica": "se não havia desligamento ou reinício marcado, nada mudou"}
