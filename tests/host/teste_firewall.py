"""O atena-docker-firewall contra um iptables de mentira: as regras saem do atena.conf, e o LiteLLM só
chega ao PC da rede de casa quando há ATENA_PC_IP, e só na porta do LM Studio."""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
tmp = tempfile.mkdtemp(prefix="teste-firewall-")
CONF, REGRAS, BIN = f"{tmp}/atena.conf", f"{tmp}/regras", f"{tmp}/bin"
os.makedirs(BIN)
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


fonte = open(os.path.join(RAIZ, "host", "sbin", "atena-docker-firewall")).read().replace("/etc/atena/atena.conf", CONF)
open(f"{tmp}/firewall", "w").write(fonte)
for nome in ("iptables", "conntrack"):   # anotam cada chamada e dão certo
    open(f"{BIN}/{nome}", "w").write(f'#!/bin/sh\necho "{nome} $*" >> {REGRAS}\n')
    os.chmod(f"{BIN}/{nome}", 0o755)
exemplo = open(os.path.join(RAIZ, "atena.conf.example")).read()


def firewall(**trocas):
    texto = exemplo
    for chave, valor in trocas.items():
        texto = texto.replace(f"\n{chave}=", f"\n{chave}={valor}\n#")
    open(CONF, "w").write(texto)
    if os.path.exists(REGRAS):
        os.remove(REGRAS)
    r = subprocess.run(["sh", f"{tmp}/firewall"], capture_output=True, text=True, timeout=30,
                       env=dict(os.environ, PATH=f"{BIN}:{os.environ['PATH']}"))
    return r.returncode, open(REGRAS).read().split("\n"), r.stderr


rc, regras, erro = firewall()
confere("sem PC: roda, com o DNS e a entrada da rede de casa do atena.conf", rc == 0
        and "iptables -A ATENA-EGRESS -d 192.168.0.1 -p udp --dport 53 -j RETURN" in regras
        and any("-i enp3s0 -s 192.168.0.0/24" in r and "--ctorigdst 192.168.0.10" in r for r in regras), erro)
confere("sem PC: nenhuma exceção para a rede de casa", not any("10.10.20.0/24 -d 192." in r for r in regras))

rc, regras, erro = firewall(ATENA_PC_IP="192.168.0.50", ATENA_PC_PORTA="1236")
pc = "iptables -A ATENA-EGRESS -s 10.10.20.0/24 -d 192.168.0.50 -p tcp --dport 1236 -j RETURN"
confere("com PC: a zona ai chega ao PC, só na porta do LM Studio", rc == 0 and pc in regras, regras)
bloqueio = next(i for i, r in enumerate(regras) if r.startswith("iptables -A ATENA-EGRESS -d 192.168.0.0/16 -j DROP"))
confere("e a exceção vem antes do bloqueio da rede de casa", regras.index(pc) < bloqueio)

shutil.rmtree(tmp)
print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
