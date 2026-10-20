"""Ajudantes dos testes do lab: carregam o runner e a ponte apontando para pastas temporárias."""
import importlib.machinery
import os
import shutil
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FALHAS = []
SESSAO = "11111111-2222-3333-4444-555555555555"


def carregar(nome, *caminho):
    sys.dont_write_bytecode = True
    return importlib.machinery.SourceFileLoader(nome, os.path.join(RAIZ, *caminho)).load_module()


def runner(contas="pessoal trabalho", troca=None):
    """O runner como módulo, com a base, os projetos e o atena.conf numa pasta temporária."""
    rn = carregar("runner", "host", "sbin", "atena-claude-runner")
    tmp = tempfile.mkdtemp(prefix="teste-lab-")
    base, projetos = f"{tmp}/base", f"{tmp}/projetos"
    for d in ("fila", "resultados", "registros", *(f"contas/{c}" for c in contas.replace(",", " ").split())):
        os.makedirs(f"{base}/{d}", exist_ok=True)
    os.makedirs(projetos)
    os.chmod(projetos, 0o2775)   # como o instalador cria /srv/lab/projetos
    shutil.copy(os.path.join(RAIZ, "host", "lab", "gitconfig"), f"{base}/.gitconfig")
    with open(f"{tmp}/atena.conf", "w") as f:
        f.write(f'ATENA_CLAUDE_CONTAS="{contas}"\nATENA_TZ=America/Sao_Paulo\n'
                + (f"ATENA_CLAUDE_TROCA={troca}\n" if troca else ""))
    rn.BASE, rn.PROJETOS, rn.CONF = base, projetos, f"{tmp}/atena.conf"
    return rn, tmp


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def fim():
    print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
    sys.exit(1 if FALHAS else 0)
