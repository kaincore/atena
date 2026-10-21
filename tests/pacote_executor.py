"""O executor para os testes: o pacote atena_executor (um módulo por assunto) visto como um módulo só,
como ele era antes da divisão. ex.nome lê o nome no módulo que o tem; ex.nome = valor troca em todos os
módulos que o têm (o que o define e os que o importaram), para a troca valer em qualquer lugar.
Cada carga é um pacote novo, com nome próprio: dois executores no mesmo teste não dividem estado."""
import importlib
import importlib.util
import os
import pkgutil
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CARGAS = []


class Executor:
    def __init__(self, modulos):
        object.__setattr__(self, "_modulos", modulos)

    def __getattr__(self, nome):
        for m in self._modulos:
            if nome in vars(m):
                return vars(m)[nome]
        raise AttributeError(f"o executor não tem {nome}")

    def __setattr__(self, nome, valor):
        donos = [m for m in self._modulos if nome in vars(m)]
        if not donos:
            raise AttributeError(f"o executor não tem {nome}")
        for m in donos:
            setattr(m, nome, valor)


def carregar_executor():
    """ATENA_EXECUTOR=<pasta> testa outro pacote (ex.: /usr/local/lib/atena-executor, o instalado)."""
    pasta = os.path.join(os.environ.get("ATENA_EXECUTOR") or os.path.join(RAIZ, "host", "executor"), "atena_executor")
    CARGAS.append(pasta)
    nome = f"atena_executor_teste{len(CARGAS)}"
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(nome, os.path.join(pasta, "__init__.py"),
                                                  submodule_search_locations=[pasta])
    pacote = importlib.util.module_from_spec(spec)
    sys.modules[nome] = pacote
    spec.loader.exec_module(pacote)
    return Executor([importlib.import_module(f"{nome}.{m.name}") for m in pkgutil.iter_modules([pasta])])
