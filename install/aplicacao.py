"""Aplica o estado desejado (install/estado.py) num servidor, por partes: grava o que difere ou falta,
guarda o que sobra, reinicia só o que mudou de verdade e confere. Antes de mexer, guarda tudo o que vai
mudar num backup (/var/backups/atena-aplicar/<quando>/antes.tar, com a lista do que foi criado), e o
desfazer volta a ele. Se um passo falha, desfaz sozinho.

Fica de fora, só avisado: o /etc/docker/daemon.json (aplicar reinicia o Docker e todos os containers) e
as stacks que ainda não existem no servidor (quem as cria, com os segredos, é o instalador).
"""
import datetime
import fcntl
import grp
import json
import os
import pwd
import shutil
import subprocess
import tarfile
from dataclasses import dataclass, field

import estado

BACKUPS = "/var/backups/atena-aplicar"
STACKS = "/opt/atena/stacks/"
UNIDADES = "/etc/systemd/system/"
# os arquivos de cada serviço do host: mudou de verdade (não só comentário), ele reinicia (se estava no ar)
SERVICOS = {
    "atena-docker-firewall.service": ("/usr/local/sbin/atena-docker-firewall", UNIDADES + "atena-docker-firewall.service"),
    "atena-executor.service": ("/usr/local/lib/atena-executor/", "/usr/local/sbin/atena-executor",
                               UNIDADES + "atena-executor.service"),
}


@dataclass
class Plano:
    escrever: list = field(default_factory=list)   # (Item, Resultado): grava o conteúdo do repositório
    guardar: list = field(default_factory=list)    # Resultado: sobra ou cópia antiga, vai para o backup
    manuais: list = field(default_factory=list)    # (Resultado, motivo): fica como está, só avisado
    passos: list = field(default_factory=list)     # (descrição, comando, pasta): o que roda depois


class Recusa(Exception):
    """O aplicar não começou (nada mudou), ou falhou e desfez (desfez=True)."""

    def __init__(self, mensagem, desfez=False):
        super().__init__(mensagem)
        self.desfez = desfez


class Sistema:
    """Roda os comandos de verdade ou, num ensaio (--alvo), só anota (e, para testar, finge uma falha)."""

    def __init__(self, alvo):
        self.ensaio = alvo not in ("", "/")
        self.anotados = []
        self.falhar = os.environ.get("ATENA_APLICAR_ENSAIO_FALHA", "") if self.ensaio else ""

    def rodar(self, comando, pasta=None):
        """(deu certo, saída)."""
        if self.ensaio:
            texto = " ".join(comando) + (f" (em {pasta})" if pasta else "")
            self.anotados.append(texto)
            if self.falhar and self.falhar in texto:
                self.falhar = ""   # falha uma vez só: o desfazer, depois, roda os mesmos passos
                return False, "falha de ensaio"
            return True, ""
        r = subprocess.run(comando, cwd=pasta, capture_output=True, text=True, timeout=900)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    def no_ar(self, pasta):
        """Se a stack tem container (uma stack parada fica parada; só os arquivos dela mudam)."""
        if self.ensaio:
            return True
        r = subprocess.run(["docker", "compose", "ps", "-q"], cwd=pasta, capture_output=True, text=True)
        return r.returncode == 0 and bool(r.stdout.strip())

    def ativo(self, unidade):
        if self.ensaio:
            return False
        return subprocess.run(["systemctl", "is-active", "--quiet", unidade]).returncode == 0


def so_comentario(r):
    return r is not None and r.detalhes == ["só nos comentários"]


def pasta_da_stack(caminho):
    """/opt/atena/stacks/<zona>/<nome> de um arquivo de stack, ou None."""
    if not caminho.startswith(STACKS):
        return None
    partes = caminho[len(STACKS):].split("/")
    return STACKS + "/".join(partes[:2]) if len(partes) > 2 else None


def planejar(raiz, alvo="/", conf=None, partes=None, donos=True):
    """O que aplicar faria: (Plano, conf, opções). Não muda nada."""
    resultados, c, tem = estado.conferir(raiz, alvo, conf, partes, donos)
    itens, _ = estado.desejado(raiz, c, tem)
    por_destino = {i.destino: i for i in itens}
    p = Plano()
    for r in resultados:
        if r.estado == "igual":
            continue
        if r.estado == "ilegivel":
            p.manuais.append((r, "sem permissão para ler (rode com sudo)"))
            continue
        if r.estado in ("sobra", "copia"):
            p.guardar.append(r)
            continue
        i = por_destino[r.caminho]
        stack = pasta_da_stack(i.destino)
        if i.chaves_json:
            p.manuais.append((r, "aplicar reinicia o Docker e todos os containers: faça à mão"))
        elif i.conteudo is None:   # a memória da Atena: só a semente, e só quando falta
            if r.estado == "falta" and i.semente is not None:
                p.escrever.append((i, r))
            else:
                p.manuais.append((r, "é da Atena: o aplicar só põe a semente quando o arquivo falta"))
        elif stack and not os.path.isfile(estado.no_alvo(alvo, stack + "/compose.yaml")):
            p.manuais.append((r, f"a stack {stack[len(STACKS):]} não existe neste servidor; quem a cria é o instalador"))
        else:
            p.escrever.append((i, r))
    p.passos = passos(p)
    return p, c, tem


def passos(p):
    """O que roda depois de gravar, na ordem: o systemd relê as unidades, o firewall e o executor reiniciam
    se mudaram de verdade, o SSH confere a configuração, e cada stack que mudou sobe de novo."""
    mudou = [(i.destino, r) for i, r in p.escrever] + [(r.caminho, None) for r in p.guardar if r.estado == "sobra"]
    de_verdade = [c for c, r in mudou if not so_comentario(r)]
    lista = []
    if any(c.startswith(UNIDADES) for c, _ in mudou):
        lista.append(("o systemd relê as unidades", ["systemctl", "daemon-reload"], None))
    for unidade, caminhos in SERVICOS.items():
        if any(c.startswith(caminhos) or c.startswith(UNIDADES + unidade + ".d/") for c in de_verdade):
            lista.append((f"reinicia {unidade}", ["systemctl", "try-restart", unidade], None))
    for c in de_verdade:   # temporizadores, vigias e sockets da Atena que mudaram
        nome = c[len(UNIDADES):] if c.startswith(UNIDADES) else ""
        if "/" not in nome and nome.endswith((".timer", ".path", ".socket")):
            lista.append((f"reinicia {nome}", ["systemctl", "try-restart", nome], None))
    if any(c.startswith("/etc/ssh/") for c, _ in mudou):
        # sem o SSH rodando, falta a pasta que o "sshd -t" exige (como no 90-ssh.sh)
        lista.append(("o SSH confere a configuração nova", ["sh", "-c", "install -d -m 0755 /run/sshd && sshd -t"], None))
        if any(c.startswith("/etc/ssh/") for c in de_verdade):
            lista.append(("o SSH relê a configuração", ["systemctl", "try-reload-or-restart", "ssh.service"], None))
    stacks = {}
    for c in de_verdade:
        s = pasta_da_stack(c) or (STACKS + "agents/hermes" if c == "/srv/agents/hermes/SOUL.md" else None)
        if s:
            stacks.setdefault(s, set()).add(c[len(s) + 1:] if c.startswith(s) else "SOUL.md")
    for s, arquivos in sorted(stacks.items()):
        nome = s[len(STACKS):]
        construir = ["--build"] if any(a.startswith("app/") for a in arquivos) else []
        if not construir and not arquivos & {"compose.yaml", "compose.override.yaml", ".env"}:
            # só um arquivo que o container lê ao subir (config.yaml, server.yml, o SOUL da Atena): reinicia
            lista.append((f"{nome}: reinicia", ["docker", "compose", "restart"], s))
        lista.append((f"{nome}: sobe com o compose e espera ficar saudável",
                      ["docker", "compose", "up", "-d", *construir, "--wait", "--wait-timeout", "300"], s))
    return lista


def _dono(i, ensaio):
    if ensaio or not i.dono:
        return None
    return pwd.getpwnam(i.dono).pw_uid, grp.getgrnam(i.grupo).gr_gid


def _criar_pasta(pasta, ids, criados):
    if os.path.isdir(pasta):
        return
    _criar_pasta(os.path.dirname(pasta), ids, criados)
    os.mkdir(pasta, 0o755)
    if ids:
        os.chown(pasta, *ids)
    criados.append(pasta)


def _raiz(alvo):
    return "/" if alvo in ("", "/") else alvo


def _rel(alvo, caminho):
    return os.path.relpath(estado.no_alvo(alvo, caminho), _raiz(alvo))


def aplicar(raiz, p, alvo="/", sistema=None, aviso=print):
    """Grava o plano, com backup antes; roda os passos; se um falhar, desfaz. Devolve a pasta do backup."""
    sistema = sistema or Sistema(alvo)
    if not p.escrever and not p.guardar:
        return None
    if not sistema.ensaio and any("atena-executor" in " ".join(c) for _, c, _ in p.passos) \
            and sistema.ativo("atena-claude.service"):
        raise Recusa("o Claude Code está trabalhando agora, e o executor precisa reiniciar; rode de novo quando terminar")
    base = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(estado.no_alvo(alvo, BACKUPS), mode=0o700, exist_ok=True)
    for n in range(1, 100):   # dois no mesmo segundo: -2, -3...
        quando = base if n == 1 else f"{base}-{n}"
        pasta = estado.no_alvo(alvo, f"{BACKUPS}/{quando}")
        if not os.path.exists(pasta):
            break
    os.mkdir(pasta, 0o700)
    existentes = [c for c in [i.destino for i, _ in p.escrever] + [r.caminho for r in p.guardar]
                  if os.path.lexists(estado.no_alvo(alvo, c))]
    with tarfile.open(f"{pasta}/antes.tar", "w") as t:
        for c in existentes:
            t.add(estado.no_alvo(alvo, c), arcname=_rel(alvo, c), recursive=False)
    manifesto = {"quando": quando, "repositorio": raiz, "criados": [], "passos": [[d, c, s] for d, c, s in p.passos],
                 "gravados": [i.destino for i, _ in p.escrever], "guardados": [r.caminho for r in p.guardar],
                 "desfeito": None}
    criados = []
    try:
        for i, _ in p.escrever:
            destino = estado.no_alvo(alvo, i.destino)
            ids = _dono(i, sistema.ensaio)
            _criar_pasta(os.path.dirname(destino), ids if ids and i.dono != "root" else None, criados)
            novo = destino + ".aplicar-novo"
            with open(novo, "wb") as f:
                f.write(i.conteudo if i.conteudo is not None else i.semente)
            os.chmod(novo, i.modo if i.modo is not None else 0o600)   # sem modo, só a semente da memória
            if ids:
                os.chown(novo, *ids)
            if not os.path.lexists(destino):
                criados.append(destino)
            os.replace(novo, destino)
        for r in p.guardar:
            os.remove(estado.no_alvo(alvo, r.caminho))
    finally:
        manifesto["criados"] = [os.path.relpath(c, _raiz(alvo)) for c in criados]
        with open(f"{pasta}/manifesto.json", "w") as f:
            json.dump(manifesto, f, ensure_ascii=False, indent=1)
    falha = _rodar_passos(p.passos, sistema, aviso)
    if falha:
        aviso(f"falhou: {falha}; desfazendo")
        try:
            desfazer(alvo, quando, sistema, aviso)
        except Recusa as e:
            raise Recusa(f"{falha}; {e}", desfez=True)
        raise Recusa(f"{falha}; o servidor voltou ao que era (backup em {pasta})", desfez=True)
    return pasta


def _rodar_passos(lista, sistema, aviso):
    for descricao, comando, pasta in lista:
        if comando[:2] == ["docker", "compose"] and not sistema.no_ar(pasta):
            aviso(f"  -      {descricao}: a stack está parada; ficou só com os arquivos novos")
            continue
        ok, saida = sistema.rodar(comando, pasta)
        aviso(f"  {'ok   ' if ok else 'FALHA'}  {descricao}" + (f": {saida[-300:]}" if saida and not ok else ""))
        if not ok:
            return descricao
    return None


def backups(alvo="/"):
    """As pastas de backup, da mais nova para a mais velha: [(quando, manifesto)]."""
    base = estado.no_alvo(alvo, BACKUPS)
    try:
        nomes = sorted(os.listdir(base), reverse=True)
    except FileNotFoundError:
        return []
    lista = []
    for n in nomes:
        try:
            with open(f"{base}/{n}/manifesto.json") as f:
                lista.append((n, json.load(f)))
        except (OSError, ValueError):
            continue
    return lista


def desfazer(alvo="/", quando=None, sistema=None, aviso=print):
    """Volta ao backup (o mais novo que ainda não foi desfeito, ou o de quando) e roda os mesmos passos."""
    sistema = sistema or Sistema(alvo)
    candidatos = [(n, m) for n, m in backups(alvo) if (n == quando if quando else not m.get("desfeito"))]
    if not candidatos:
        raise Recusa("não há o que desfazer" + (f" (nenhum backup {quando})" if quando else ""))
    n, m = candidatos[0]
    pasta = estado.no_alvo(alvo, f"{BACKUPS}/{n}")
    for c in reversed(m["criados"]):
        caminho = os.path.join(_raiz(alvo), c)
        if os.path.isdir(caminho) and not os.path.islink(caminho):
            shutil.rmtree(caminho)
        elif os.path.lexists(caminho):
            os.remove(caminho)
    with tarfile.open(f"{pasta}/antes.tar") as t:
        t.extractall(_raiz(alvo), filter="fully_trusted")   # o backup é nosso, numa pasta só do root
    falha = _rodar_passos([tuple(x) for x in m["passos"]], sistema, aviso)
    m["desfeito"] = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    with open(f"{pasta}/manifesto.json", "w") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    if falha:
        raise Recusa(f"os arquivos voltaram, mas {falha} falhou: confira à mão")
    return n


class Trava:
    """Um aplicar de cada vez."""

    def __init__(self, alvo):
        self.caminho = estado.no_alvo(alvo, "/run/atena-aplicar.lock")

    def __enter__(self):
        os.makedirs(os.path.dirname(self.caminho), exist_ok=True)
        self.f = open(self.caminho, "w")
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Recusa("outro ./aplicar está rodando")
        return self

    def __exit__(self, *a):
        self.f.close()
