"""O catálogo das ações: cada uma diz o que faz, o risco e quem a usa. O destrutivo vira pedido (sem isso, o
celular não teria o que aprovar), e o atena-executor acoes dá a lista de cada perfil."""
import contextlib
import io
import sys

from comum import carregar, confere, fim

ex, tmp = carregar()
erros = {n: a for n, a in ex.ACOES.items() if a.risco not in ex.RISCOS}
confere("todo risco é consulta, muda ou destrutivo", not erros, erros)
confere("toda ação tem ajuda e um perfil (painel ou atena)",
        all(a.ajuda.strip() and a.perfis and a.perfis <= {"painel", "atena"} for a in ex.ACOES.values()))
sem_pedido = [n for n, a in ex.ACOES.items() if a.risco == ex.DESTRUTIVO and a.preparar is None]
confere("toda ação destrutiva vira pedido (o celular tem o que aprovar)", not sem_pedido, sem_pedido)
confere("há ação destrutiva (o app.apagar)", ex.ACOES["app.apagar"].risco == ex.DESTRUTIVO)
lab_errado = [n for n, a in ex.ACOES.items() if (a.modulo == ex.LAB) != n.startswith(("claude.", "app."))]
confere("o módulo lab é o das ações claude.* e app.*", not lab_errado, lab_errado)
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

fim()
