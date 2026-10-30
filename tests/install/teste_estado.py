"""O estado desejado (install/estado.py) e o ./aplicar --conferir: um servidor de mentira numa pasta
temporária, montado a partir do próprio estado, tem de sair igual; cada estrago nele aparece no lugar certo.
E o estado anda junto com as etapas do instalador: preenche, tira a GPU, monta o lab.json e usa os padrões
como elas, e todo arquivo do repositório que vai para o servidor está descrito nele."""
import glob
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

tmp = tempfile.mkdtemp(prefix="teste-estado-")
FALHAS = []
INSTALADOR = {os.path.basename(p): open(p).read() for p in glob.glob(os.path.join(RAIZ, "install", "*.sh"))}
TUDO = "\n".join(INSTALADOR.values())


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def escrever_conf(caminho, **trocas):
    """O atena.conf.example, com as trocas (ATENA_X="valor")."""
    texto = open(os.path.join(RAIZ, "atena.conf.example")).read()
    for chave, valor in trocas.items():
        texto, n = re.subn(rf"^{chave}=.*$", f"{chave}={valor}", texto, flags=re.M)
        if not n:
            texto += f"{chave}={valor}\n"
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    open(caminho, "w").write(texto)


def montar(alvo, opcoes=("hermes", "lab", "painel"), **trocas):
    """Um servidor de mentira em alvo: as pastas das opções e cada arquivo como o estado pede."""
    shutil.rmtree(alvo, ignore_errors=True)
    escrever_conf(f"{alvo}/etc/atena/atena.conf", **trocas)
    for pasta in {"hermes": "srv/agents/hermes", "lab": "var/lib/atena-claude", "painel": "srv/core/painel"}.values():
        if any(pasta.endswith(o) or o in pasta for o in opcoes):
            os.makedirs(f"{alvo}/{pasta}", exist_ok=True)
    conf = estado.ler_conf(f"{alvo}/etc/atena/atena.conf")
    itens, _ = estado.desejado(RAIZ, conf, estado.instalado(alvo))
    for i in itens:
        p = estado.no_alvo(alvo, i.destino)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        dados = i.conteudo if i.conteudo is not None else b"o que a Atena lembra"
        if i.chaves_json:   # o daemon.json de verdade tem mais chaves (o runtime da NVIDIA)
            dados = json.dumps(dict(json.loads(dados), runtimes={"nvidia": {"path": "nvidia-container-runtime"}})).encode()
        open(p, "wb").write(dados)
        if i.modo is not None:
            os.chmod(p, i.modo)
    return itens


def resultados(alvo, **kw):
    return {r.caminho: r for r in estado.conferir(RAIZ, alvo, donos=False, **kw)[0]}


# --- o estado anda junto com o instalador
conf_exemplo = f"{tmp}/exemplo.conf"
escrever_conf(conf_exemplo, ATENA_PAINEL_CASA="sim")
c = estado.ler_conf(conf_exemplo)
modelos = [rel for rel in estado.arquivos(RAIZ, ".") if os.path.isfile(os.path.join(RAIZ, rel))
           and estado.e_modelo(open(os.path.join(RAIZ, rel), "rb").read())
           and rel.split("/")[0] in ("stacks", "host") and not rel.endswith((".md", ".sh"))]
confere("há modelos com {{ATENA_*}} para comparar", len(modelos) >= 3, modelos)
pedidas = {v.decode() for rel in modelos
           for v in re.findall(rb"\{\{(?:SE )?(ATENA_\w+)\}\}", open(os.path.join(RAIZ, rel), "rb").read())}
confere("todo {{ATENA_*}} dos modelos é uma chave que o estado preenche", pedidas <= set(estado.RENDERIZADAS),
        pedidas - set(estado.RENDERIZADAS))
diferentes = []
for rel in modelos:
    saida = f"{tmp}/renderizado"
    r = subprocess.run(["bash", "-c", 'RAIZ=$1; CONF=$2; . "$RAIZ/install/lib.sh"; renderizar "$3" "$4"', "_", RAIZ,
                        conf_exemplo, os.path.join(RAIZ, rel), saida], capture_output=True)
    if r.returncode != 0 or open(saida, "rb").read() != estado.renderizar(open(os.path.join(RAIZ, rel), "rb").read(), c, rel):
        diferentes.append(rel)
confere(f"o renderizar do instalador preenche os {len(modelos)} modelos pelo estado", not diferentes, diferentes)
open(f"{tmp}/modelo", "w").write("ip={{ATENA_LAN_IP}} x={{ATENA_NAO_EXISTE}}\n")
r = subprocess.run(["bash", "-c", 'RAIZ=$1; CONF=$2; . "$RAIZ/install/lib.sh"; renderizar "$3" "$4"', "_", RAIZ,
                    conf_exemplo, f"{tmp}/modelo", f"{tmp}/saida"], capture_output=True, text=True)
confere("um {{ATENA_*}} sem valor faz o instalador parar, dizendo qual",
        r.returncode != 0 and "{{ATENA_NAO_EXISTE}}" in r.stderr and "não consegui preencher" in r.stderr, r.stderr)
# os blocos {{SE ATENA_X}} ... {{FIM}}: ficam só quando a chave tem valor, e as marcas saem sempre
modelo = (b"antes\n  # {{SE ATENA_ROUTER_IP}}\ndns: {{ATENA_ROUTER_IP}}\n# {{FIM}}\ndepois\n")
com = estado.renderizar(modelo, c, "m")
sem = estado.renderizar(modelo, dict(c, ATENA_ROUTER_IP=""), "m")
confere("bloco com a chave: fica, sem as linhas de marca", com == b"antes\ndns: 192.168.0.1\ndepois\n", com)
confere("bloco sem a chave: sai inteiro", sem == b"antes\ndepois\n", sem)
erros = []
for errado, trecho in ((b"# {{SE ATENA_TZ}}\nx\n", "não tem {{FIM}}"), (b"x\n# {{FIM}}\n", "sem {{SE"),
                       (b"{{SE ATENA_TZ}}\n{{SE ATENA_TZ}}\n{{FIM}}\n", "dentro de outro"),
                       (b"{{SE ATENA_TZX}}\n{{FIM}}\n", "não é uma chave"),
                       (b"# {{SE ATENA_TZ}} um texto que sumiria\n# {{FIM}}\n", "só pode ter a marca")):
    try:
        estado.renderizar(errado, c, "m")
        erros.append((errado, "passou"))
    except estado.ConfInvalida as e:
        if trecho not in str(e):
            erros.append((errado, str(e)))
confere("bloco sem fim, fim sem bloco, bloco dentro de bloco, chave desconhecida e texto na linha da marca: "
        "recusados, dizendo o quê",
        not erros, erros)
confere("um arquivo só com um bloco também é um modelo", estado.e_modelo(b"# {{SE ATENA_PC_IP}}\n# {{FIM}}\n")
        and not estado.e_modelo(b"nada aqui\n"))
open(f"{tmp}/modelo", "wb").write(modelo)
escrever_conf(f"{tmp}/sem-roteador.conf", ATENA_ROUTER_IP="")
r = subprocess.run(["bash", "-c", 'RAIZ=$1; CONF=$2; . "$RAIZ/install/lib.sh"; renderizar "$3" "$4"', "_", RAIZ,
                    f"{tmp}/sem-roteador.conf", f"{tmp}/modelo", f"{tmp}/saida"], capture_output=True, text=True)
confere("o instalador tira o bloco cuja chave está vazia no atena.conf",
        r.returncode == 0 and open(f"{tmp}/saida", "rb").read() == b"antes\ndepois\n", r.stderr)
r = subprocess.run([sys.executable, os.path.join(RAIZ, "install", "estado.py"), "preencher", conf_exemplo],
                   capture_output=True, text=True)
confere("estado.py preencher sem os três caminhos: sai com 2 e diz o uso", r.returncode == 2 and "uso:" in r.stderr, r.stderr)

etapa80 = INSTALADOR["80-stacks.sh"]
bloco = etapa80[etapa80.index('if [ "$ATENA_GPU" = none ]; then'):]
bloco = bloco[bloco.index("\n") + 1:bloco.index("\n  fi\n")]
diferentes = []
for compose in sorted(glob.glob(os.path.join(RAIZ, "stacks", "*", "*", "compose.yaml"))):
    os.makedirs(f"{tmp}/gpu", exist_ok=True)
    shutil.copy(compose, f"{tmp}/gpu/compose.yaml")
    subprocess.run(["bash", "-c", 'destino=$1\n' + bloco, "_", f"{tmp}/gpu"], check=True)
    if open(f"{tmp}/gpu/compose.yaml", "rb").read() != estado.sem_gpu(open(compose, "rb").read()):
        diferentes.append(compose)
confere("sem GPU, o estado tira a GPU dos composes como o 80-stacks.sh", not diferentes, diferentes)
confere("e há o que tirar (gpus: all em algum compose)",
        any(b"gpus: all" in open(f, "rb").read() for f in glob.glob(os.path.join(RAIZ, "stacks", "*", "*", "compose.yaml"))))

etapa88 = INSTALADOR["88-lab.sh"]
trecho = etapa88[etapa88.index("<<'PY'\n", etapa88.index("lab_json=$(mktemp)")) + 7:]
trecho = trecho[:trecho.index("\nPY\n") + 1]
contas = "max pro, max Errada trabalho"
subprocess.run([sys.executable, "-", os.path.join(RAIZ, "host", "lab", "lab.json"), f"{tmp}/lab.json", contas],
               input=trecho, text=True, check=True)
escrever_conf(conf_exemplo, ATENA_CLAUDE_CONTAS=f'"{contas}"')
itens, _ = estado.desejado(RAIZ, estado.ler_conf(conf_exemplo), {"hermes": True, "lab": True, "painel": True, "ssh": False})
lab_json = next(i for i in itens if i.destino == "/usr/local/lib/atena-claude/lab.json")
confere("o lab.json do estado é o que o 88-lab.sh monta, com as contas do atena.conf",
        lab_json.conteudo == open(f"{tmp}/lab.json", "rb").read())
confere("e esconde a credencial de cada conta válida (max, pro, trabalho)",
        all(f"contas/{n}/.credentials.json" in lab_json.conteudo.decode() for n in ("max", "pro", "trabalho"))
        and "Errada" not in lab_json.conteudo.decode())

padroes = dict(re.findall(r':\s+"\$\{(ATENA_\w+):=([^}]*)\}"', INSTALADOR["00-verificar.sh"]))
confere("os padrões do estado são os do 00-verificar.sh",
        {k: v for k, v in padroes.items() if k != "ATENA_NTFY_URL"} == estado.PADROES, (padroes, estado.PADROES))
escrever_conf(conf_exemplo)
texto = open(conf_exemplo).read()
open(conf_exemplo, "w").write(re.sub(r"^ATENA_(TZ|NTFY_URL|VOZ)=.*\n", "", texto, flags=re.M))
c = estado.ler_conf(conf_exemplo)
confere("um atena.conf antigo, sem as chaves novas, fica com os padrões",
        c["ATENA_TZ"] == "America/Sao_Paulo" and c["ATENA_VOZ"] == "nao"
        and c["ATENA_NTFY_URL"] == f"http://{c['ATENA_LAN_IP']}:2586", c)

# o PC da rede de casa no LiteLLM: o modelo pc só com ATENA_PC_IP, e o plano B só com ATENA_PC_RESERVA
try:
    import yaml
except ImportError:
    yaml = None
litellm = open(os.path.join(RAIZ, "stacks", "ai", "litellm", "config.yaml"), "rb").read()
casos = {"sem PC": {}, "com PC": {"ATENA_PC_IP": "192.168.0.50"},
         "com PC e plano B": {"ATENA_PC_IP": "192.168.0.50", "ATENA_PC_MODELO": "gemma-12b", "ATENA_PC_RESERVA": "sonnet"}}
for nome, trocas in casos.items():
    texto = estado.renderizar(litellm, dict(c, **trocas), "config.yaml").decode()
    if yaml:
        cfg = yaml.safe_load(texto)
        nomes = [m["model_name"] for m in cfg["model_list"]]
        reserva = cfg["litellm_settings"].get("fallbacks")
    else:   # sem o PyYAML, pelo texto
        nomes = [linha.split(":", 1)[1].strip() for linha in texto.split("\n") if "- model_name:" in linha]
        reserva = "fallbacks:" in texto or None
    if nome == "sem PC":
        confere("LiteLLM sem PC: nem o modelo pc, nem plano B, e o YAML vale", "pc" not in nomes and not reserva
                and "{{" not in texto and "voz" in nomes, (nomes, reserva))
    elif nome == "com PC":
        confere("LiteLLM com PC: o modelo pc no IP e na porta do atena.conf, sem plano B", "pc" in nomes and not reserva
                and "api_base: http://192.168.0.50:1234/v1" in texto and "model: openai/qwen3-14b" in texto, (nomes, reserva))
        confere("e o comentário do bloco chega inteiro (as marcas ficam sozinhas na linha)",
                "  # O PC da rede de casa (ATENA_PC_IP" in texto and "SE ATENA" not in texto)
    else:
        confere("LiteLLM com plano B: o pc cai para o modelo de ATENA_PC_RESERVA",
                "model: openai/gemma-12b" in texto and (reserva == [{"pc": ["sonnet"]}] if yaml else reserva), reserva)

# todo arquivo do repositório que vai para o servidor está no estado, com todas as opções ligadas
escrever_conf(conf_exemplo, ATENA_PAINEL_CASA="sim", ATENA_TAILSCALE="sim", ATENA_CLAUDE_SKILLS="sim",
              ATENA_SENSORES_MODULO="nct6683", ATENA_GPU="nvidia")
itens, vigias = estado.desejado(RAIZ, estado.ler_conf(conf_exemplo),
                                {"hermes": True, "lab": True, "painel": True, "ssh": True})
FORA = {"hermes/configurar.sh": "roda dentro do container (a configuração do Hermes), não é copiado",
        "stacks/core/painel/DESIGN.md": "documentação do painel", "stacks/core/painel/PRODUCT.md": "idem"}
origens = [i.origem for i in itens]
esquecidos = []
for pasta in ("host/sbin", "host/systemd", "host/executor/atena_executor", "host/lab", "host/polkit", "host/ssh",
              "host/docker", "hermes", "stacks"):
    for rel in estado.arquivos(RAIZ, pasta):
        if (rel in FORA or rel.endswith(".env.example") or "/.impeccable/" in rel
                or rel.startswith("host/lab/coletor/")   # vira a imagem do coletor (docker build), não é copiado
                or any(o == rel or o.startswith((rel + " ", rel + ",")) for o in origens)):
            continue
        esquecidos.append(rel)
confere("todo arquivo de host/, hermes/ e stacks/ que vai para o servidor está no estado", not esquecidos, esquecidos)
fora_do_instalador = [i.origem for i in itens if i.origem.startswith(("host/", "hermes/"))
                      and not i.origem.endswith(".slice") and "/atena_executor/" not in i.origem
                      and os.path.basename(i.origem.split(" ")[0].rstrip(",")) not in TUDO]
confere("e todo arquivo do estado (fora os de um glob) aparece nas etapas do instalador", not fora_do_instalador,
        fora_do_instalador)
destinos = [i.destino for i in itens]
confere("nenhum destino repetido", len(destinos) == len(set(destinos)),
        sorted({d for d in destinos if destinos.count(d) > 1}))

# --- o conferir num servidor de mentira
alvo = f"{tmp}/servidor"
itens = montar(alvo, ATENA_PAINEL_CASA="sim", ATENA_SENSORES_MODULO="nct6683", ATENA_CLAUDE_SKILLS="sim",
               ATENA_TAILSCALE="sim")
r = resultados(alvo)
confere("servidor montado pelo estado: tudo igual", all(x.estado == "igual" for x in r.values()),
        [x for x in r.values() if x.estado != "igual"])
confere("o painel na rede de casa entra preenchido (o IP do atena.conf)",
        b"192.168.0.10:3100" in open(f"{alvo}/etc/systemd/system/atena-painel-casa.socket", "rb").read())
confere("sem GPU (o exemplo), os composes saem sem gpus: all",
        b"gpus: all" not in open(f"{alvo}/opt/atena/stacks/ai/ollama/compose.yaml", "rb").read())


def estragar(rel, dados):
    with open(f"{alvo}{rel}", "ab") as f:
        f.write(dados)


def estragos():
    """Um de cada: mudado, faltando, sobrando, cópia antiga, só comentário, modo, chave do daemon.json."""
    estragar("/usr/local/lib/atena-executor/atena_executor/stacks.py", b"\nIMAGEM_LIVRE = True\n")
    os.remove(f"{alvo}/usr/local/sbin/atena-telegram")
    os.makedirs(f"{alvo}/etc/systemd/system/atena-executor.service.d", exist_ok=True)
    open(f"{alvo}/etc/systemd/system/atena-executor.service.d/leitura.conf", "w").write("[Service]\nProtectHome=read-only\n")
    os.makedirs(f"{alvo}/etc/systemd/system/atena-velha.service.d")
    open(f"{alvo}/etc/systemd/system/atena-velha.service.d/x.conf", "w").write("[Service]\n")
    open(f"{alvo}/usr/local/sbin/atena-foto", "w").write("#!/bin/sh\n")
    open(f"{alvo}/usr/local/sbin/atena-executor.antes-aprovacao", "w").write("velho\n")
    open(f"{alvo}/usr/local/lib/atena-executor/atena_executor/arca.py", "w").write("# o Arca\n")
    estragar("/etc/systemd/system/atena-vigia.timer", b"# so um comentario a mais\n")
    os.chmod(f"{alvo}/usr/local/sbin/atena-reconciliar", 0o700)
    open(f"{alvo}/opt/atena/stacks/core/painel/app/public/velho.js", "w").write("// sobrou\n")
    open(f"{alvo}/opt/atena/stacks/core/beszel/.env", "w").write("BESZEL_KEY=segredo\n")   # o que é do servidor
    os.makedirs(f"{alvo}/opt/atena/stacks/apps/meu-app")
    open(f"{alvo}/opt/atena/stacks/apps/meu-app/compose.yaml", "w").write("services: {}\n")
    d = json.load(open(f"{alvo}/etc/docker/daemon.json"))
    d["live-restore"] = False
    json.dump(d, open(f"{alvo}/etc/docker/daemon.json", "w"))
    os.remove(f"{alvo}/srv/agents/hermes/memories/USER.md")
    open(f"{alvo}/srv/agents/hermes/memories/MEMORY.md", "w").write("outra coisa, que é dela\n")


estragos()
r = resultados(alvo)
confere("módulo do executor mudado: difere", r["/usr/local/lib/atena-executor/atena_executor/stacks.py"].estado == "difere")
confere("script que falta: falta", r["/usr/local/sbin/atena-telegram"].estado == "falta")
confere("drop-in feito à mão: sobra", r.get("/etc/systemd/system/atena-executor.service.d/leitura.conf",
                                             estado.Resultado("", "", "nada")).estado == "sobra")
confere("pasta de drop-in que o repositório não tem: o que está nela sobra",
        "/etc/systemd/system/atena-velha.service.d/x.conf" in r and r["/etc/systemd/system/atena-velha.service.d/x.conf"].estado == "sobra")
confere("script velho em /usr/local/sbin: sobra", r["/usr/local/sbin/atena-foto"].estado == "sobra")
confere("cópia .antes-*: cópia, não sobra", r["/usr/local/sbin/atena-executor.antes-aprovacao"].estado == "copia")
confere("módulo velho do executor: sobra", r["/usr/local/lib/atena-executor/atena_executor/arca.py"].estado == "sobra")
confere("só um comentário a mais: difere, só nos comentários",
        r["/etc/systemd/system/atena-vigia.timer"].detalhes == ["só nos comentários"], r["/etc/systemd/system/atena-vigia.timer"])
confere("modo errado: difere, com o modo", r["/usr/local/sbin/atena-reconciliar"].detalhes == ["modo 700, o repositório pede 755"],
        r["/usr/local/sbin/atena-reconciliar"])
confere("arquivo velho no app do painel: sobra", r["/opt/atena/stacks/core/painel/app/public/velho.js"].estado == "sobra")
confere("o .env e as stacks suas ficam fora", not any(".env" in k or "meu-app" in k for k in r))
confere("daemon.json com uma chave da Atena mudada: difere, dizendo qual",
        r["/etc/docker/daemon.json"].detalhes == ["chaves diferentes: live-restore"], r["/etc/docker/daemon.json"])
confere("memória da Atena: só precisa existir", r["/srv/agents/hermes/memories/USER.md"].estado == "falta"
        and r["/srv/agents/hermes/memories/MEMORY.md"].estado == "igual")

if os.geteuid() != 0:   # o root lê tudo
    os.chmod(f"{alvo}/usr/local/sbin/atena-avisar", 0)
    r = resultados(alvo, partes=["host"])
    confere("sem permissão para ler: ?, e não igual", r["/usr/local/sbin/atena-avisar"].estado == "ilegivel")
    os.chmod(f"{alvo}/usr/local/sbin/atena-avisar", 0o755)

# o dono: o estado pede um usuário, e o arquivo é de outro
eu = estado.nome_dono(os.getuid())
p = f"{tmp}/dono.txt"
open(p, "wb").write(b"x")
os.chmod(p, 0o644)
grupo = estado.nome_grupo(os.getgid())
r = estado.comparar(estado.Item("host", p, b"x", "x", 0o644, eu, grupo), "/")
confere("dono certo: igual", r.estado == "igual", r)
r = estado.comparar(estado.Item("host", p, b"x", "x", 0o644, "hermes-que-nao-existe", grupo), "/")
confere("dono errado: difere, dizendo quem é e quem devia ser",
        r.detalhes == [f"dono {eu}:{grupo}, o repositório pede hermes-que-nao-existe:{grupo}"], r)

# as opções: sem o lab e com o painel fora da rede de casa (as unidades dela ficaram de quando estava)
casa = {u: open(f"{alvo}/etc/systemd/system/{u}", "rb").read() for u in ("atena-painel-casa.socket", "atena-painel-casa.service")}
montar(alvo, opcoes=("hermes", "painel"), ATENA_PAINEL_CASA="nao")
for u, dados in casa.items():
    open(f"{alvo}/etc/systemd/system/{u}", "wb").write(dados)
r = resultados(alvo)
confere("painel fora da rede de casa: as unidades dela sobram",
        r["/etc/systemd/system/atena-painel-casa.socket"].estado == "sobra")
confere("sem o lab: nada do lab no estado", not any(k.startswith("/usr/local/lib/atena-claude") for k in r)
        and "/usr/local/sbin/atena-claude-runner" not in r)
os.remove(f"{alvo}/etc/systemd/system/atena-painel-casa.socket")
os.remove(f"{alvo}/etc/systemd/system/atena-painel-casa.service")
r = resultados(alvo)
confere("e, tiradas, o servidor volta a ficar igual", all(x.estado == "igual" for x in r.values()),
        [x for x in r.values() if x.estado != "igual"])

# fora de um clone do git (o CI roda numa cópia sem .git), o que não foi commitado fica de fora num clone
repo = f"{tmp}/repo"
os.makedirs(f"{repo}/stacks/core/x/__pycache__")
open(f"{repo}/stacks/core/x/compose.yaml", "w").write("services: {}\n")
open(f"{repo}/stacks/core/x/__pycache__/y.pyc", "w").write("")
confere("fora do git: todos os arquivos, menos o cache do Python",
        estado.arquivos(repo, "stacks") == ["stacks/core/x/compose.yaml"], estado.arquivos(repo, "stacks"))
if shutil.which("git"):
    g = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(g + ["init", "-q"], check=True)
    subprocess.run(g + ["add", "stacks/core/x/compose.yaml"], check=True)
    open(f"{repo}/stacks/core/x/rascunho.png", "w").write("")
    confere("num clone: só o que o git conhece", estado.arquivos(repo, "stacks") == ["stacks/core/x/compose.yaml"],
            estado.arquivos(repo, "stacks"))

# --- o ./aplicar --conferir: o mesmo servidor de mentira, pela linha de comando
def aplicar(*args):
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "aplicar"), *args], capture_output=True, text=True, timeout=120,
                       stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout, r.stderr


montar(alvo, ATENA_PAINEL_CASA="sim", ATENA_SENSORES_MODULO="nct6683", ATENA_CLAUDE_SKILLS="sim", ATENA_TAILSCALE="sim")
rc, saida, erro = aplicar("--conferir", "--alvo", alvo, "--sem-dono")
confere("aplicar: servidor igual, sai com 0 e diz", rc == 0 and "o servidor está igual ao repositório" in saida, saida + erro)
rc, saida, erro = aplicar("--alvo", alvo, "--sem-dono")
confere("aplicar sem --conferir, num servidor igual: nada a aplicar", rc == 0 and "Nada a aplicar" in saida, saida + erro)
estragos()
rc, saida, erro = aplicar("--conferir", "--alvo", alvo, "--sem-dono")
confere("com diferenças, sai com 1 e conta no resumo", rc == 1 and "Resumo: 11 diferenças (4 difere, 2 falta, 5 sobra)" in saida
        and "cópias antigas (.antes-*): 1" in saida, saida)
rc, saida, _ = aplicar("--conferir", "--alvo", alvo, "--sem-dono", "--diff", "--parte", "executor")
confere("--diff mostra a linha que o repositório não tem, do servidor para o repositório",
        "-IMAGEM_LIVRE = True" in saida and "+++ repositório:host/executor/atena_executor/stacks.py" in saida, saida)
confere("--parte executor: só o executor", "atena-telegram" not in saida and "arca.py" in saida, saida)
rc, saida, _ = aplicar("--conferir", "--alvo", alvo, "--sem-dono", "--json")
j = json.loads(saida)
confere("--json: a contagem e só o que não está igual", j["contagem"]["falta"] == 2
        and all(x["estado"] != "igual" for x in j["resultados"]), j["contagem"])
rc, saida, erro = aplicar("--conferir", "--alvo", alvo, "--parte", "arca")
confere("parte desconhecida: sai com 2 e lista as partes", rc == 2 and "executor" in erro, erro)
rc, saida, erro = aplicar("--conferir", "--alvo", f"{tmp}/vazio")
confere("sem o atena.conf: sai com 2 e diz onde procurou", rc == 2 and "vazio/etc/atena/atena.conf" in erro, erro)

shutil.rmtree(tmp)
print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
