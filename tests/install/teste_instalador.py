"""O install.sh escolhe o atena.conf: o da pasta do repositório, quando há um, ou o do servidor
(/etc/atena/atena.conf). Roda o install.sh de verdade, com uma etapa de mentira no lugar das outras."""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
tmp = tempfile.mkdtemp(prefix="teste-instalador-")
SERVIDOR = f"{tmp}/etc/atena/atena.conf"
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


# uma cópia do instalador com o /etc/atena/atena.conf apontando para a pasta temporária e uma etapa só,
# que diz qual atena.conf leu
REPO = f"{tmp}/repo"
os.makedirs(f"{REPO}/install")
fonte = open(os.path.join(RAIZ, "install.sh")).read().replace("/etc/atena/atena.conf", SERVIDOR)
open(f"{REPO}/install.sh", "w").write(fonte)
shutil.copy(os.path.join(RAIZ, "install", "lib.sh"), f"{REPO}/install/lib.sh")
open(f"{REPO}/install/00-mostrar.sh", "w").write('echo "CONF=$CONF IP=$ATENA_LAN_IP"\n')
exemplo = open(os.path.join(RAIZ, "atena.conf.example")).read()


def instalar():
    r = subprocess.run(["bash", f"{REPO}/install.sh"], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout, r.stderr


os.makedirs(os.path.dirname(SERVIDOR))
open(SERVIDOR, "w").write(exemplo.replace("ATENA_LAN_IP=192.168.0.10", "ATENA_LAN_IP=192.168.0.20"))
rc, saida, erro = instalar()
confere("sem atena.conf na pasta: lê o do servidor", rc == 0 and f"CONF={SERVIDOR} IP=192.168.0.20" in saida, saida + erro)

open(f"{REPO}/atena.conf", "w").write(exemplo)
rc, saida, erro = instalar()
confere("com atena.conf na pasta: ele vale (e depois vira o do servidor)",
        rc == 0 and f"CONF={REPO}/atena.conf IP=192.168.0.10" in saida, saida + erro)

os.remove(f"{REPO}/atena.conf")
os.remove(SERVIDOR)
rc, saida, erro = instalar()
confere("sem nenhum dos dois: para e diz como criar", rc != 0 and "cp atena.conf.example atena.conf" in erro, erro)

etapa30 = open(os.path.join(RAIZ, "install", "30-zonas.sh")).read()
confere("a etapa 30 não copia o atena.conf do servidor por cima dele mesmo",
        '[ "$CONF" = /etc/atena/atena.conf ] || instalar_arquivo "$CONF" /etc/atena/atena.conf' in etapa30)

shutil.rmtree(tmp)
print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
