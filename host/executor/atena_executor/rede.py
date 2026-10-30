"""A rede de casa, só para ver: quem está conectado agora (IP, MAC, fabricante e o nome que o aparelho
diz), e o nome que o dono dá a cada MAC. Nada aqui mexe na rede nem no roteador.

Como acha os aparelhos sem privilégio nenhum: manda um pacote UDP vazio para cada endereço da faixa
(ATENA_LAN_CIDR, na porta 9, a do descarte); para entregá-lo, o próprio kernel pergunta pelo ARP quem tem
aquele IP, e quem existe responde. A tabela de vizinhos (ip -s neigh) diz depois quem respondeu e há
quanto tempo. O nome vem do DNS do roteador, do mDNS (Apple, Linux, impressoras) ou do NetBIOS
(Windows); o fabricante, do começo do MAC (a lista do IEEE, pacote ieee-data). Celular costuma usar um
MAC privado (aleatório) em cada rede: aí não há fabricante, e o nome do dono é o que identifica."""

import csv
import ipaddress
import json
import os
import re
import select
import socket
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait

from .base import Erro, ler, ler_conf, rodar


REDE = "/var/lib/atena-executor/rede.json"   # os aparelhos já vistos e os nomes que o dono deu
OUI = "/usr/share/ieee-data/oui.csv"
VALE = 60              # uma varredura vale um minuto: o painel aberto pergunta a cada 30 s
CONECTADO = 120        # respondeu nos últimos 2 min: está na rede agora
NOME_VALE = 6 * 3600   # o nome que o aparelho diz é perguntado de novo a cada 6 h
ESQUECE = 30 * 86400   # sem nome do dono e sumido há 30 dias, sai da lista (o MAC privado muda)
NOVO = 86400           # apareceu no último dia (e não na primeira varredura): "novo na rede"
MAIOR_FAIXA = 22       # até 1022 endereços: uma faixa maior encheria a rede de ARP
# quem já tinha resposta antiga passa 5 s esperando (DELAY) antes de perguntar de novo, e quem não
# existe leva 3 tentativas de 1 s: em 7 s a tabela de vizinhos já disse quem respondeu
ESPERA_ARP = 7
ESPERA_NOME = 1.5
NOME_MAX = 40

TRAVA_VARREDURA = threading.Lock()        # uma varredura por vez
TRAVA_ARQUIVO = threading.Lock()
FABRICANTES = {}


def faixa():
    conf = ler_conf()
    try:
        rede = ipaddress.ip_network(conf.get("ATENA_LAN_CIDR", ""), strict=False)
    except ValueError:
        raise Erro(404, "a rede de casa não está no atena.conf (ATENA_LAN_CIDR, ex.: 192.168.0.0/24)")
    if rede.version != 4 or rede.prefixlen < MAIOR_FAIXA:
        raise Erro(400, f"a varredura só cobre uma rede IPv4 de /{MAIOR_FAIXA} para baixo (ATENA_LAN_CIDR é {rede})")
    return rede, conf


def ler_guardado():
    try:
        with open(REDE) as f:
            guardado = json.load(f)
    except (OSError, ValueError):
        guardado = {}
    guardado.setdefault("aparelhos", {})
    return guardado


def gravar(guardado):
    os.makedirs(os.path.dirname(REDE), exist_ok=True)
    temporario = REDE + ".novo"
    with open(temporario, "w") as f:
        json.dump(guardado, f, indent=1, ensure_ascii=False)
    os.replace(temporario, REDE)


def fabricante(mac):
    """O dono do começo do MAC (MA-L do IEEE); None para MAC privado ou sem a lista."""
    if aleatorio(mac):
        return None
    if not FABRICANTES:
        lidos = {"": None}   # mesmo sem o ieee-data, não tenta abrir a cada aparelho
        try:
            with open(OUI, newline="", encoding="utf-8", errors="replace") as f:
                for registro in csv.reader(f):
                    if len(registro) >= 3 and re.fullmatch(r"[0-9A-F]{6}", registro[1]):
                        lidos[registro[1]] = registro[2].strip()
        except OSError:
            pass
        FABRICANTES.update(lidos)   # de uma vez: outra thread nunca vê a lista pela metade
    return FABRICANTES.get(mac.replace(":", "")[:6].upper())


def aleatorio(mac):
    """MAC administrado localmente (o 2º bit do 1º byte): o privado dos celulares, VMs e containers."""
    return bool(int(mac[:2], 16) & 2)


def sondar(rede, proprio):
    """Um UDP vazio para cada endereço: o kernel faz o ARP de cada um."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for ip in rede.hosts():
            if str(ip) == proprio:
                continue
            try:
                s.sendto(b"", (str(ip), 9))
            except OSError:   # rede fora do ar, fila cheia: quem não recebeu fica para a próxima
                pass


def vizinhos(rede, interface):
    """A tabela de vizinhos, só da faixa: ({ip: (mac, segundos desde a última resposta)}, se ainda há
    pergunta sem resposta, a de quem não respondeu ainda ou a de quem tinha resposta antiga)."""
    argv = ["ip", "-s", "-4", "neigh", "show"] + (["dev", interface] if interface else [])
    codigo, saida = rodar(argv, 10)
    if codigo != 0:
        raise Erro(500, "não consegui ler a tabela de vizinhos (ip neigh); confira o ATENA_LAN_IF no atena.conf")
    achados, andando = {}, False
    for linha in saida.splitlines():
        partes = linha.split()
        try:
            dentro = bool(partes) and ipaddress.ip_address(partes[0]) in rede
        except ValueError:
            continue
        if not dentro:
            continue
        andando = andando or partes[-1] in ("INCOMPLETE", "DELAY", "PROBE")
        m = re.search(r"\blladdr ([0-9a-f:]{17})\b.*?\bused \d+/(\d+)/\d+", linha)
        if m:
            achados[partes[0]] = (m.group(1), int(m.group(2)))
    return achados, andando


# --- o nome que o aparelho diz ------------------------------------------------------------------

def limpar_nome(nome):
    """O primeiro rótulo ("iPhone-de-Ana.local" → "iPhone-de-Ana"), só com letras imprimíveis."""
    nome = nome.strip().rstrip(".").split(".")[0]
    nome = "".join(c for c in nome if c.isprintable()).strip()
    return nome[:63] or None


def pergunta_mdns(ip, ident):
    """Pergunta PTR do endereço reverso, mandada direto ao aparelho (a resposta volta só para nós)."""
    rotulos = list(reversed(ip.split("."))) + ["in-addr", "arpa"]
    nome = b"".join(bytes([len(r)]) + r.encode() for r in rotulos) + b"\0"
    return struct.pack("!HHHHHH", ident, 0, 1, 0, 0, 0) + nome + struct.pack("!HH", 12, 1)


def ler_nome_dns(dados, pos, saltos=0):
    """Um nome DNS a partir de pos, seguindo os ponteiros de compressão. (rótulos, posição depois)."""
    rotulos = []
    while True:
        if pos >= len(dados) or saltos > 20:
            raise ValueError("nome DNS cortado")
        n = dados[pos]
        if n == 0:
            return rotulos, pos + 1
        if n & 0xC0 == 0xC0:
            alvo = struct.unpack("!H", dados[pos:pos + 2])[0] & 0x3FFF
            resto, _ = ler_nome_dns(dados, alvo, saltos + 1)
            return rotulos + resto, pos + 2
        rotulos.append(dados[pos + 1:pos + 1 + n].decode("utf-8", "replace"))
        pos += 1 + n


def resposta_mdns(dados):
    """O nome da primeira resposta PTR, ou None."""
    try:
        _, _, perguntas, respostas = struct.unpack("!HHHH", dados[:8])
        pos = 12
        for _ in range(perguntas):
            _, pos = ler_nome_dns(dados, pos)
            pos += 4
        for _ in range(respostas):
            _, pos = ler_nome_dns(dados, pos)
            tipo, _, _, tamanho = struct.unpack("!HHIH", dados[pos:pos + 10])
            pos += 10
            if tipo == 12:
                rotulos, _ = ler_nome_dns(dados, pos)
                return limpar_nome(".".join(rotulos))
            pos += tamanho
    except (ValueError, struct.error, IndexError):
        pass
    return None


# NetBIOS: "qual o seu nome?" (NBSTAT do nome *), como o nbtstat -A do Windows
PERGUNTA_NETBIOS = (struct.pack("!HHHHHH", 0x4154, 0, 1, 0, 0, 0)
                    + b"\x20" + b"CK" + b"A" * 30 + b"\0" + struct.pack("!HH", 0x21, 1))


def resposta_netbios(dados):
    """O nome da máquina (o primeiro nome único com sufixo 0x00), ou None."""
    try:
        _, pos = ler_nome_dns(dados, 12)
        quantos = dados[pos + 10]
        pos += 11
        for _ in range(quantos):
            nome, sufixo, bandeiras = dados[pos:pos + 15], dados[pos + 15], dados[pos + 16]
            pos += 18
            if sufixo == 0 and not bandeiras & 0x80:   # 0x80: nome de grupo (o do grupo de trabalho)
                return limpar_nome(nome.decode("latin-1"))
    except (ValueError, IndexError):
        pass
    return None


def nome_dns(ip):
    try:
        nome = socket.gethostbyaddr(ip)[0]
    except OSError:
        return None
    return None if nome == ip or nome.endswith(".arpa") else limpar_nome(nome)


def nomes(ips):
    """{ip: nome} pelo mDNS, pelo NetBIOS e pelo DNS do roteador, todos ao mesmo tempo (até 1,5 s)."""
    if not ips:
        return {}
    achados = {}
    dns = ThreadPoolExecutor(max_workers=8)
    futuros = {ip: dns.submit(nome_dns, ip) for ip in ips}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as mdns, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as nb:
        for i, ip in enumerate(ips):
            for s, dados, porta in ((mdns, pergunta_mdns(ip, i + 1), 5353), (nb, PERGUNTA_NETBIOS, 137)):
                try:
                    s.sendto(dados, (ip, porta))
                except OSError:
                    pass
        fim = time.monotonic() + ESPERA_NOME
        while (falta := fim - time.monotonic()) > 0 and len(achados) < len(ips):
            prontos, _, _ = select.select([mdns, nb], [], [], falta)
            for s in prontos:
                try:
                    dados, (ip, _) = s.recvfrom(2048)
                except OSError:
                    continue
                if ip in futuros and ip not in achados:
                    nome = (resposta_mdns if s is mdns else resposta_netbios)(dados)
                    if nome:
                        achados[ip] = nome
    wait(futuros.values(), timeout=max(0.0, fim - time.monotonic()))
    for ip, futuro in futuros.items():
        if ip not in achados and futuro.done() and futuro.result():
            achados[ip] = futuro.result()
    dns.shutdown(wait=False, cancel_futures=True)
    return achados


# --- a varredura ----------------------------------------------------------------------------------

def varrer():
    """Pergunta a rede toda e grava quem respondeu. Uma por vez: quem chega no meio espera e usa a dela."""
    rede, conf = faixa()
    with TRAVA_VARREDURA:
        if time.time() - ler_guardado().get("varrido_em", 0) < 10:
            return ler_guardado()   # alguém acabou de varrer enquanto esta esperava
        inicio = time.time()
        interface = conf.get("ATENA_LAN_IF") or None
        sondar(rede, conf.get("ATENA_LAN_IP"))
        while True:
            achados, andando = vizinhos(rede, interface)
            if not andando or time.time() - inicio >= ESPERA_ARP:
                break
            time.sleep(0.5)
        agora = time.time()
        vistos = {ip: (mac, agora - idade) for ip, (mac, idade) in achados.items()}
        antes = ler_guardado()["aparelhos"]
        perguntar = [ip for ip, (mac, visto) in vistos.items()
                     if agora - visto < CONECTADO and agora - antes.get(mac, {}).get("nome_rede_em", 0) > NOME_VALE]
        achados_nome = nomes(perguntar)
        with TRAVA_ARQUIVO:
            guardado = ler_guardado()   # o dono pode ter dado um nome no meio
            aparelhos = guardado["aparelhos"]
            for ip, (mac, visto) in vistos.items():
                a = aparelhos.setdefault(mac, {"primeiro": round(agora)})
                if visto >= a.get("ultimo", 0) - 1:   # o IP mais recente: o antigo pode ainda estar na tabela
                    a["ip"] = ip
                a["ultimo"] = round(max(a.get("ultimo", 0), visto))
                if ip in perguntar:
                    a["nome_rede_em"] = round(agora)
                    if achados_nome.get(ip):
                        a["nome_rede"] = achados_nome[ip]
            for mac in [m for m, a in aparelhos.items() if not a.get("nome") and agora - a.get("ultimo", 0) > ESQUECE]:
                del aparelhos[mac]
            guardado.setdefault("comecou_em", round(agora))
            guardado["varrido_em"] = round(agora)
            guardado["durou_s"] = round(agora - inicio, 1)
            gravar(guardado)
        return guardado


def varrer_em_segundo_plano():
    if TRAVA_VARREDURA.locked():
        return
    def tentar():
        try:
            varrer()
        except Exception:   # o próximo pedido tenta de novo; quem pediu esta já tem a resposta
            pass
    threading.Thread(target=tentar, daemon=True).start()


def proprio(conf):
    """O próprio servidor: ele não aparece na tabela de vizinhos."""
    ip, interface = conf.get("ATENA_LAN_IP"), conf.get("ATENA_LAN_IF")
    if not ip or not interface or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,15}", interface):
        return None
    try:
        return ip, ler(f"/sys/class/net/{interface}/address").lower()
    except OSError:
        return None


def roteador():
    codigo, saida = rodar(["ip", "-4", "route", "show", "default"], 5)
    m = re.search(r"\bvia (\S+)", saida) if codigo == 0 else None
    return m and m.group(1)


def acao_rede_aparelhos(cliente, params):
    rede, conf = faixa()
    guardado = ler_guardado()
    if params.get("agora") or not guardado.get("varrido_em"):
        guardado = varrer()   # uns 7 s
    elif time.time() - guardado["varrido_em"] > VALE:
        varrer_em_segundo_plano()   # responde com a última; a próxima consulta já vem com a nova
    agora = time.time()
    pc = (conf.get("ATENA_PC_MAC") or "").lower().replace("-", ":")
    comeco = guardado.get("comecou_em") or agora
    servidor, porta_rede = proprio(conf), roteador()
    lista = []
    for mac, a in guardado["aparelhos"].items():
        if servidor and mac == servidor[1]:
            continue   # vai embaixo, com o que o servidor sabe de si
        papel = "roteador" if a.get("ip") == porta_rede else "pc" if mac == pc else None
        lista.append({"mac": mac, "ip": a.get("ip"), "nome": a.get("nome"), "nome_rede": a.get("nome_rede"),
                      "fabricante": fabricante(mac), "mac_privado": aleatorio(mac), "papel": papel,
                      "conectado": agora - a.get("ultimo", 0) < CONECTADO,
                      "novo": not a.get("nome") and a.get("primeiro", 0) > comeco + 3600 and agora - a["primeiro"] < NOVO,
                      "primeiro": a.get("primeiro"), "ultimo": a.get("ultimo")})
    if servidor:
        ip, mac = servidor
        a = guardado["aparelhos"].get(mac, {})
        lista.append({"mac": mac, "ip": ip, "nome": a.get("nome"), "nome_rede": socket.gethostname(),
                      "fabricante": fabricante(mac), "mac_privado": aleatorio(mac), "papel": "servidor",
                      "conectado": True, "novo": False, "primeiro": None, "ultimo": round(agora)})
    # os conectados pela ordem do IP; os outros, do visto mais há pouco ao mais antigo
    lista.sort(key=lambda x: (not x["conectado"], int(ipaddress.ip_address(x["ip"])) if x["conectado"] else 0,
                              -(x["ultimo"] or 0)))
    return {"rede": str(rede), "varrido_em": guardado.get("varrido_em"), "durou_s": guardado.get("durou_s"),
            "varrendo": TRAVA_VARREDURA.locked(), "conectados": sum(x["conectado"] for x in lista), "aparelhos": lista,
            "obs": "conectado = respondeu nos últimos 2 min; novo = apareceu no último dia; celular com MAC "
                   "privado não diz o fabricante, e o nome do dono é o que o identifica; sem nome e sumido há "
                   "30 dias, sai da lista"}


def acao_rede_nomear(cliente, params):
    mac = str(params.get("mac", "")).lower().replace("-", ":")
    if not re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", mac):
        raise Erro(400, "mac inválido (ex.: 00:11:22:33:44:55)")
    nome = params.get("nome")
    if not isinstance(nome, str):
        raise Erro(400, "nome é um texto (vazio tira o nome)")
    nome = " ".join("".join(c if c.isprintable() else " " for c in nome).split())
    if len(nome) > NOME_MAX:
        raise Erro(400, f"nome com até {NOME_MAX} letras")
    _, conf = faixa()
    with TRAVA_ARQUIVO:
        guardado = ler_guardado()
        servidor = proprio(conf)
        if mac not in guardado["aparelhos"] and not (servidor and servidor[1] == mac):
            raise Erro(404, f"nenhum aparelho com o MAC {mac} foi visto na rede (veja rede.aparelhos)")
        a = guardado["aparelhos"].setdefault(mac, {"ip": servidor and servidor[0]})
        if nome:
            a["nome"] = nome
        else:
            a.pop("nome", None)
        gravar(guardado)
    return {"mac": mac, "nome": nome or None}
