"""As habilidades da Atena (servidor-atena e lab) documentam exatamente as ações que o executor tem."""
import glob
import importlib.machinery
import os
import re
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.dont_write_bytecode = True
ex = importlib.machinery.SourceFileLoader("executor", os.path.join(RAIZ, "host", "sbin", "atena-executor")).load_module()
texto = ""
for caminho in sorted(glob.glob(os.path.join(RAIZ, "hermes", "skills", "atena", "*", "SKILL.md"))):
    with open(caminho) as f:
        texto += f.read()
citadas = {a for a in re.findall(r"`([a-z]+\.[a-z]+)`", texto) if a.split(".")[1] not in ("md", "py", "yaml", "conf", "json")}
falta = sorted(set(ex.ACOES) - citadas)
sobra = sorted(citadas - set(ex.ACOES))
print("ações sem explicação nas habilidades:", falta or "nenhuma")
print("ações nas habilidades que o executor não tem:", sobra or "nenhuma")
sys.exit(1 if falta or sobra else 0)
