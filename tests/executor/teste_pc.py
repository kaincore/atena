"""PC da rede de casa: estado, Wake-on-LAN e a chave SSH restrita (rede e SSH simulados)."""
import os

from comum import carregar, confere, erro, fim

ex, tmp = carregar()
ex.PC_HOSTS = f"{tmp}/pc-known-hosts"
open(ex.PC_HOSTS, "w").write("192.168.0.50 ssh-ed25519 AAAA\n")
CONF = {"ATENA_LAN_CIDR": "192.168.0.0/24", "ATENA_PC_IP": "192.168.0.50", "ATENA_PC_MAC": "00:11:22:33:44:55",
        "ATENA_PC_PORTA": "1234", "ATENA_PC_USUARIO": "atena-pc"}
ex.ler_conf = lambda: dict(CONF)
c = {"cliente": "hermes", "zonas": ["apps"], "acoes": []}

# --- estado: a porta do LM Studio e a tabela de vizinhos (ARP) ---
REDE = {"porta": False, "vizinho": "192.168.0.50 dev enp3s0 FAILED"}


def conectar_falso(endereco, timeout=None):
    if not REDE["porta"]:
        raise OSError("recusada")

    class Conexao:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    return Conexao()


ex.socket.create_connection = conectar_falso
ex.rodar = lambda argv, tempo=30: (0, REDE["vizinho"])
confere("PC desligado", ex.acao_pc_estado(c, {}) == {"ligado": False, "lm_studio": False})
REDE["vizinho"] = "192.168.0.50 dev enp3s0 lladdr 00:11:22:33:44:55 REACHABLE"
confere("placa de rede responde, LM Studio ainda não", ex.acao_pc_estado(c, {}) == {"ligado": True, "lm_studio": False})
REDE["porta"] = True
confere("LM Studio respondendo", ex.acao_pc_estado(c, {}) == {"ligado": True, "lm_studio": True})

# --- Wake-on-LAN ---
ENVIADOS = []


class SocketFalso:
    def __init__(self, *a):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def setsockopt(self, *a):
        pass

    def sendto(self, dados, destino):
        ENVIADOS.append((dados, destino))


original = ex.socket.socket
ex.socket.socket = SocketFalso
ex.acao_pc_ligar(c, {})
ex.socket.socket = original
dados, destino = ENVIADOS[0]
confere("pacote mágico: 6 x FF e o MAC 16 vezes", dados == b"\xff" * 6 + bytes.fromhex("001122334455") * 16)
confere("enviado para o broadcast da rede de casa", destino[0] == "192.168.0.255" and {d[1] for _, d in ENVIADOS} == {7, 9})
CONF["ATENA_PC_MAC"] = "00:11:22"
confere("MAC inválido: 500", erro(ex.acao_pc_ligar, c, {})[0] == 500)
CONF["ATENA_PC_MAC"] = "00:11:22:33:44:55"

# --- desligar, reiniciar e cancelar pela chave restrita ---
CENARIO = {"ligado": True, "resposta": None}
ex.acao_pc_estado = lambda cliente, params: {"ligado": CENARIO["ligado"], "lm_studio": CENARIO["ligado"]}
CHAMADAS = []
AVISO = "** WARNING: connection is not using a post-quantum key exchange algorithm.\n"


def ssh_falso(argv, tempo=30):
    CHAMADAS.append(argv)
    pedido = argv[-1]
    if CENARIO["resposta"] is not None:
        return CENARIO["resposta"]
    if pedido in ("desligar", "reiniciar", "cancelar"):
        return 0, AVISO + f"atena-pc: {pedido}\n"
    return 1, AVISO + "atena-pc: recusado\n"


ex.rodar = ssh_falso
r = ex.acao_pc_desligar(c, {})
confere("desligar: manda 'desligar' com a chave e o known_hosts fixos",
        r["desligando"] and CHAMADAS[-1][-1] == "desligar" and "StrictHostKeyChecking=yes" in CHAMADAS[-1]
        and f"UserKnownHostsFile={ex.PC_HOSTS}" in CHAMADAS[-1] and CHAMADAS[-1][-2] == "atena-pc@192.168.0.50", r)
r = ex.acao_pc_reiniciar(c, {})
confere("reiniciar: manda 'reiniciar'", r["reiniciando"] and CHAMADAS[-1][-1] == "reiniciar", r)
r = ex.acao_pc_cancelar(c, {})
confere("cancelar: manda 'cancelar'", r["cancelado"] and CHAMADAS[-1][-1] == "cancelar", r)

CENARIO["resposta"] = (0, "")   # a chave roda outra coisa no Windows
confere("PC que não responde 'atena-pc: <pedido>' dá erro (não finge sucesso)", erro(ex.acao_pc_reiniciar, c, {})[0] == 502)
CENARIO["resposta"] = (255, "Permission denied (publickey).")
status, msg = erro(ex.acao_pc_desligar, c, {})
confere("chave recusada: 502 com o motivo", status == 502 and "publickey" in msg, msg)
CENARIO["resposta"] = (255, "ssh: connect to host 192.168.0.50 port 22: No route to host")
confere("acabou de desligar (ARP ainda diz ligado): conta como desligado", ex.acao_pc_cancelar(c, {})["cancelado"] is False)
CENARIO["resposta"] = None

CENARIO["ligado"] = False
n = len(CHAMADAS)
confere("PC desligado: desligar não chama o SSH", ex.acao_pc_desligar(c, {})["desligando"] is False and len(CHAMADAS) == n)
confere("PC desligado: reiniciar sugere pc.ligar", "pc.ligar" in ex.acao_pc_reiniciar(c, {})["motivo"])
CENARIO["ligado"] = True

os.unlink(ex.PC_HOSTS)
confere("sem known_hosts fixado: 404", erro(ex.acao_pc_desligar, c, {})[0] == 404)
CONF["ATENA_PC_IP"] = ""
confere("sem PC no atena.conf: 404 em tudo", all(erro(f, c, {})[0] == 404 for f in (ex.acao_pc_ligar, ex.acao_pc_desligar)))

fim()
