"""A habilidade servidor-atena documenta exatamente as ações que o executor tem."""
import importlib.machinery
import os
import re
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.dont_write_bytecode = True
ex = importlib.machinery.SourceFileLoader("executor", os.path.join(RAIZ, "host", "sbin", "atena-executor")).load_module()
texto = open(os.path.join(RAIZ, "hermes", "skills", "atena", "servidor-atena", "SKILL.md")).read()
citadas = {a for a in re.findall(r"`([a-z]+\.[a-z]+)`", texto) if a.split(".")[1] not in ("md", "py", "yaml", "conf")}
falta = sorted(set(ex.ACOES) - citadas)
sobra = sorted(citadas - set(ex.ACOES))
print("ações sem explicação na habilidade:", falta or "nenhuma")
print("ações na habilidade que o executor não tem:", sobra or "nenhuma")
sys.exit(1 if falta or sobra else 0)
