"""As regras das zonas em todos os composes do repositório (preenchidos com o atena.conf.example). O CI já
confere que eles abrem (docker compose config); aqui, que seguem o modelo:
- todo serviço fica na fatia da zona da pasta dele (os limites de CPU e RAM);
- porta publicada sempre com o IP na frente (127.0.0.1 ou o da rede de casa), nunca em todas as interfaces;
- as redes de fora são a da zona ou uma de serviço (svc-*);
- imagem com versão fixa; nada de privileged nem cap_add;
- network_mode e o socket do Docker só nas exceções conhecidas;
- healthcheck em todo serviço (a ronda e o reconciliador dependem dele), menos onde a imagem já traz o dela.
Uma exceção nova entra numa das listas abaixo, com o motivo."""
import glob
import os
import sys

import yaml

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "install"))
import estado  # noqa: E402

# serviço (zona/stack/serviço): o motivo
NETWORK_MODE = {"core/painel/painel": ("none", "o painel não tem rede: fala por dois sockets"),
                "core/beszel/beszel-agent": ("host", "o agente do Beszel mede a rede e os discos do servidor")}
SOCKET_DOCKER = {"core/dockge/dockge": "o Dockge sobe as stacks",
                 "core/beszel/beszel-agent": "o agente do Beszel lê os containers (só leitura)"}
HEALTHCHECK_DA_IMAGEM = {"apps/open-webui/open-webui": "a imagem do Open WebUI traz o healthcheck dela",
                         "core/dockge/dockge": "a imagem do Dockge traz o healthcheck dela"}
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


conf = estado.ler_conf(os.path.join(RAIZ, "atena.conf.example"))
achados, servicos = [], 0
for caminho in sorted(glob.glob(os.path.join(RAIZ, "stacks", "*", "*", "compose.yaml"))):
    zona, stack = caminho.split(os.sep)[-3:-1]
    cfg = yaml.safe_load(estado.renderizar(open(caminho, "rb").read(), conf, caminho))
    redes = {k: (v or {}) for k, v in (cfg.get("networks") or {}).items()}
    for chave, rede in redes.items():
        nome = rede.get("name", chave)
        if rede.get("external") and nome != f"zone-{zona}" and not nome.startswith("svc-"):
            achados.append(f"{zona}/{stack}: a rede {nome} não é da zona {zona} nem de serviço (svc-*)")
    for nome, s in cfg["services"].items():
        servicos += 1
        onde = f"{zona}/{stack}/{nome}"
        if s.get("cgroup_parent") != f"atena-{zona}.slice":
            achados.append(f"{onde}: cgroup_parent tem que ser atena-{zona}.slice")
        for porta in s.get("ports") or []:
            texto = porta if isinstance(porta, str) else str(porta.get("host_ip", "")) + ":"
            if texto.count(":") < 2 or texto.split(":")[0] not in ("127.0.0.1", conf["ATENA_LAN_IP"]):
                achados.append(f"{onde}: a porta {porta} precisa do IP na frente (127.0.0.1 ou {{{{ATENA_LAN_IP}}}})")
        imagem = str(s.get("image", ""))
        versao = imagem.rsplit("/", 1)[-1]
        if "@sha256:" not in imagem and (":" not in versao or versao.endswith(":latest")):
            achados.append(f"{onde}: a imagem {imagem} precisa de uma versão fixa")
        for chave in ("privileged", "cap_add"):
            if s.get(chave):
                achados.append(f"{onde}: {chave} não pode")
        modo = s.get("network_mode")
        if modo and NETWORK_MODE.get(onde, (None,))[0] != modo:
            achados.append(f"{onde}: network_mode {modo} só nas exceções conhecidas")
        volumes = [v if isinstance(v, str) else str(v.get("source", "")) for v in s.get("volumes") or []]
        if any("docker.sock" in v for v in volumes) and onde not in SOCKET_DOCKER:
            achados.append(f"{onde}: o socket do Docker só nas exceções conhecidas (equivale a root)")
        if "healthcheck" not in s and onde not in HEALTHCHECK_DA_IMAGEM:
            achados.append(f"{onde}: sem healthcheck (a ronda e o reconciliador não veem se ele travou)")
        if s.get("restart") != "unless-stopped":
            achados.append(f"{onde}: restart tem que ser unless-stopped (volta depois de um boot, menos o que você parou)")
confere(f"os {servicos} serviços dos composes do repositório seguem as regras das zonas", not achados, achados)
confere("e há o que conferir", servicos >= 10)
mortas = [k for k in {**dict.fromkeys(NETWORK_MODE), **SOCKET_DOCKER, **HEALTHCHECK_DA_IMAGEM}
          if not os.path.isfile(os.path.join(RAIZ, "stacks", *k.split("/")[:2], "compose.yaml"))]
confere("as exceções são de stacks que existem", not mortas, mortas)

print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
