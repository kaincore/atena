"""O compose da Atena monta a personalidade (SOUL.md) e as habilidades dela (skills/atena) só para leitura,
sem deixar o Docker criar uma pasta no lugar de um arquivo que falta, e o resto do espaço dela continua
gravável (a memória, as notas, as entregas)."""
import os
import sys

import yaml

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "install"))
import estado  # noqa: E402
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


# o compose como o instalador o põe no servidor, com os valores do atena.conf.example
modelo = os.path.join(RAIZ, "stacks", "agents", "hermes", "compose.yaml")
conf = estado.ler_conf(os.path.join(RAIZ, "atena.conf.example"))
compose = yaml.safe_load(estado.renderizar(open(modelo, "rb").read(), conf, modelo))
volumes = compose["services"]["hermes"]["volumes"]
longos = {v["target"]: v for v in volumes if isinstance(v, dict)}
curtos = [v for v in volumes if isinstance(v, str)]
for alvo, origem in (("/opt/data/SOUL.md", "/srv/agents/hermes/SOUL.md"),
                     ("/opt/data/skills/atena", "/srv/agents/hermes/skills/atena")):
    v = longos.get(alvo, {})
    confere(f"{alvo}: só leitura, do arquivo do servidor", v.get("type") == "bind" and v.get("source") == origem
            and v.get("read_only") is True, v)
    confere(f"{alvo}: sem o arquivo, o container não sobe (o Docker não cria uma pasta no lugar)",
            v.get("bind", {}).get("create_host_path") is False, v)
confere("o espaço da Atena continua gravável (memória, notas, entregas)", "/srv/agents/hermes:/opt/data" in curtos, curtos)
confere("nenhuma outra montagem da Atena é só leitura sem querer",
        sorted(longos) == ["/opt/data/SOUL.md", "/opt/data/skills/atena"], sorted(longos))

# o instalador põe os arquivos antes de subir o container (sem eles, o compose não sobe)
etapa = open(os.path.join(RAIZ, "install", "86-hermes.sh")).read()
confere("o 86-hermes.sh copia o SOUL e as habilidades antes do docker compose up",
        etapa.index("copiar_hermes SOUL.md") < etapa.index("docker compose up")
        and etapa.index("copiar_hermes skills/atena/servidor-atena/SKILL.md") < etapa.index("docker compose up"))

print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
