"""Ronda da Atena: fonte barata do monitor do cron do Hermes.

Imprime só o que está fora do normal, sem horários nem números que mudam à toa. O Hermes compara a
saída com a anterior e só acorda a Atena (e gasta API) quando ela muda. Toda vez que acorda, ela lê a
lista inteira: por isso uma linha que já foi dita não pode ficar nela esperando a próxima mudança.
"""
import http.client
import json
import os
import socket
import time

SOCKET = "/run/atena-executor/executor.sock"
ESTADO = "/opt/data/cron/ronda-estado.json"   # o que a ronda lembra de uma volta para a outra
CARENCIA = 15 * 60   # a unidade com falha que roda de novo (por um timer) segue na lista por 15 min


class Conexao(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(60)
        self.sock.connect(SOCKET)


def acao(nome):
    with open("/opt/data/executor.token") as f:
        token = f.read().strip()
    c = Conexao("x")
    c.request("POST", "/acao/" + nome, body=json.dumps({"params": {}, "origem": "ronda"}),
              headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    r = json.loads(c.getresponse().read())
    if not r.get("ok"):
        raise RuntimeError(f"o executor recusou {nome}: {r.get('erro')}")
    return r["resultado"]


def ler_estado():
    try:
        with open(ESTADO) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def gravar_estado(estado):
    """Grava o estado; devolve o erro, ou None se gravou."""
    try:
        with open(ESTADO + ".tmp", "w") as f:
            json.dump(estado, f)
        os.replace(ESTADO + ".tmp", ESTADO)
    except OSError as e:
        return type(e).__name__
    return None


def unidades_com_falha(estado):
    """As unidades do systemd com falha. A que um timer roda de novo sai do estado failed enquanto roda
    e volta a ele quando falha outra vez, e cada troca acordaria a Atena: ela só sai da lista depois
    de 15 min sem falhar."""
    agora = time.time()
    vistas = estado.setdefault("unidades", {})
    for unidade in acao("status.sistema").get("falhas", []):
        vistas[unidade] = agora
    for unidade, quando in list(vistas.items()):
        if agora - quando > CARENCIA:
            del vistas[unidade]
    return sorted(vistas)


def problemas(estado):
    achados = []
    for c in acao("status.servicos"):
        onde = f"{c['container']} (stack {c['stack']}, zona {c['zona']})"
        if c["estado"] != "running":
            achados.append(f"container {onde}: {c['estado']}")
        elif "unhealthy" in c["status"]:
            achados.append(f"container {onde}: doente (unhealthy)")
    for unidade in unidades_com_falha(estado):
        achados.append(f"unidade do systemd com falha: {unidade}")
    recursos = acao("status.recursos")
    for ponto, d in recursos["discos"].items():
        uso = 100 - 100 * d["livre_gb"] / d["total_gb"]
        limite = next((n for n in (95, 90, 85) if uso >= n), None)
        if limite:
            achados.append(f"disco {ponto} acima de {limite}%")
    if recursos["ram_disponivel_mb"] < 0.10 * recursos["ram_total_mb"]:
        achados.append("RAM disponível abaixo de 10%")
    gpu = recursos.get("gpu")
    if gpu and gpu["temperatura_c"] >= 85:
        achados.append("GPU acima de 85 °C")
    temperaturas = recursos.get("temperaturas") or {}
    if (temperaturas.get("cpu_c") or 0) >= 85:
        achados.append("CPU acima de 85 °C")
    if (temperaturas.get("nvme_c") or 0) >= 70:
        achados.append("NVMe acima de 70 °C")
    return achados


def claude_code(estado):
    """O trabalho do Claude Code que acabou de terminar, numa volta só: a que acorda a Atena para o resumo.
    Na volta seguinte a linha sai da lista, e a Atena não repete o resumo a cada outra mudança."""
    terminados = {"concluido", "falhou", "recusado", "expirado", "cancelado"}
    ultimo = next((t for t in acao("claude.trabalhos")["trabalhos"]   # do mais novo para o mais velho
                   if t["estado"] in terminados), None)
    novo = ultimo is not None and "claude_avisado" in estado and ultimo["id"] != estado["claude_avisado"]
    estado["claude_avisado"] = ultimo and ultimo["id"]   # na primeira volta, só guarda: não avisa o que já havia
    if not novo:
        return []
    return [f"Claude Code: último trabalho terminado = {ultimo['id']} ({ultimo['estado']}, projeto {ultimo['projeto']})"]


def perguntas_claude():
    """Perguntas do Claude Code sem resposta: acorda a Atena quando chega uma e aos 10 min sem resposta."""
    linhas = []
    for q in acao("claude.perguntas"):
        if q["esperando_min"] >= 10:
            linhas.append(f"Claude Code pergunta {q['id']} (projeto {q['projeto']}): o dono não respondeu em 10 min")
        else:
            linhas.append(f"Claude Code pergunta {q['id']} (projeto {q['projeto']}): esperando o dono")
    return linhas


estado = ler_estado() or {}
try:
    lista = problemas(estado)
except Exception as e:
    lista = [f"a ronda não conseguiu falar com o executor ({type(e).__name__})"]
try:
    trabalhos = claude_code(estado)
except Exception:
    trabalhos = []   # sem Claude Code liberado no token: a ronda segue só com o servidor
try:
    trabalhos += perguntas_claude()
except Exception:
    pass
erro = gravar_estado(estado)
if erro:
    lista.append(f"a ronda não conseguiu guardar o que já avisou em {ESTADO} ({erro})")
print("\n".join(sorted(lista)) if lista else "tudo normal")
if trabalhos:
    print("\n".join(trabalhos))
