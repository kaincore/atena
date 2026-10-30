"""O catálogo das ações: cada uma diz o que faz, o risco e quem a usa. O destrutivo vira pedido (sem isso, o
celular não teria o que aprovar), e o atena-executor acoes dá ao instalador a lista de cada perfil."""
import contextlib
import io
import os
import re
import sys

from comum import RAIZ, carregar, confere, fim

ex, tmp = carregar()
erros = {n: a for n, a in ex.ACOES.items() if a.risco not in ex.RISCOS}
confere("todo risco é consulta, muda ou destrutivo", not erros, erros)
confere("toda ação tem ajuda e um perfil (painel ou atena)",
        all(a.ajuda.strip() and a.perfis and a.perfis <= {"painel", "atena"} for a in ex.ACOES.values()))
sem_pedido = [n for n, a in ex.ACOES.items() if a.risco == ex.DESTRUTIVO and a.preparar is None]
confere("toda ação destrutiva vira pedido (o celular tem o que aprovar)", not sem_pedido, sem_pedido)
confere("há ação destrutiva (o app.apagar)", ex.ACOES["app.apagar"].risco == ex.DESTRUTIVO)
lab_errado = [n for n, a in ex.ACOES.items() if (a.modulo == ex.LAB) != n.startswith(("claude.", "app.", "receita."))]
confere("o módulo lab é o das ações claude.*, app.* e receita.*", not lab_errado, lab_errado)
confere("as internas não estão no catálogo (ninguém as pede)", not set(ex.INTERNAS) & set(ex.ACOES))


def acoes(perfil):
    saida = io.StringIO()
    argv = sys.argv
    sys.argv = ["atena-executor", "acoes", perfil]
    try:
        with contextlib.redirect_stdout(saida):
            ex.principal()
    finally:
        sys.argv = argv
    return saida.getvalue().strip().split(",")


painel, atena, atena_lab = acoes("painel"), acoes("atena"), acoes("atena-lab")
confere("atena-executor acoes: as listas de cada perfil", painel == ex.do_perfil("painel")
        and atena == ex.do_perfil("atena") and atena_lab == ex.do_perfil("atena-lab"))
confere("a Atena e o lab não se repetem, e juntas são tudo o que é dela",
        not set(atena) & set(atena_lab) and set(atena) | set(atena_lab) == {n for n, a in ex.ACOES.items() if "atena" in a.perfis})
confere("o painel não tem o que só a Atena usa (arquivo.entregar, local.processar, claude.responder)",
        not {"arquivo.entregar", "local.processar", "claude.responder"} & set(painel))
confere("o que só o painel usa: a central e o aviso da agenda",
        {"aprovacoes.lista", "aprovacoes.decidir", "atividade.lista", "aviso.celular"} <= set(painel)
        and not {"aprovacoes.decidir", "aviso.celular"} & set(atena + atena_lab))
with contextlib.suppress(SystemExit), contextlib.redirect_stderr(io.StringIO()):
    saida = io.StringIO()
    sys.argv = ["atena-executor", "acoes", "outro"]
    with contextlib.redirect_stdout(saida):
        ex.principal()
confere("perfil desconhecido: não imprime lista", "," not in saida.getvalue())

# o instalador monta os tokens pelo catálogo, sem lista própria
instalador = {n: open(os.path.join(RAIZ, "install", n)).read() for n in ("85-painel.sh", "86-hermes.sh", "88-lab.sh")}
confere("o 85-painel.sh pega as ações do painel no catálogo", "atena-executor acoes painel" in instalador["85-painel.sh"])
confere("o 86-hermes.sh e o 88-lab.sh pegam as da Atena", "atena-executor acoes atena)" in instalador["86-hermes.sh"]
        and "atena-executor acoes atena-lab" in instalador["88-lab.sh"])
# fora dos comentários, só o app.publicar, que a Atena pede ao celular por escolha (não é destrutivo)
listas = {n: [m for linha in t.split("\n") if not linha.lstrip().startswith("#")
              for m in re.findall(r"\b[a-z]+\.[a-z]+\b", linha.split(" # ")[0]) if m in ex.ACOES]
          for n, t in instalador.items()}
confere("e nenhuma etapa tem uma lista de ações à mão (fora o app.publicar, aprovado por escolha)",
        listas == {"85-painel.sh": [], "86-hermes.sh": [], "88-lab.sh": ["app.publicar"]}, listas)
fim()
