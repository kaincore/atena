"""As habilidades da Atena (servidor-atena e lab) documentam exatamente as ações que o executor tem."""
import glob
import os
import re
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "tests"))
from pacote_executor import carregar_executor  # noqa: E402

ex = carregar_executor()
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
