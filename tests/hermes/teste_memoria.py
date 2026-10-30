"""A semente da memória da Atena (hermes/memoria) cabe nos limites do Hermes, está no formato dele, e nem
ela nem o SOUL e as habilidades trazem de volta o que já não vale (a memória antiga contradizia o SOUL,
e uma contradição assim já a fez recusar pedidos).

  python3 teste_memoria.py                       a semente, o SOUL e as habilidades do repositório
  python3 teste_memoria.py <pasta memories>      também a memória viva (ex.: /srv/agents/hermes/memories)
"""
import glob
import os
import re
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIMITES = {"USER.md": 1375, "MEMORY.md": 2200}   # user_char_limit e memory_char_limit do Hermes
SEPARADOR = "\n§\n"
# o que já foi verdade e deixou de ser: termo → o que vale agora
PROIBIDOS = {
    r"tsundere": "a personalidade tsundere saiu; ela é madura e perspicaz (SOUL)",
    r"deliver:? *origin": "lembretes e tarefas agendadas vão pelo ntfy (deliver: ntfy, SOUL)",
    r"n[ãa]o (foi )?iniciado": "o painel está no ar",
    r"\barca\.(lista|pegar|guardar)\b|porta 3002": "o Arca saiu do modelo (v0.24.0)",
    r"curl -s --unix-socket": "o executor se chama pelo acao.py, que mostra o código HTTP",
}
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def conferir_memoria(pasta, rotulo):
    for nome, limite in LIMITES.items():
        caminho = os.path.join(pasta, nome)
        confere(f"{rotulo}/{nome} existe", os.path.isfile(caminho))
        if not os.path.isfile(caminho):
            continue
        texto = open(caminho, encoding="utf-8").read()
        confere(f"{rotulo}/{nome} cabe no limite do Hermes ({len(texto)} de {limite} letras)", len(texto) <= limite)
        entradas = texto.split(SEPARADOR)
        confere(f"{rotulo}/{nome}: entradas separadas por § e nenhuma vazia",
                all(e.strip() and "§" not in e for e in entradas), [e[:40] for e in entradas])


def conferir_termos(arquivos):
    for caminho in arquivos:
        texto = open(caminho, encoding="utf-8").read()
        rel = os.path.relpath(caminho, RAIZ) if caminho.startswith(RAIZ) else caminho
        achados = [f"{m.group(0)!r}: {motivo}" for padrao, motivo in PROIBIDOS.items()
                   for m in [re.search(padrao, texto, re.I)] if m]
        confere(f"{rel} sem o que já não vale", not achados, "; ".join(achados))


conferir_memoria(os.path.join(RAIZ, "hermes", "memoria"), "semente")
conferir_termos(sorted(glob.glob(os.path.join(RAIZ, "hermes", "memoria", "*.md")))
                + [os.path.join(RAIZ, "hermes", "SOUL.md")]
                + sorted(glob.glob(os.path.join(RAIZ, "hermes", "skills", "**", "SKILL.md"), recursive=True)))
for pasta in sys.argv[1:]:
    conferir_memoria(pasta, pasta.rstrip("/"))
    conferir_termos([os.path.join(pasta, n) for n in LIMITES if os.path.isfile(os.path.join(pasta, n))])

print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
