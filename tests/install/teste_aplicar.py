"""O ./aplicar de verdade num servidor de mentira (--alvo, um ensaio: os comandos só são anotados). Ele grava
o que difere, guarda o que sobra, roda só os passos do que mudou de verdade, e o --desfazer volta
exatamente ao que era. Uma falha num passo desfaz sozinha. A memória da Atena só ganha a semente quando
falta; o daemon.json e uma stack que não existe ficam de fora."""
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "install"))
import estado  # noqa: E402

tmp = tempfile.mkdtemp(prefix="teste-aplicar-")
ALVO = f"{tmp}/servidor"
FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def montar():
    """Um servidor de mentira igual ao repositório: com a Atena, o lab, o painel e o SSH endurecido."""
    shutil.rmtree(ALVO, ignore_errors=True)
    texto = open(os.path.join(RAIZ, "atena.conf.example")).read()
    for chave, valor in (("ATENA_PAINEL_CASA", "sim"), ("ATENA_TAILSCALE", "sim"), ("ATENA_PC_IP", "192.168.0.50")):
        texto = re.sub(rf"^{chave}=.*$", f"{chave}={valor}", texto, flags=re.M)
    os.makedirs(f"{ALVO}/etc/atena")
    open(f"{ALVO}/etc/atena/atena.conf", "w").write(texto)
    for pasta in ("srv/agents/hermes", "var/lib/atena-claude", "srv/core/painel", "etc/ssh/sshd_config.d"):
        os.makedirs(f"{ALVO}/{pasta}")
    open(f"{ALVO}/etc/ssh/sshd_config.d/00-atena-hardening.conf", "w").write("")
    conf = estado.ler_conf(f"{ALVO}/etc/atena/atena.conf")
    itens, _ = estado.desejado(RAIZ, conf, estado.instalado(ALVO))
    for i in itens:
        p = estado.no_alvo(ALVO, i.destino)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(i.conteudo if i.conteudo is not None else b"o que a Atena lembra\n")
        # sem modo no estado: a memória da Atena com 600, e o resto (as stacks) como o administrador deixou
        os.chmod(p, i.modo if i.modo is not None else 0o600 if i.conteudo is None else 0o664)


def foto():
    """Cada arquivo do servidor de mentira (fora os backups e a trava): conteúdo e modo."""
    tudo = {}
    for base, pastas, nomes in os.walk(ALVO):
        rel = os.path.relpath(base, ALVO)
        if rel.startswith(("var/backups", "run")):
            continue
        for n in nomes:
            p = os.path.join(base, n)
            tudo[os.path.relpath(p, ALVO)] = (open(p, "rb").read(), os.stat(p).st_mode & 0o7777)
        for n in pastas:
            rel_pasta = os.path.relpath(os.path.join(base, n), ALVO)
            if not rel_pasta.startswith(("var/backups", "run")):
                tudo[rel_pasta + "/"] = (None, os.stat(os.path.join(base, n)).st_mode & 0o7777)
    return tudo


def aplicar(*args, falha=None):
    env = dict(os.environ)
    if falha:
        env["ATENA_APLICAR_ENSAIO_FALHA"] = falha
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "aplicar"), "--alvo", ALVO, "--sem-dono", *args],
                       capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL, env=env)
    return r.returncode, r.stdout, r.stderr


def escrever(rel, dados, modo="w"):
    with open(f"{ALVO}{rel}", modo) as f:
        f.write(dados)


def estragos():
    escrever("/usr/local/lib/atena-executor/atena_executor/stacks.py", "\nIMAGEM_LIVRE = True\n", "a")
    os.remove(f"{ALVO}/usr/local/sbin/atena-telegram")
    escrever("/etc/systemd/system/atena-executor.service.d/leitura.conf", "[Service]\nProtectHome=read-only\n")
    escrever("/usr/local/sbin/atena-executor.antes-aprovacao", "velho\n")
    escrever("/etc/systemd/system/atena-vigia.timer", "# só um comentário a mais\n", "a")
    os.chmod(f"{ALVO}/usr/local/sbin/atena-reconciliar", 0o700)
    escrever("/opt/atena/stacks/core/painel/app/public/velho.js", "// sobrou\n")
    escrever("/opt/atena/stacks/ai/litellm/config.yaml", "\n# a mais, à mão\nfoo: 1\n", "a")
    os.remove(f"{ALVO}/opt/atena/stacks/core/painel/app/public/zonas.js")
    escrever("/opt/atena/stacks/ai/ollama/compose.yaml", "# só um comentário\n", "a")
    escrever("/etc/ssh/sshd_config.d/00-atena-hardening.conf", "# comentário do SSH\n", "a")
    os.remove(f"{ALVO}/srv/agents/hermes/memories/USER.md")
    escrever("/srv/agents/hermes/memories/MEMORY.md", "a memória que ela escreveu\n")
    d = json.load(open(f"{ALVO}/etc/docker/daemon.json"))
    d["live-restore"] = False
    escrever("/etc/docker/daemon.json", json.dumps(d))
    shutil.rmtree(f"{ALVO}/opt/atena/stacks/apps/open-webui")


# --- igual: nada a fazer
montar()
rc, saida, erro = aplicar("--sim")
confere("servidor igual: nada a aplicar, sai com 0, sem backup", rc == 0 and "Nada a aplicar" in saida
        and not os.path.exists(f"{ALVO}/var/backups"), saida + erro)

# --- aplicar
estragos()
antes = foto()
rc, saida, erro = aplicar()
confere("sem --sim e sem terminal: não aplica, pede o --sim, sai com 2", rc == 2 and "--sim" in erro and foto() == antes,
        saida + erro)
rc, saida, erro = aplicar("--sim")
confere("aplica: sai com 0 e mostra o plano antes", rc == 0 and "grava (" in saida and "guarda no backup (" in saida
        and "fica como está (" in saida and "Pronto:" in saida, saida + erro)
anotados = [linha.split("ensaio: ", 1)[1] for linha in saida.split("\n") if "ensaio: " in linha]
confere("o systemd relê as unidades e o executor reinicia (mudou de verdade)",
        "systemctl daemon-reload" in anotados and "systemctl try-restart atena-executor.service" in anotados, anotados)
confere("por último, com tudo de pé, os tokens ganham as ações novas do catálogo",
        anotados[-1:] == ["atena-executor token-acertar"], anotados)
confere("o que mudou só nos comentários não reinicia (atena-vigia.timer, ollama)",
        not any("atena-vigia.timer" in c for c in anotados) and not any("ollama" in c for c in anotados), anotados)
confere("o SSH confere a configuração, e não recarrega (só comentário)",
        any("sshd -t" in c for c in anotados) and not any("ssh.service" in c for c in anotados), anotados)
confere("o LiteLLM (config.yaml mudou) reinicia e sobe esperando ficar saudável",
        "docker compose restart (em /opt/atena/stacks/ai/litellm)" in anotados
        and "docker compose up -d --wait --wait-timeout 300 (em /opt/atena/stacks/ai/litellm)" in anotados, anotados)
confere("o painel (sobrou um arquivo no app) sobe de novo com --build, sem reiniciar antes",
        any(c.startswith("docker compose up -d --build --wait") for c in anotados)
        and "docker compose restart (em /opt/atena/stacks/core/painel)" not in anotados, anotados)

r = {x.caminho: x for x in estado.conferir(RAIZ, ALVO, donos=False)[0]}
resta = sorted(c for c, x in r.items() if x.estado in ("difere", "falta", "sobra"))
confere("depois: só o que fica como está (o daemon.json e a stack que não existe)",
        "/etc/docker/daemon.json" in resta and all(c == "/etc/docker/daemon.json" or "/apps/open-webui/" in c for c in resta),
        resta)
confere("o arquivo de stack trocado fica com o modo que tinha (664), e não só para o root",
        os.stat(f"{ALVO}/opt/atena/stacks/ai/litellm/config.yaml").st_mode & 0o777 == 0o664)
zonas = os.path.join(RAIZ, "stacks", "core", "painel", "app", "public", "zonas.js")
confere("o arquivo de stack que faltava volta com o modo do repositório (o container o lê)",
        os.stat(f"{ALVO}/opt/atena/stacks/core/painel/app/public/zonas.js").st_mode & 0o777 == os.stat(zonas).st_mode & 0o777
        and os.stat(zonas).st_mode & 0o004)
confere("a stack que não existe não foi criada", not os.path.exists(f"{ALVO}/opt/atena/stacks/apps/open-webui"))
semente = open(os.path.join(RAIZ, "hermes", "memoria", "USER.md"), "rb").read()
confere("a memória que faltava ganhou a semente, com modo 600",
        open(f"{ALVO}/srv/agents/hermes/memories/USER.md", "rb").read() == semente
        and os.stat(f"{ALVO}/srv/agents/hermes/memories/USER.md").st_mode & 0o777 == 0o600)
confere("e a que existia, escrita por ela, ficou como estava",
        open(f"{ALVO}/srv/agents/hermes/memories/MEMORY.md").read() == "a memória que ela escreveu\n")
backups = os.listdir(f"{ALVO}/var/backups/atena-aplicar")
manifesto = json.load(open(f"{ALVO}/var/backups/atena-aplicar/{backups[0]}/manifesto.json"))
confere("um backup, com o que foi criado e o que foi guardado",
        len(backups) == 1 and "usr/local/sbin/atena-telegram" in manifesto["criados"]
        and "/etc/systemd/system/atena-executor.service.d/leitura.conf" in manifesto["guardados"], manifesto)

# --- desfazer
rc, saida, erro = aplicar("--desfazer")
confere("--desfazer: sai com 0, e o servidor volta exatamente ao que era (conteúdo e modo)",
        rc == 0 and "Desfeito" in saida and foto() == antes,
        sorted(set(foto().items()) ^ set(antes.items()))[:5] if foto() != antes else saida + erro)
rc, saida, erro = aplicar("--backups")
confere("--backups: o backup aparece como desfeito", rc == 0 and "desfeito em" in saida, saida)
rc, saida, erro = aplicar("--desfazer")
confere("--desfazer de novo: não há o que desfazer, sai com 2", rc == 2 and "não há o que desfazer" in erro, erro)

# --- uma falha num passo desfaz sozinha
rc, saida, erro = aplicar("--sim", falha="atena-executor")
confere("um passo que falha (o executor não sobe): sai com 1 e desfaz sozinho", rc == 1 and "voltou ao que era" in erro
        and foto() == antes, saida + erro)

# --- por parte
rc, saida, erro = aplicar("--sim", "--parte", "executor")
r = {x.caminho: x for x in estado.conferir(RAIZ, ALVO, donos=False)[0]}
confere("--parte executor: grava só o executor", rc == 0
        and r["/usr/local/lib/atena-executor/atena_executor/stacks.py"].estado == "igual"
        and r["/usr/local/sbin/atena-telegram"].estado == "falta", saida + erro)
confere("e reinicia só o executor (e acerta os tokens)", "ensaio: systemctl try-restart atena-executor.service" in saida
        and "ensaio: atena-executor token-acertar" in saida
        and "daemon-reload" not in saida and "docker compose" not in saida, saida)

# --- a trava: um aplicar de cada vez
os.makedirs(f"{ALVO}/run", exist_ok=True)
with open(f"{ALVO}/run/atena-aplicar.lock", "w") as trava:
    fcntl.flock(trava, fcntl.LOCK_EX)
    rc, saida, erro = aplicar("--sim")
confere("com outro aplicar rodando: não começa, sai com 2", rc == 2 and "outro ./aplicar" in erro, erro)

# --- sem sudo, no servidor de verdade
if os.geteuid() != 0:
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "aplicar"), "--sim"], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL)
    confere("sem sudo, no servidor de verdade: pede o sudo e não começa", r.returncode == 2 and "sudo" in r.stderr, r.stderr)

shutil.rmtree(tmp)
print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
