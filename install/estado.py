"""O estado desejado do servidor: cada arquivo que o repositório põe nele, com o conteúdo já preenchido
com os valores do atena.conf, o modo e o dono, e as pastas onde o que não está aqui sobra. Também
compara esse estado com um servidor, sem mudar nada (./aplicar --conferir).

As regras são as das etapas do instalador (install/*.sh): os caminhos, os modos, o que é preenchido e o
que depende de uma opção (--hermes, --lab, --painel, --ssh). O tests/install/teste_estado.py confere que
as duas descrições andam juntas. O instalador preenche os modelos por aqui também:
  python3 install/estado.py preencher <atena.conf> <modelo> <destino>
"""
import difflib
import fnmatch
import grp
import json
import os
import pwd
import re
import subprocess
import sys
from dataclasses import dataclass, field

# os {{ATENA_*}} que os modelos podem pedir
RENDERIZADAS = ("ATENA_LAN_IP", "ATENA_LAN_CIDR", "ATENA_LAN_IF", "ATENA_ROUTER_IP", "ATENA_ADMIN_USER",
                "ATENA_TZ", "ATENA_NTFY_URL", "ATENA_PAINEL_CASA",
                "ATENA_PC_IP", "ATENA_PC_PORTA", "ATENA_PC_MODELO", "ATENA_PC_RESERVA")
# as chaves que chegaram depois da primeira versão: um atena.conf mais antigo fica com o padrão
# (os mesmos do install/00-verificar.sh)
PADROES = {"ATENA_TZ": "America/Sao_Paulo", "ATENA_SENSORES_MODULO": "", "ATENA_VOZ": "nao",
           "ATENA_CLAUDE_CONTAS": "principal", "ATENA_CLAUDE_TROCA": "nao", "ATENA_CLAUDE_VERSAO": "2.1.302",
           "ATENA_CLAUDE_SKILLS": "nao", "ATENA_PAINEL_CASA": "nao",
           "ATENA_PC_IP": "", "ATENA_PC_PORTA": "1234", "ATENA_PC_MODELO": "qwen3-14b", "ATENA_PC_RESERVA": ""}
# sem GPU, o 80-stacks.sh tira o pedido de GPU dos composes e troca as imagens pelas de CPU
SEM_GPU = ((r"^ *gpus: all", None),
           (r"speaches:0.8.3-cuda-12.6.3 .*", "speaches:0.8.3-cpu"),
           (r"WHISPER__INFERENCE_DEVICE: cuda", "WHISPER__INFERENCE_DEVICE: cpu"),
           (r"henrygd/beszel-agent-nvidia:", "henrygd/beszel-agent:"))
# um bloco entre uma linha com {{SE ATENA_X}} e outra com {{FIM}} só fica quando ATENA_X tem valor
SE = re.compile(rb"\{\{SE (ATENA_[A-Z_]+)\}\}")
FIM = b"{{FIM}}"
MARCA_SOZINHA = re.compile(rb"^\s*(#|//)?\s*\{\{(SE ATENA_[A-Z_]+|FIM)\}\}\s*$")
COPIA_ANTIGA = re.compile(r"\.antes-")   # instalar_arquivo guarda .antes-atena-<data>; as trocas à mão, .antes-<o quê>

PARTES = {
    "host": "scripts, unidades do systemd e configuração do sistema",
    "executor": "o executor de ações",
    "stacks": "as stacks do repositório",
    "painel": "o código do painel",
    "hermes": "a Atena: personalidade, habilidades e scripts",
    "lab": "o lab do Claude Code",
}


@dataclass
class Item:
    """Um arquivo que o repositório põe no servidor."""
    parte: str
    destino: str                    # caminho no servidor
    conteudo: bytes | None          # None: basta existir (ex.: a memória da Atena, que é dela)
    origem: str                     # de onde vem, no repositório
    modo: int | None = None
    dono: str | None = None
    grupo: str | None = None
    chaves_json: bool = False       # só as chaves do repositório precisam estar iguais (o daemon.json)


@dataclass
class Vigia:
    """Uma pasta do modelo: o que casa com o padrão e não é um Item sobra."""
    parte: str
    pasta: str
    padrao: str = "*"
    recursiva: bool = False


@dataclass
class Resultado:
    parte: str
    caminho: str
    estado: str                     # igual, difere, falta, sobra, copia, ilegivel
    origem: str = ""
    detalhes: list = field(default_factory=list)
    servidor: bytes | None = None   # para o --diff
    repositorio: bytes | None = None


class ConfInvalida(Exception):
    pass


def ler_conf(caminho):
    """Os ATENA_* do atena.conf como o instalador os vê: o bash lê o arquivo (ele é um script), e as chaves
    que faltam ficam com o padrão."""
    if not os.path.isfile(caminho):
        raise ConfInvalida(f"não achei o {caminho}")
    r = subprocess.run(["bash", "-c", 'set -a; . "$1" >/dev/null || exit 1; '
                        'for v in "${!ATENA_@}"; do printf "%s=%s\\0" "$v" "${!v}"; done', "_", caminho],
                       capture_output=True)
    if r.returncode != 0:
        raise ConfInvalida(f"o bash não conseguiu ler o {caminho}: {r.stderr.decode(errors='replace').strip()}")
    conf = dict(PADROES)
    for par in r.stdout.decode().split("\0"):
        if "=" in par:
            chave, valor = par.split("=", 1)
            conf[chave] = valor
    conf.setdefault("ATENA_NTFY_URL", f"http://{conf.get('ATENA_LAN_IP', '')}:2586")
    return conf


def e_modelo(texto):
    """Se o arquivo tem algo para preencher ({{ATENA_*}} ou um bloco {{SE ATENA_*}})."""
    return b"{{ATENA_" in texto or b"{{SE ATENA_" in texto


def renderizar(texto, conf, origem):
    """Preenche os {{ATENA_*}} de um modelo com os valores do atena.conf e recusa o que sobrar. Um bloco
    entre uma linha com {{SE ATENA_X}} e outra com {{FIM}} só fica quando ATENA_X tem valor, e as duas
    linhas de marca saem sempre (elas podem ser comentários do arquivo). É o renderizar do instalador
    (install/lib.sh) e o do ./aplicar."""
    linhas, chave = [], None
    for n, linha in enumerate(texto.split(b"\n"), 1):
        if (SE.search(linha) or FIM in linha) and not MARCA_SOZINHA.match(linha):
            raise ConfInvalida(f"{origem}:{n}: a linha de um {{{{SE}}}} ou {{{{FIM}}}} só pode ter a marca (o resto dela some)")
        m = SE.search(linha)
        if m:
            if chave:
                raise ConfInvalida(f"{origem}:{n}: um {{{{SE}}}} dentro de outro")
            chave = m.group(1).decode()
            if chave not in RENDERIZADAS:
                raise ConfInvalida(f"{origem}:{n}: {chave} não é uma chave que os modelos podem pedir")
            continue
        if FIM in linha:
            if not chave:
                raise ConfInvalida(f"{origem}:{n}: um {{{{FIM}}}} sem {{{{SE ATENA_...}}}}")
            chave = None
            continue
        if not chave or conf.get(chave, ""):
            linhas.append(linha)
    if chave:
        raise ConfInvalida(f"{origem}: o {{{{SE {chave}}}}} não tem {{{{FIM}}}}")
    texto = b"\n".join(linhas)
    for v in RENDERIZADAS:
        texto = texto.replace(("{{" + v + "}}").encode(), conf.get(v, "").encode())
    sobrou = re.search(rb"\{\{ATENA_[A-Z_]*\}\}", texto)
    if sobrou:
        raise ConfInvalida(f"sobrou um {sobrou.group(0).decode()} sem valor em {origem}")
    return texto


def sem_gpu(texto):
    linhas = []
    for linha in texto.decode().split("\n"):
        if re.search(SEM_GPU[0][0], linha):
            continue
        for padrao, troca in SEM_GPU[1:]:
            linha = re.sub(padrao, troca, linha)
        linhas.append(linha)
    return "\n".join(linhas).encode()


def arquivos(raiz, pasta):
    """Os arquivos do repositório numa pasta, relativos à raiz: os que o git conhece (o que está na pasta e
    não foi commitado fica de fora) ou, fora de um clone (um git archive), todos, menos o cache do Python."""
    try:
        r = subprocess.run(["git", "-c", f"safe.directory={raiz}", "-C", raiz, "ls-files", "-z", "--", pasta],
                           capture_output=True, check=True)
        lista = sorted(p for p in r.stdout.decode().split("\0") if p)
        if lista or os.path.isdir(os.path.join(raiz, ".git")):
            return lista
    except (OSError, subprocess.CalledProcessError):
        pass
    lista = []
    for base, pastas, nomes in os.walk(os.path.join(raiz, pasta)):
        pastas[:] = [p for p in pastas if p != "__pycache__"]
        lista += [os.path.relpath(os.path.join(base, n), raiz) for n in nomes]
    return sorted(lista)


def contas_claude(texto):
    """As contas de ATENA_CLAUDE_CONTAS, como o 88-lab.sh as lê para o lab.json."""
    return [c for c in dict.fromkeys(re.split(r"[\s,]+", texto)) if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,19}", c)]


def instalado(alvo):
    """O que este servidor tem além do básico (as opções do install.sh), pelas pastas que cada uma cria."""
    return {"hermes": os.path.isdir(no_alvo(alvo, "/srv/agents/hermes")),
            "lab": os.path.isdir(no_alvo(alvo, "/var/lib/atena-claude")),
            "painel": os.path.isdir(no_alvo(alvo, "/srv/core/painel")),
            "ssh": os.path.exists(no_alvo(alvo, "/etc/ssh/sshd_config.d/00-atena-hardening.conf"))}


def no_alvo(alvo, caminho):
    return os.path.join(alvo, caminho.lstrip("/")) if alvo not in ("", "/") else caminho


def desejado(raiz, conf, tem):
    """(itens, vigias): o que o repositório põe neste servidor, com este atena.conf e estas opções."""
    itens, vigias = [], []
    admin = conf.get("ATENA_ADMIN_USER", "atena")

    def ler(rel):
        with open(os.path.join(raiz, rel), "rb") as f:
            return f.read()

    def item(parte, rel, destino, modo=0o644, dono="root", grupo="root", preencher=False):
        texto = ler(rel)
        if preencher:
            texto = renderizar(texto, conf, rel)
        itens.append(Item(parte, destino, texto, rel, modo, dono, grupo))

    # --- host: 30-zonas, 40-firewall, 50-servicos, 82-executor, 84-ntfy e as etapas opcionais
    unidades = [os.path.basename(p) for p in arquivos(raiz, "host/systemd") if p.endswith(".slice")]
    unidades += ["atena-docker-firewall.service",
                 "atena-stacks-sync.service", "atena-stacks-sync.path", "atena-litellm-virada-mes.service",
                 "atena-litellm-virada-mes.timer", "atena-reconciliar.service", "atena-reconciliar.timer",
                 "docker.service.d/10-atena-srv.conf",
                 "atena-executor.service", "atena-avisar@.service", "atena-vigia.service", "atena-vigia.timer",
                 "atena-.service.d/50-avisar.conf", "atena-avisar@.service.d/99-sem-laco.conf"]
    sbin = ["atena-docker-firewall", "atena-stacks-sync", "atena-chave-anthropic", "atena-litellm-virada-mes",
            "atena-reconciliar", "atena-executor", "atena-avisar", "atena-ntfy-celular"]
    preenchidas = []
    if tem["painel"]:
        sbin.append("atena-painel-senha")
        if conf.get("ATENA_PAINEL_CASA") == "sim":
            preenchidas += ["atena-painel-casa.socket", "atena-painel-casa.service"]
    if tem["hermes"]:
        sbin += ["atena-telegram", "atena-hermes-chave"]
    if tem["lab"]:
        sbin += ["atena-claude-runner", "atena-claude-conta", "atena-lab-lixeira", "atena-lab-tailscale"]
        unidades += ["atena-claude.path", "atena-claude.service", "atena-lab-lixeira.service",
                     "atena-lab-lixeira.timer", "atena-executor.service.d/lab.conf", "atena-lab.slice.d/50-lab.conf"]
        if conf.get("ATENA_TAILSCALE") == "sim":
            unidades += ["atena-lab-tailscale-on@.service", "atena-lab-tailscale-off@.service"]
            item("host", "host/polkit/50-atena-lab-tailscale.rules", "/etc/polkit-1/rules.d/50-atena-lab-tailscale.rules")
    for u in unidades:
        item("host", f"host/systemd/{u}", f"/etc/systemd/system/{u}")
    for u in preenchidas:
        item("host", f"host/systemd/{u}", f"/etc/systemd/system/{u}", preencher=True)
    for s in sbin:
        item("host", f"host/sbin/{s}", f"/usr/local/sbin/{s}", 0o755)
    itens.append(Item("host", "/etc/docker/daemon.json", ler("host/docker/daemon.json"), "host/docker/daemon.json",
                      chaves_json=True))
    modulo = conf.get("ATENA_SENSORES_MODULO", "")
    if modulo:
        itens.append(Item("host", "/etc/modules-load.d/atena-sensores.conf",
                          f"# Atena: chip da placa para o sistema.sensores (ventoinhas)\n{modulo}\n".encode(),
                          "gerado: ATENA_SENSORES_MODULO", 0o644, "root", "root"))
    if tem["ssh"]:
        item("host", "host/ssh/00-atena-hardening.conf", "/etc/ssh/sshd_config.d/00-atena-hardening.conf", 0o600,
             preencher=True)
    # (e as pastas atena*.d de drop-ins que existirem no servidor: o conferir as acrescenta)
    vigias += [Vigia("host", "/usr/local/sbin", "atena-*"),
               Vigia("host", "/etc/systemd/system", "atena*"),
               Vigia("host", "/etc/systemd/system/docker.service.d", "*atena*"),
               Vigia("host", "/etc/modules-load.d", "atena-*"),
               Vigia("host", "/etc/polkit-1/rules.d", "*atena*")]

    # --- executor (82): o pacote inteiro, sem sobrar módulo velho
    for rel in arquivos(raiz, "host/executor/atena_executor"):
        if rel.endswith(".py"):
            item("executor", rel, f"/usr/local/lib/atena-executor/atena_executor/{os.path.basename(rel)}")
    vigias.append(Vigia("executor", "/usr/local/lib/atena-executor/atena_executor", "*.py"))

    # --- stacks (80): cada stack do repositório, preenchida (o .env é gerado, e o .env.example só o descreve)
    for rel in arquivos(raiz, "stacks"):
        partes = rel.split("/")
        if len(partes) < 4 or partes[-1] == ".env.example":
            continue
        zona, nome, resto = partes[1], partes[2], "/".join(partes[3:])
        parte = "stacks"
        if (zona, nome) == ("core", "painel"):   # o 85-painel.sh leva só o compose e o app/
            if not tem["painel"] or not (resto == "compose.yaml" or resto.startswith("app/")):
                continue
            parte = "painel" if resto.startswith("app/") else "stacks"
        texto = ler(rel)
        if e_modelo(texto):
            texto = renderizar(texto, conf, rel)
        if resto == "compose.yaml" and conf.get("ATENA_GPU") == "none" and (zona, nome) != ("core", "painel"):
            texto = sem_gpu(texto)
        itens.append(Item(parte, f"/opt/atena/stacks/{zona}/{nome}/{resto}", texto, rel))
    if tem["painel"]:
        vigias.append(Vigia("painel", "/opt/atena/stacks/core/painel/app", recursiva=True))

    # --- hermes (86): os arquivos da Atena são do usuário hermes; a memória, só a semente da primeira vez
    if tem["hermes"]:
        D = "/srv/agents/hermes"
        for rel, dst in (("SOUL.md", "SOUL.md"),
                         ("skills/atena/servidor-atena/SKILL.md", "skills/atena/servidor-atena/SKILL.md"),
                         ("skills/atena/notas/SKILL.md", "skills/atena/notas/SKILL.md"),
                         ("scripts/ronda.py", "scripts/ronda.py"), ("scripts/acao.py", "scripts/acao.py"),
                         ("scripts/bom_dia.py", "scripts/bom_dia.py"), ("ferramentas.txt", "ferramentas/requisitos.txt")):
            item("hermes", f"hermes/{rel}", f"{D}/{dst}", 0o644, "hermes", "atena-acoes")
        for m in ("USER.md", "MEMORY.md"):
            itens.append(Item("hermes", f"{D}/memories/{m}", None, f"hermes/memoria/{m} (só a semente)"))

    # --- lab (88)
    if tem["lab"]:
        L = "/usr/local/lib/atena-claude"
        item("lab", "host/lab/dono.py", f"{L}/dono.py")
        item("lab", "host/lab/skills.json", f"{L}/skills.json")
        cfg = json.loads(ler("host/lab/lab.json"))
        cfg["sandbox"]["filesystem"]["denyRead"] += [f"/var/lib/atena-claude/contas/{c}/.credentials.json"
                                                     for c in contas_claude(conf.get("ATENA_CLAUDE_CONTAS", ""))]
        itens.append(Item("lab", f"{L}/lab.json", (json.dumps(cfg, indent=2, ensure_ascii=False) + "\n").encode(),
                          "host/lab/lab.json, com as contas do atena.conf", 0o644, "root", "root"))
        if conf.get("ATENA_CLAUDE_SKILLS") == "sim":
            for nome in ("package.json", "package-lock.json"):
                item("lab", f"host/lab/ferramentas/{nome}", f"{L}/ferramentas/{nome}")
            item("lab", "host/lab/tela.js", f"{L}/ferramentas/tela.js")
            item("lab", "host/lab/atena-tela", f"{L}/ferramentas/bin/atena-tela", 0o755)
        vigias += [Vigia("lab", L, "*.py"), Vigia("lab", L, "*.json")]
        item("lab", "host/lab/gitconfig", "/var/lib/atena-claude/.gitconfig")
        item("lab", "host/lab/lab-interativo.json", "/srv/lab/.claude/settings.json", 0o644, admin, admin)
        item("lab", "host/lab/guarda_escopo.py", "/srv/lab/.claude/hooks/guarda_escopo.py", 0o644, admin, admin)
        if tem["hermes"]:
            D = "/srv/agents/hermes"
            item("lab", "hermes/skills/atena/lab/SKILL.md", f"{D}/skills/atena/lab/SKILL.md", 0o644, "hermes", "atena-acoes")
            item("lab", "host/lab/gitconfig-atena", f"{D}/.gitconfig", 0o644, "hermes", "atena-acoes")
            item("lab", "host/lab/hermes-compose.override.yaml", "/opt/atena/stacks/agents/hermes/compose.override.yaml",
                 0o644, admin, admin)
    return itens, vigias


def texto_sem_comentarios(dados):
    """As linhas sem os comentários (# do shell, do YAML, do Python e do systemd), para dizer quando dois
    arquivos só diferem neles. Um # depois de um espaço também abre comentário, a não ser dentro de aspas."""
    linhas = []
    for linha in dados.decode(errors="replace").split("\n"):
        m = re.search(r"\s#", linha)
        if m and linha[:m.start()].count('"') % 2 == 0 and linha[:m.start()].count("'") % 2 == 0:
            linha = linha[:m.start()]
        if linha.strip() and not linha.strip().startswith("#"):
            linhas.append(linha.rstrip())
    return linhas


def nome_dono(uid):
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def nome_grupo(gid):
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)


def comparar(item, alvo, donos=True):
    caminho = no_alvo(alvo, item.destino)
    r = Resultado(item.parte, item.destino, "igual", item.origem, repositorio=item.conteudo)
    try:
        st = os.stat(caminho)
    except FileNotFoundError:
        r.estado = "falta"
        return r
    except PermissionError:
        r.estado = "ilegivel"
        return r
    if item.conteudo is not None:
        try:
            with open(caminho, "rb") as f:
                atual = f.read()
        except PermissionError:
            r.estado = "ilegivel"
            return r
        r.servidor = atual
        if item.chaves_json:
            try:
                no_servidor = json.loads(atual)
            except ValueError:
                no_servidor = {}
            diferentes = [k for k, v in json.loads(item.conteudo).items() if no_servidor.get(k) != v]
            if diferentes:
                r.estado = "difere"
                r.detalhes.append("chaves diferentes: " + ", ".join(diferentes))
        elif atual != item.conteudo:
            r.estado = "difere"
            if texto_sem_comentarios(atual) == texto_sem_comentarios(item.conteudo):
                r.detalhes.append("só nos comentários")
    if item.modo is not None and (st.st_mode & 0o7777) != item.modo:
        r.estado = "difere"
        r.detalhes.append(f"modo {st.st_mode & 0o7777:o}, o repositório pede {item.modo:o}")
    if donos and item.dono and (nome_dono(st.st_uid), nome_grupo(st.st_gid)) != (item.dono, item.grupo):
        r.estado = "difere"
        r.detalhes.append(f"dono {nome_dono(st.st_uid)}:{nome_grupo(st.st_gid)}, o repositório pede {item.dono}:{item.grupo}")
    return r


def sobras(vigia, esperados, alvo):
    """O que está numa pasta do modelo e não vem do repositório: sobras e cópias antigas (.antes-*)."""
    pasta = no_alvo(alvo, vigia.pasta)
    try:
        if vigia.recursiva:
            nomes = [os.path.relpath(os.path.join(b, n), pasta) for b, _, ns in os.walk(pasta) for n in ns]
        else:
            nomes = [n for n in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, n))]
    except FileNotFoundError:
        return []
    except PermissionError:
        return [Resultado(vigia.parte, vigia.pasta + "/", "ilegivel")]
    achados = []
    for nome in sorted(nomes):
        destino = os.path.join(vigia.pasta, nome)
        if destino in esperados or not fnmatch.fnmatch(os.path.basename(nome), vigia.padrao):
            continue
        achados.append(Resultado(vigia.parte, destino, "copia" if COPIA_ANTIGA.search(nome) else "sobra"))
    return achados


def pastas_de_dropin(alvo):
    """As pastas atena*.d do systemd no servidor: o que está nelas e não vem do repositório sobra."""
    base = no_alvo(alvo, "/etc/systemd/system")
    try:
        nomes = sorted(os.listdir(base))
    except (FileNotFoundError, PermissionError):
        return []
    return [f"/etc/systemd/system/{n}" for n in nomes
            if n.startswith("atena") and n.endswith(".d") and os.path.isdir(os.path.join(base, n))]


def conferir(raiz, alvo="/", conf=None, partes=None, donos=True):
    """Compara o estado desejado com o servidor em alvo. Devolve (resultados, conf, tem)."""
    c = ler_conf(conf or no_alvo(alvo, "/etc/atena/atena.conf"))
    tem = instalado(alvo)
    itens, vigias = desejado(raiz, c, tem)
    vigias += [Vigia("host", p) for p in pastas_de_dropin(alvo)]
    esperados = {i.destino for i in itens}
    resultados = [comparar(i, alvo, donos) for i in itens if not partes or i.parte in partes]
    vistos = set()
    for v in vigias:
        if partes and v.parte not in partes:
            continue
        for r in sobras(v, esperados, alvo):
            if r.caminho not in vistos:
                vistos.add(r.caminho)
                resultados.append(r)
    return resultados, c, tem


def diff(r, linhas=60):
    """O diff do servidor para o repositório (o que aplicar mudaria), cortado em linhas."""
    if r.servidor is None or r.repositorio is None:
        return []
    try:
        a, b = r.servidor.decode().split("\n"), r.repositorio.decode().split("\n")
    except UnicodeDecodeError:
        return ["    (arquivo binário)"]
    saida = list(difflib.unified_diff(a, b, f"servidor:{r.caminho}", f"repositório:{r.origem}", lineterm="", n=2))
    if len(saida) > linhas:
        saida = saida[:linhas] + [f"... mais {len(saida) - linhas} linhas"]
    return ["    " + s for s in saida]


def principal(argv):
    """estado.py preencher <atena.conf> <modelo> <destino>: o renderizar do instalador."""
    if len(argv) != 4 or argv[0] != "preencher":
        print("uso: python3 install/estado.py preencher <atena.conf> <modelo> <destino>", file=sys.stderr)
        return 2
    _, conf, origem, destino = argv
    try:
        with open(origem, "rb") as f:
            texto = renderizar(f.read(), ler_conf(conf), origem)
        with open(destino, "wb") as f:
            f.write(texto)
    except (OSError, ConfInvalida) as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
