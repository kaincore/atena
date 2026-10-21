"""O atena.conf, o registro, os comandos que o executor roda e o Erro que vira a resposta HTTP."""

import json
import subprocess


CONF = "/etc/atena/atena.conf"
LIMITE_SAIDA = 10 * 1024
ZONAS = {"prod", "core", "apps", "ai", "agents", "lab"}


def log(**campos):
    print(json.dumps(campos, ensure_ascii=False), flush=True)  # vai para o journal


def ler_conf():
    conf = {}
    with open(CONF) as f:
        for linha in f:
            linha = linha.split("#", 1)[0].strip()
            if "=" in linha:
                chave, valor = linha.split("=", 1)
                conf[chave.strip()] = valor.strip().strip('"')
    return conf


def ler(caminho):
    with open(caminho) as f:
        return f.read().strip()


PROCESSOS = {}   # projeto → construção em andamento (app.cancelar interrompe)


def rodar(argv, tempo=30, cancelavel=None):
    if cancelavel is None:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=tempo)
        return r.returncode, (r.stdout + r.stderr)[-LIMITE_SAIDA:]
    with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
        PROCESSOS[cancelavel] = proc
        try:
            saida, _ = proc.communicate(timeout=tempo)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise
        finally:
            PROCESSOS.pop(cancelavel, None)
    return proc.returncode, saida[-LIMITE_SAIDA:]


class Erro(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status


class Cancelado(Erro):
    """O dono mandou parar no meio (app.cancelar)."""
    def __init__(self, mensagem="cancelado pelo dono"):
        super().__init__(409, mensagem)
