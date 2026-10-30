"""A rede de casa: a varredura (tabela de vizinhos simulada), o fabricante pelo MAC, os nomes que os aparelhos
dizem (pacotes de mDNS e NetBIOS montados aqui), o nome do dono e quem sai da lista."""
import json
import struct
import time

from comum import carregar, confere, erro, fim

ex, tmp = carregar()
ex.REDE = f"{tmp}/rede.json"
ex.OUI = f"{tmp}/oui.csv"
with open(ex.OUI, "w") as f:
    f.write('Registry,Assignment,Organization Name,Organization Address\n'
            'MA-L,001122,"Fabricante Exemplo, Ltda.",Rua Um 1\nMA-L,A4B1C2,Roteadores Exemplo,Rua Dois 2\n')
CONF = {"ATENA_LAN_CIDR": "192.168.0.0/24", "ATENA_LAN_IF": "enp3s0", "ATENA_LAN_IP": "192.168.0.10",
        "ATENA_PC_MAC": "00:11:22:33:44:55"}
ex.ler_conf = lambda: dict(CONF)
ex.proprio = lambda conf: ("192.168.0.10", "00:11:22:aa:bb:cc")
ex.ESPERA_ARP = 3
c = {"cliente": "painel", "zonas": ["apps"], "acoes": []}

# --- a tabela de vizinhos, como o ip -s -4 neigh show dev escreve (o "probes" vem grudado) ---
TABELA = {"agora": ""}
LEITURAS = []
SONDADAS = []
NOMES_PEDIDOS = []


def rodar_falso(argv, tempo=30):
    if argv[:2] == ["ip", "-4"] and "route" in argv:
        return 0, "default via 192.168.0.1 dev enp3s0 proto static\n"
    if "neigh" in argv:
        LEITURAS.append(argv)
        texto = TABELA["agora"]
        if isinstance(texto, list):   # uma leitura por vez: a pergunta ainda sem resposta, depois a resposta
            texto = texto.pop(0) if len(texto) > 1 else texto[0]
        return 0, texto
    return 1, "comando inesperado"


ex.rodar = rodar_falso
ex.sondar = lambda rede, proprio: SONDADAS.append((str(rede), proprio))


def nomes_falsos(ips):
    NOMES_PEDIDOS.append(sorted(ips))
    return {"192.168.0.23": "iPhone-de-Exemplo"} if "192.168.0.23" in ips else {}


ex.nomes = nomes_falsos

ROTEADOR = "192.168.0.1 lladdr a4:b1:c2:00:00:01  ref 1 used 900/0/900probes 1 REACHABLE"
CELULAR = "192.168.0.23 lladdr 3a:00:00:00:00:23  used 40/2/40probes 4 REACHABLE"
PC = "192.168.0.50 lladdr 00:11:22:33:44:55  used 3000/2900/2900probes 0 STALE"
FALTA = "192.168.0.77  INCOMPLETE"
FORA = "10.10.0.3 lladdr 02:42:0a:0a:00:03  used 1/1/1probes 1 REACHABLE"
TABELA["agora"] = ["\n".join([ROTEADOR, CELULAR, PC, FALTA, FORA]), "\n".join([ROTEADOR, CELULAR, PC, FORA])]

r = ex.acao_rede_aparelhos(c, {})
confere("a primeira consulta varre na hora (não há o que mostrar antes)", len(SONDADAS) == 1 and SONDADAS[0] == ("192.168.0.0/24", "192.168.0.10"), SONDADAS)
confere("espera a pergunta sem resposta (INCOMPLETE) antes de ler a tabela de novo", len(LEITURAS) == 2, LEITURAS)
confere("lê só a interface de casa", LEITURAS[0][-2:] == ["dev", "enp3s0"], LEITURAS[0])
por_ip = {a["ip"]: a for a in r["aparelhos"]}
confere("só a faixa de casa (as redes dos containers ficam fora)", set(por_ip) == {"192.168.0.1", "192.168.0.10", "192.168.0.23", "192.168.0.50"}, sorted(por_ip))
confere("conectado = respondeu há pouco; o PC parado há 48 min não está",
        por_ip["192.168.0.1"]["conectado"] and por_ip["192.168.0.23"]["conectado"] and not por_ip["192.168.0.50"]["conectado"])
confere("visto pela última vez = a última resposta, não a varredura", time.time() - por_ip["192.168.0.50"]["ultimo"] >= 2890)
confere("papéis: o roteador (rota padrão), o PC (ATENA_PC_MAC) e o próprio servidor",
        (por_ip["192.168.0.1"]["papel"], por_ip["192.168.0.50"]["papel"], por_ip["192.168.0.10"]["papel"]) == ("roteador", "pc", "servidor"))
confere("fabricante pelo começo do MAC (lista do IEEE)",
        por_ip["192.168.0.1"]["fabricante"] == "Roteadores Exemplo" and por_ip["192.168.0.50"]["fabricante"] == "Fabricante Exemplo, Ltda.")
confere("MAC privado do celular: sem fabricante, marcado", por_ip["192.168.0.23"]["mac_privado"] and por_ip["192.168.0.23"]["fabricante"] is None)
confere("o nome que o aparelho diz, perguntado só aos conectados", por_ip["192.168.0.23"]["nome_rede"] == "iPhone-de-Exemplo"
        and NOMES_PEDIDOS == [["192.168.0.1", "192.168.0.23"]], NOMES_PEDIDOS)
confere("ordem: conectados pelo IP, depois os outros", [a["ip"] for a in r["aparelhos"]] == ["192.168.0.1", "192.168.0.10", "192.168.0.23", "192.168.0.50"])
confere("na primeira varredura ninguém é novo", not any(a["novo"] for a in r["aparelhos"]))
confere("conta os conectados (com o servidor)", r["conectados"] == 3 and r["rede"] == "192.168.0.0/24")

# --- a próxima consulta: dentro de 1 min usa a guardada; depois, varre em segundo plano ---
ex.acao_rede_aparelhos(c, {})
confere("dentro de 1 min não varre de novo", len(SONDADAS) == 1)
guardado = json.load(open(ex.REDE))
guardado["varrido_em"] -= 120
guardado["comecou_em"] -= 3 * 86400
json.dump(guardado, open(ex.REDE, "w"))
NOVO = "192.168.0.31 lladdr 00:11:22:00:00:31  used 5/1/5probes 1 REACHABLE"
TABELA["agora"] = "\n".join([ROTEADOR, CELULAR, NOVO])
r = ex.acao_rede_aparelhos(c, {})
confere("velha: responde na hora com a guardada", "192.168.0.31" not in {a["ip"] for a in r["aparelhos"]})
for _ in range(50):
    if not ex.TRAVA_VARREDURA.locked() and len(SONDADAS) == 2:
        break
    time.sleep(0.05)
r = ex.acao_rede_aparelhos(c, {})
por_ip = {a["ip"]: a for a in r["aparelhos"]}
confere("e a varredura em segundo plano já entra na próxima", len(SONDADAS) == 2 and "192.168.0.31" in por_ip, SONDADAS)
confere("aparelho que chegou depois da primeira varredura é novo", por_ip["192.168.0.31"]["novo"])
confere("o nome que o aparelho diz não é perguntado de novo antes de 6 h", NOMES_PEDIDOS[-1] == ["192.168.0.31"], NOMES_PEDIDOS)
confere("o PC sumido continua na lista, com a última vez", "192.168.0.50" in por_ip and not por_ip["192.168.0.50"]["conectado"])

# --- o IP que mudou: vale o mais recente ---
guardado = json.load(open(ex.REDE))
guardado["varrido_em"] -= 120
json.dump(guardado, open(ex.REDE, "w"))
TABELA["agora"] = "\n".join([ROTEADOR, "192.168.0.24 lladdr 3a:00:00:00:00:23  used 3/1/3probes 1 REACHABLE",
                             "192.168.0.23 lladdr 3a:00:00:00:00:23  used 600/500/600probes 0 STALE"])
r = ex.acao_rede_aparelhos(c, {"agora": True})
celular = [a for a in r["aparelhos"] if a["mac"] == "3a:00:00:00:00:23"]
confere("agora=true varre antes de responder; o IP novo vence o antigo da tabela",
        len(SONDADAS) == 3 and len(celular) == 1 and celular[0]["ip"] == "192.168.0.24", celular)

# --- o nome do dono ---
confere("mac inválido: 400", erro(ex.acao_rede_nomear, c, {"mac": "00:11:22", "nome": "x"})[0] == 400)
confere("nome que não é texto: 400", erro(ex.acao_rede_nomear, c, {"mac": "3a:00:00:00:00:23", "nome": 5})[0] == 400)
confere("nome longo: 400", erro(ex.acao_rede_nomear, c, {"mac": "3a:00:00:00:00:23", "nome": "x" * 41})[0] == 400)
status, msg = erro(ex.acao_rede_nomear, c, {"mac": "de:ad:be:ef:00:01", "nome": "Fantasma"})
confere("MAC que nunca apareceu: 404 que aponta a lista", status == 404 and "rede.aparelhos" in msg, msg)
r = ex.acao_rede_nomear(c, {"mac": "3A-00-00-00-00-23", "nome": "  Celular\tda\n Ana "})
confere("nomeia (MAC com traço e maiúsculas; espaços e controles viram um espaço)", r == {"mac": "3a:00:00:00:00:23", "nome": "Celular da Ana"}, r)
r = ex.acao_rede_nomear(c, {"mac": "00:11:22:aa:bb:cc", "nome": "Servidor"})
lista = ex.acao_rede_aparelhos(c, {})["aparelhos"]
servidor = [a for a in lista if a["mac"] == "00:11:22:aa:bb:cc"]
confere("o próprio servidor também ganha nome, e aparece uma vez só", len(servidor) == 1 and servidor[0]["nome"] == "Servidor"
        and servidor[0]["papel"] == "servidor", servidor)
confere("aparelho com nome do dono não é novo", not [a for a in lista if a["nome"] and a["novo"]])

# --- quem sai da lista: sem nome e sumido há 30 dias ---
guardado = json.load(open(ex.REDE))
guardado["varrido_em"] -= 120
for mac in ("3a:00:00:00:00:23", "00:11:22:33:44:55"):
    guardado["aparelhos"][mac]["ultimo"] -= 31 * 86400
json.dump(guardado, open(ex.REDE, "w"))
TABELA["agora"] = ROTEADOR
ex.acao_rede_aparelhos(c, {"agora": True})
aparelhos = json.load(open(ex.REDE))["aparelhos"]
confere("sumido há 30 dias sem nome sai; com nome do dono fica", "00:11:22:33:44:55" not in aparelhos and "3a:00:00:00:00:23" in aparelhos)
r = ex.acao_rede_nomear(c, {"mac": "3a:00:00:00:00:23", "nome": ""})
confere("nome vazio tira o nome", r["nome"] is None and "nome" not in json.load(open(ex.REDE))["aparelhos"]["3a:00:00:00:00:23"])

# --- a faixa: só IPv4 de /22 para baixo ---
CONF["ATENA_LAN_CIDR"] = "10.0.0.0/16"
confere("faixa grande demais: 400 (encheria a rede de ARP)", erro(ex.acao_rede_aparelhos, c, {})[0] == 400)
CONF["ATENA_LAN_CIDR"] = ""
confere("sem ATENA_LAN_CIDR: 404", erro(ex.acao_rede_aparelhos, c, {})[0] == 404)
CONF["ATENA_LAN_CIDR"] = "192.168.0.0/24"

# --- fabricante e MAC privado ---
ex.FABRICANTES.clear()
ex.OUI = f"{tmp}/nao-existe.csv"
confere("sem o ieee-data: sem fabricante, sem erro", ex.fabricante("00:11:22:33:44:55") is None and ex.FABRICANTES == {"": None})
confere("MAC privado: o 2º bit do 1º byte", ex.aleatorio("3a:00:00:00:00:00") and ex.aleatorio("02:42:0a:00:00:01")
        and not ex.aleatorio("00:11:22:33:44:55") and not ex.aleatorio("a4:b1:c2:00:00:01"))

# --- os nomes que os aparelhos dizem: os pacotes ---
pergunta = ex.pergunta_mdns("192.168.0.23", 7)
confere("mDNS: pergunta PTR de 23.0.168.192.in-addr.arpa", pergunta[:2] == b"\x00\x07"
        and b"\x0223\x010\x03168\x03192\x07in-addr\x04arpa\x00\x00\x0c\x00\x01" in pergunta)
nome_ptr = b"\x11iPhone-de-Exemplo\x05local\x00"
resposta = (struct.pack("!HHHHHH", 7, 0x8400, 1, 1, 0, 0) + pergunta[12:]
            + b"\xc0\x0c" + struct.pack("!HHIH", 12, 0x8001, 10, len(nome_ptr)) + nome_ptr)
confere("mDNS: lê o nome da resposta (com ponteiro de compressão) e tira o .local",
        ex.resposta_mdns(resposta) == "iPhone-de-Exemplo", ex.resposta_mdns(resposta))
confere("mDNS: resposta cortada ou com laço de ponteiros não derruba", ex.resposta_mdns(resposta[:40]) is None
        and ex.resposta_mdns(resposta[:12] + b"\xc0\x0c") is None)


def nbstat(*nomes):
    corpo = bytes([len(nomes)]) + b"".join(n.ljust(15).encode("latin-1") + bytes([s, b, 0]) for n, s, b in nomes)
    return (struct.pack("!HHHHHH", 0x4154, 0x8400, 0, 1, 0, 0) + b"\x20" + b"CK" + b"A" * 30 + b"\0"
            + struct.pack("!HHIH", 0x21, 1, 0, len(corpo)) + corpo)


confere("NetBIOS: a pergunta é o NBSTAT do nome *", ex.PERGUNTA_NETBIOS.endswith(b"\x20CK" + b"A" * 30 + b"\x00\x00\x21\x00\x01"))
confere("NetBIOS: o nome da máquina, não o do grupo de trabalho",
        ex.resposta_netbios(nbstat(("WORKGROUP", 0, 0x80), ("PC-EXEMPLO", 0x20, 0), ("PC-EXEMPLO", 0, 0))) == "PC-EXEMPLO")
confere("NetBIOS: resposta cortada não derruba", ex.resposta_netbios(nbstat(("PC-EXEMPLO", 0, 0))[:60]) is None)
confere("nome limpo: primeiro rótulo, sem controles", ex.limpar_nome("tv-sala.lan.") == "tv-sala"
        and ex.limpar_nome("ma\x07u.local") == "mau" and ex.limpar_nome(" . ") is None)

fim()
