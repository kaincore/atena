"""Ronda da Atena: fonte barata do monitor do cron do Hermes.

Imprime só o que está fora do normal, sem horários nem números que mudam à toa. O Hermes compara a
saída com a anterior e só acorda a Atena (e gasta API) quando ela muda.
"""
import http.client
import json
import socket

SOCKET = "/run/atena-executor/executor.sock"


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


def problemas():
    achados = []
    for c in acao("status.servicos"):
        onde = f"{c['container']} (stack {c['stack']}, zona {c['zona']})"
        if c["estado"] != "running":
            achados.append(f"container {onde}: {c['estado']}")
        elif "unhealthy" in c["status"]:
            achados.append(f"container {onde}: doente (unhealthy)")
    for unidade in acao("status.sistema").get("falhas", []):
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
    return achados


try:
    lista = problemas()
except Exception as e:
    lista = [f"a ronda não conseguiu falar com o executor ({type(e).__name__})"]
print("\n".join(sorted(lista)) if lista else "tudo normal")
