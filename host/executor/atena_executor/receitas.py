"""Receitas (módulo lab): o estilo de um site ou de um programa, estudado pelo Claude Code e guardado para
usar nos projetos.

receita.estudar com url abre o site no coletor (a imagem atena/coletor: um Chromium sem tela, sem IA, num
container de uma vez na rede lab-coletor, que alcança a internet e não a rede de casa nem o servidor) e
grava a coleta em /srv/lab/projetos/receita-<nome>/coleta. Com arquivo (um programa que o dono mandou:
APK, .exe, AppImage, app Electron...), copia o arquivo para alvo/ no mesmo projeto; com imagens, os
prints que o dono mandou vão para telas/. Depois põe o Claude Code para ler tudo com a skill receita (o
impeccable document, o REA e os descompiladores do lab, sem rede e sem rodar o programa) e escrever o
RECEITA.md e o receita.json.
Quando o trabalho termina bem, a receita vai para /srv/lab/receitas/<nome> e para o índice (SQLite com
busca por texto) que o painel e a Atena consultam; claude.tarefa com receitas=[...] leva receitas para
um projeto. Os arquivos são a receita de verdade: o índice se refaz a partir deles (indexar)."""

import base64
import grp
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shutil
import socket
import sqlite3
import stat
import subprocess
import threading
import time
import urllib.parse
import zipfile

from .arquivos import caminho_do_cliente, fora_da_zona, pastas_de_entrega
from .base import Cancelado, Erro, ler_conf, log, rodar
from .celular import avisar
from .claude import contas_claude, contas_prontas, lab_instalado, preparar_claude_tarefa, skills_claude
from .lab import CANCELAR, PROJETOS_LAB
from .pedidos import ESTADO, TERMINADOS, TRAVA, criar_pedido, executar, mudar
from .segredos import caminho_legivel, ocultar, recusar_banco


RECEITAS = "/srv/lab/receitas"                         # uma pasta por receita pronta (só o executor escreve)
INDICE_RECEITAS = "/var/lib/atena-executor/receitas.db"   # o índice: se refaz das pastas
COLETOR = "atena/coletor:1.0.0"                        # construído pelo instalador (host/lab/coletor)
REDE_COLETOR = "lab-coletor"                           # internet sim; casa, Tailscale e servidor não
TEMPO_COLETA = 240                                     # s; o coletor leva de 30 s a 2 min
MINUTOS_RECEITA = 45                                   # o trabalho do Claude Code que escreve a receita
PREFIXO = "receita-"                                   # o projeto do lab onde a receita é estudada
NOME_RECEITA = re.compile(r"[a-z0-9][a-z0-9-]{0,30}")  # receita-<nome> cabe nos 40 de um projeto
LIMITE_TEXTO = 200 * 1024                              # RECEITA.md e DESIGN.md
LIMITE_DADOS = 64 * 1024                               # receita.json
LIMITE_PRINT = 3 * 1024 * 1024
LIMITE_ALVO = 1024 ** 3                                # o programa estudado (o Ghidra com mais que isso não dá)
MAX_IMAGENS = 6                                        # prints que o dono manda junto (telas/tela-<n>)
PRINTS = ("pc.jpg", "pc-escuro.jpg", "tablet.jpg", "celular.jpg", "pc-inteira.jpg", "celular-inteira.jpg")
PRINT = re.compile(r"(pc|pc-escuro|tablet|celular|pc-inteira|celular-inteira)\.jpg|tela-[1-6]\.(jpg|png)")
JPEG, PNG = b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n"
MAX_RECEITAS_PROJETO = 3                               # claude.tarefa com receitas=[...]
ESTUDANDO = {}                                         # nome → pedido de receita.estudar coletando agora
TRAVA_INDICE = threading.Lock()
ESQUEMA = """
CREATE TABLE IF NOT EXISTS receitas (
  nome TEXT PRIMARY KEY, titulo TEXT, origem TEXT, estado TEXT, resumo TEXT, tags TEXT, paleta TEXT,
  fontes TEXT, trabalho TEXT, pedido TEXT, erro TEXT, criada REAL, atualizada REAL);
"""
BUSCA = ("CREATE VIRTUAL TABLE IF NOT EXISTS busca USING fts5(nome UNINDEXED, titulo, resumo, tags, texto, "
         "tokenize='unicode61 remove_diacritics 2')")


# --- o endereço -------------------------------------------------------------------------------------------

def resolver_nome(host, porta):
    """Os endereços IP de um nome (os testes trocam esta função para não depender da rede)."""
    return {i[4][0] for i in socket.getaddrinfo(host, porta, proto=socket.IPPROTO_TCP)}


def endereco_publico(url):
    """O endereço do site, conferido: http(s), sem usuário e senha, e apontando só para a internet. O
    firewall do coletor barra a rede de casa de qualquer jeito; aqui o dono fica sabendo na hora."""
    if not isinstance(url, str) or not 4 <= len(url.strip()) <= 2000:
        raise Erro(400, "url deve ser o endereço do site (ex.: https://exemplo.com)")
    url = url.strip()
    if not re.match(r"[a-z]+://", url, re.I):
        url = "https://" + url   # "exemplo.com" vira https://exemplo.com
    try:
        partes = urllib.parse.urlsplit(url)
        porta = partes.port
    except ValueError:
        raise Erro(400, "url não é um endereço válido")
    if partes.scheme.lower() not in ("http", "https") or not partes.hostname or partes.username or partes.password:
        raise Erro(400, "url deve ser http:// ou https://, sem usuário e senha")
    host = partes.hostname
    try:
        enderecos = resolver_nome(host, porta or (443 if partes.scheme.lower() == "https" else 80))
    except (OSError, UnicodeError):
        raise Erro(400, f"não achei o site {host} (o endereço está certo? o servidor está na internet?)")
    for e in enderecos:
        if not ipaddress.ip_address(str(e).split("%")[0]).is_global:
            raise Erro(400, f"{host} aponta para a rede de casa ou para o próprio servidor ({e}); o coletor "
                            "só abre sites da internet")
    return urllib.parse.urlunsplit((partes.scheme.lower(), partes.netloc.lower(), partes.path or "/", partes.query, ""))


def nome_do_site(url):
    """linear.app → linear-app; www.exemplo.com.br → exemplo-com-br."""
    host = re.sub(r"^www\d?\.", "", urllib.parse.urlsplit(url).hostname or "")
    return re.sub(r"[^a-z0-9]+", "-", host).strip("-")[:31].strip("-") or "site"


def nome_do_arquivo(caminho):
    """Linear-1.2.AppImage → linear-1-2; app-release.apk → app-release."""
    base = os.path.basename(caminho).lower()
    base = re.sub(r"\.(apk|aab|exe|msi|dll|appimage|asar|zip|jar|ipa|dmg|deb|wasm|bin|so|dylib)$", "", base)
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:31].strip("-") or "programa"


def arquivo_legivel(cliente, caminho, limite):
    """Um arquivo das pastas de entrega (os documentos do dono, os projetos do lab e o espaço da Atena, onde
    chega o que ele manda pelo Telegram), sem segredos nem bancos, até o limite. A Atena pode mandar o
    caminho como ela vê (/opt/data/...)."""
    real = caminho_legivel(caminho_do_cliente(caminho))
    if fora_da_zona(cliente, real):
        raise Erro(403, "arquivos de clientes (zona prod) estão fora do seu alcance")
    pastas = list(dict.fromkeys([*pastas_de_entrega(), os.path.realpath(PROJETOS_LAB)]))   # refazer lê do estudo
    if not any(real == p or real.startswith(p + "/") for p in pastas):
        raise Erro(403, "o arquivo precisa estar numa das pastas de entrega: " + ", ".join(pastas))
    if not os.path.isfile(real):
        raise Erro(404, f"não achei o arquivo {caminho}")
    recusar_banco(real)
    tamanho = os.path.getsize(real)
    if tamanho > limite:
        raise Erro(413, f"{os.path.basename(real)} tem {tamanho // 1024 ** 2} MB; o limite é {limite // 1024 ** 2} MB")
    return real


def imagens_validas(cliente, imagens):
    """Os prints que o dono mandou junto: até 6 JPEG ou PNG de verdade."""
    if imagens is None:
        return []
    if not isinstance(imagens, list) or len(imagens) > MAX_IMAGENS:
        raise Erro(400, f"imagens deve ser uma lista de até {MAX_IMAGENS} caminhos de prints (JPEG ou PNG)")
    reais = []
    for imagem in imagens:
        real = arquivo_legivel(cliente, imagem, LIMITE_PRINT)
        with open(real, "rb") as f:
            cabeca = f.read(8)
        if not cabeca.startswith((JPEG, PNG)):
            raise Erro(400, f"{os.path.basename(real)} não é JPEG nem PNG")
        reais.append(real)
    return list(dict.fromkeys(reais))


def tipo_do_arquivo(caminho):
    """O que o programa é, pelos primeiros bytes (e pelo índice, num ZIP): diz ao Claude Code por onde começar."""
    with open(caminho, "rb") as f:
        cabeca = f.read(4096)
    if cabeca.startswith(b"\x7fELF"):
        return "AppImage (Linux)" if cabeca[8:11] == b"AI\x02" else "ELF (Linux)"
    if cabeca.startswith(b"MZ"):
        return "PE (Windows: .exe ou .dll)"
    if cabeca[:4] in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe"):
        return "Mach-O (macOS)"
    if cabeca[:4] == b"\xca\xfe\xba\xbe":
        return "Mach-O universal ou classe Java"
    if cabeca.startswith(b"dex\n"):
        return "DEX (Android)"
    if cabeca.startswith(b"\0asm"):
        return "WebAssembly"
    if cabeca[:4] == b"\x04\x00\x00\x00" and b'{"files"' in cabeca[:64]:
        return "ASAR (Electron)"
    if cabeca.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(caminho) as z:
                nomes = z.namelist()[:50000]
        except (zipfile.BadZipFile, OSError):
            return "ZIP"
        if "AndroidManifest.xml" in nomes:
            return "APK (Android)"
        if "BundleConfig.pb" in nomes:
            return "AAB (Android)"
        if any(n.startswith("Payload/") and n.endswith(".app/Info.plist") for n in nomes):
            return "IPA (iOS)"
        if any(n.endswith(".asar") for n in nomes):
            return "ZIP com um app Electron (.asar)"
        if "META-INF/MANIFEST.MF" in nomes:
            return "JAR (Java)"
        return "ZIP"
    return "desconhecido"


def nome_valido(nome):
    if not isinstance(nome, str) or not NOME_RECEITA.fullmatch(nome):
        raise Erro(400, "nome deve ser curto, com letras minúsculas, números e hífen (ex.: linear-app)")
    return nome


# --- o índice ---------------------------------------------------------------------------------------------

def conectar():
    """O índice, criado na primeira vez. Sem FTS5 no SQLite (raro), a busca usa LIKE."""
    con = sqlite3.connect(INDICE_RECEITAS, timeout=10)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    try:
        con.execute(BUSCA)
    except sqlite3.OperationalError:
        pass
    return con


def com_busca(con):
    return con.execute("SELECT 1 FROM sqlite_master WHERE name = 'busca'").fetchone() is not None


def gravar_no_indice(nome, texto=None, **campos):
    """Cria ou atualiza a linha da receita; com texto, também o que a busca encontra."""
    for chave in ("tags", "paleta", "fontes"):
        if chave in campos:
            campos[chave] = json.dumps(campos[chave], ensure_ascii=False)
    campos["atualizada"] = time.time()
    with TRAVA_INDICE:
        con = conectar()
        try:
            with con:
                if con.execute("SELECT 1 FROM receitas WHERE nome = ?", (nome,)).fetchone() is None:
                    con.execute("INSERT INTO receitas (nome, criada) VALUES (?, ?)", (nome, time.time()))
                con.execute(f"UPDATE receitas SET {', '.join(f'{c} = ?' for c in campos)} WHERE nome = ?",
                            (*campos.values(), nome))
                if texto is not None and com_busca(con):
                    linha = con.execute("SELECT titulo, resumo, tags FROM receitas WHERE nome = ?", (nome,)).fetchone()
                    con.execute("DELETE FROM busca WHERE nome = ?", (nome,))
                    con.execute("INSERT INTO busca (nome, titulo, resumo, tags, texto) VALUES (?, ?, ?, ?, ?)",
                                (nome, linha["titulo"], linha["resumo"], " ".join(json.loads(linha["tags"] or "[]")), texto))
        finally:
            con.close()


def tirar_do_indice(nome):
    with TRAVA_INDICE:
        con = conectar()
        try:
            with con:
                con.execute("DELETE FROM receitas WHERE nome = ?", (nome,))
                if com_busca(con):
                    con.execute("DELETE FROM busca WHERE nome = ?", (nome,))
        finally:
            con.close()


def linhas_do_indice(nomes=None):
    with TRAVA_INDICE:
        con = conectar()
        try:
            if nomes is None:
                return [dict(r) for r in con.execute("SELECT * FROM receitas ORDER BY atualizada DESC")]
            return [dict(r) for r in con.execute(
                f"SELECT * FROM receitas WHERE nome IN ({', '.join('?' * len(nomes))})", list(nomes))]
        finally:
            con.close()


def indexar():
    """Ao subir: o índice segue as pastas. Receita pronta sem linha (índice novo ou perdido) entra, e linha
    de receita pronta cuja pasta sumiu sai."""
    if not os.path.isdir(RECEITAS):
        return
    no_indice = {r["nome"]: r for r in linhas_do_indice()}
    for nome in sorted(os.listdir(RECEITAS)):
        pasta = os.path.join(RECEITAS, nome)
        if not NOME_RECEITA.fullmatch(nome) or os.path.islink(pasta) or not os.path.isdir(pasta):
            continue
        if no_indice.get(nome, {}).get("estado") == "pronta":
            continue
        try:
            dados = json.loads(ler_seguro(pasta, "receita.json", limite=LIMITE_DADOS))
            texto = ler_seguro(pasta, "RECEITA.md")
            gravar_no_indice(nome, texto, estado="pronta", erro=None, **campos_do_indice(dados_validos(dados, nome)))
        except (Erro, OSError, ValueError) as e:
            log(evento="receita sem índice", receita=nome, erro=str(e))
    for nome, linha in no_indice.items():
        if linha["estado"] == "pronta" and not os.path.isdir(os.path.join(RECEITAS, nome)):
            tirar_do_indice(nome)


# --- ler e copiar sem seguir links -----------------------------------------------------------------------

def abrir_seguro(base, *partes):
    """Abre base/partes... sem seguir link simbólico em nenhum pedaço (a pasta do projeto é do Claude Code,
    que lê páginas da internet: um link ali não pode fazer o executor ler outra coisa). Devolve o fd."""
    fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for i, parte in enumerate(partes):
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", parte) or parte in (".", ".."):
                raise Erro(400, f"nome de arquivo inválido: {parte}")
            ultimo = i == len(partes) - 1
            novo = os.open(parte, os.O_RDONLY | os.O_NOFOLLOW | (0 if ultimo else os.O_DIRECTORY), dir_fd=fd)
            os.close(fd)
            fd = novo
        return fd
    except BaseException:
        os.close(fd)
        raise


def ler_bytes(base, *partes, limite):
    try:
        fd = abrir_seguro(base, *partes)
    except FileNotFoundError:
        raise Erro(404, f"falta {'/'.join(partes)}")
    except OSError as e:   # ELOOP: era um link
        raise Erro(422, f"{'/'.join(partes)} não é um arquivo comum ({e.strerror})")
    with os.fdopen(fd, "rb") as f:
        info = os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise Erro(422, f"{'/'.join(partes)} não é um arquivo comum")
        if info.st_size > limite:
            raise Erro(422, f"{'/'.join(partes)} passou de {limite // 1024} KB")
        return f.read(limite + 1)[:limite]


def ler_seguro(base, *partes, limite=LIMITE_TEXTO):
    return ler_bytes(base, *partes, limite=limite).decode("utf-8", errors="replace")


def escrever(caminho, dados):
    with open(os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640), "wb") as f:
        f.write(dados if isinstance(dados, bytes) else dados.encode())


# --- o receita.json ---------------------------------------------------------------------------------------

def texto_limpo(valor, limite):
    return re.sub(r"\s+", " ", valor).strip()[:limite] if isinstance(valor, str) else ""


def dados_validos(dados, nome):
    """O receita.json que o Claude Code escreveu, só com o que a tela e a busca usam, nos tamanhos certos."""
    if not isinstance(dados, dict):
        raise Erro(422, "receita.json deve ser um objeto JSON")
    lista = lambda chave, n: [x for x in dados.get(chave) or [] if isinstance(x, (dict, str))][:n]  # noqa: E731
    paleta = [{"nome": texto_limpo(c.get("nome"), 40), "valor": texto_limpo(c.get("valor"), 60),
               "uso": texto_limpo(c.get("uso"), 80)} for c in lista("paleta", 16) if isinstance(c, dict)]
    fontes = [{"familia": texto_limpo(f.get("familia"), 60), "uso": texto_limpo(f.get("uso"), 80),
               "licenca": texto_limpo(f.get("licenca"), 60)} for f in lista("fontes", 8) if isinstance(f, dict)]
    return {"titulo": texto_limpo(dados.get("titulo"), 120) or nome,
            "resumo": texto_limpo(dados.get("resumo"), 600),
            "tags": [texto_limpo(t, 30) for t in lista("tags", 12) if isinstance(t, str) and t.strip()],
            "paleta": [c for c in paleta if c["valor"]], "fontes": [f for f in fontes if f["familia"]]}


def campos_do_indice(dados):
    return {k: dados[k] for k in ("titulo", "resumo", "tags", "paleta", "fontes")}


# --- estudar ----------------------------------------------------------------------------------------------

def coletor_instalado():
    return rodar(["docker", "image", "inspect", COLETOR], 15)[0] == 0


def pedido_da_receita(params, coleta):
    """O pedido ao Claude Code; o como (os arquivos, o formato, as regras) está na skill receita."""
    if params.get("arquivo"):
        texto = (f"Estude o software {coleta.get('arquivo') or os.path.basename(params['arquivo'])} "
                 f"({coleta.get('tipo') or '?'}, {max(1, coleta.get('kb', 0) // 1024)} MB) e escreva a receita "
                 f"{params['nome']}.\nO arquivo está em alvo/ (o alvo.json diz o tipo e o SHA-256). Não rode o "
                 "programa: leia e analise, com o REA e os descompiladores do lab. Você não tem rede.")
    else:
        texto = (f"Estude o estilo do site {params['url']} e escreva a receita {params['nome']}.\n"
                 f"A coleta do site já está em coleta/ (título da página: {coleta.get('titulo') or '?'}; "
                 f"{coleta.get('arquivos', 0)} arquivos). Você não tem rede para o site: trabalhe só com a coleta.")
    if params.get("imagens"):
        texto += (f"\nO dono mandou {len(params['imagens'])} print(s) em telas/: são a referência principal do "
                  "visual.")
    if params.get("foco"):
        texto += f"\nO dono quer atenção especial em: {params['foco']}"
    return texto


def preparar_receita_estudar(cliente, params):
    if not lab_instalado():
        raise Erro(503, "o lab não está instalado neste servidor (sudo ./install.sh --lab)")
    if "receita" not in skills_claude():
        raise Erro(503, "a skill receita não está ligada neste servidor (ATENA_CLAUDE_SKILLS=sim e "
                        "sudo ./install.sh --lab)")
    if (params.get("url") is None) == (params.get("arquivo") is None):
        raise Erro(400, "diga url (um site) ou arquivo (um programa no servidor, como o que o dono mandou), "
                        "um dos dois")
    if params.get("url") is not None:
        params["url"] = endereco_publico(params["url"])
        base = nome_do_site(params["url"])
    else:
        params["arquivo"] = arquivo_legivel(cliente, params["arquivo"], LIMITE_ALVO)
        base = nome_do_arquivo(params["arquivo"])
    params["imagens"] = imagens_validas(cliente, params.get("imagens"))
    params["nome"] = nome_valido(params.get("nome") or base)
    params["projeto"] = PREFIXO + params["nome"]   # app.cancelar <projeto> para a coleta no meio
    foco = params.get("foco")
    if foco is not None and (not isinstance(foco, str) or len(foco.strip()) > 500):
        raise Erro(400, "foco deve ser um texto de até 500 caracteres (o que olhar com mais atenção)")
    params["foco"] = foco.strip() if foco else None
    params["refazer"] = bool(params.get("refazer"))
    nome = params["nome"]
    linha = next(iter(linhas_do_indice([nome])), None)
    if linha and linha["estado"] == "pronta" and not params["refazer"]:
        raise Erro(409, f"já existe a receita {nome} (de {linha['origem']}); refazer=true estuda de novo, "
                        "ou escolha outro nome")
    with TRAVA:
        if nome in ESTUDANDO:
            raise Erro(409, f"a receita {nome} já está sendo coletada (pedido {ESTUDANDO[nome]})")
    if params.get("url") and not coletor_instalado():
        raise Erro(503, f"o coletor ({COLETOR}) não está neste servidor; rode sudo ./install.sh --lab")
    if not params.get("conta"):   # sem escolha: a do atena.conf (ATENA_RECEITAS_CONTA) ou a primeira com login
        params["conta"] = (ler_conf().get("ATENA_RECEITAS_CONTA")
                           or next((c for c in contas_claude() if c in contas_prontas()), None))
    # confere já agora o que o trabalho do Claude Code vai pedir (conta, modelo, fila, projeto livre)
    teste = {**params_do_trabalho(params, {}), "pedido": "conferência"}
    preparar_claude_tarefa(cliente, teste)
    params["conta"] = teste["conta"]
    if params.get("url"):
        origem = urllib.parse.urlsplit(params["url"]).hostname
        texto = f"O coletor abre {params['url']} (só internet, sem IA)"
    else:
        origem = os.path.basename(params["arquivo"])
        texto = f"O programa {params['arquivo']} vai para o projeto (o Claude Code lê, sem rodar)"
    texto += f" e o Claude Code ({params['conta']}) escreve a receita {nome}, que fica em {RECEITAS}/{nome}."
    if params["imagens"]:
        texto += f"\nPrints junto: {len(params['imagens'])}"
    if params["foco"]:
        texto += f"\nFoco: {params['foco']}"
    return f"Receita {nome}: estudar o estilo de {origem}", texto


def params_do_trabalho(params, coleta):
    return {"pedido": pedido_da_receita(params, coleta), "projeto": PREFIXO + params["nome"], "skill": "receita",
            "minutos": MINUTOS_RECEITA,
            **{k: params[k] for k in ("conta", "modelo", "esforco") if params.get(k)}}


def acao_receita_estudar(p):
    nome = p["params"]["nome"]
    with TRAVA:
        if nome in ESTUDANDO:
            raise Erro(409, f"a receita {nome} já está sendo coletada (pedido {ESTUDANDO[nome]})")
        ESTUDANDO[nome] = p["id"]
    threading.Thread(target=estudar, args=(p,), daemon=True).start()
    return None   # o pedido fica em "executando" até o trabalho do Claude Code entrar na fila


def estudar(p):
    params = p["params"]
    nome = params["nome"]
    try:
        if params.get("url"):
            mudar(p, etapa="coletando")
            coleta = coletar(params["url"], nome)
        else:
            mudar(p, etapa="copiando")
            coleta = copiar_alvo(params["arquivo"], nome)
        if params.get("imagens"):
            copiar_telas(params["imagens"], nome)
        mudar(p, etapa="escrevendo", coleta=coleta)
        anterior = next(iter(linhas_do_indice([nome])), None)
        trabalho = pedir_ao_claude(p, coleta)   # o índice já marca a receita (receita_comecou)
        gravar_no_indice(nome, titulo=(anterior or {}).get("titulo") or coleta.get("titulo") or nome,
                         origem=params.get("url") or coleta["origem"], pedido=p["id"])
        mudar(p, estado="concluido", resultado={
            "receita": nome, "trabalho": trabalho["id"], "coleta": coleta,
            "dica": "o Claude Code está escrevendo a receita; o celular avisa quando ela ficar pronta"})
        log(evento="receita coletada", receita=nome, pedido=p["id"], trabalho=trabalho["id"])
    except Cancelado as e:
        mudar(p, estado="cancelado", erro=str(e))
        avisar(f"Cancelado: receita {nome}", "A coleta parou; nada foi guardado.", tags=["no_entry"])
    except Erro as e:
        mudar(p, estado="falhou", erro=str(e))
        avisar(f"A receita {nome} não começou", str(e), tags=["x"])
    except Exception as e:
        mudar(p, estado="falhou", erro=f"erro interno: {e}")
        log(evento="erro ao estudar receita", pedido=p["id"], erro=repr(e))
        avisar(f"A receita {nome} não começou", "erro interno; veja journalctl -u atena-executor", tags=["x"])
    finally:
        with TRAVA:
            ESTUDANDO.pop(nome, None)


def grupo_lab():
    try:
        return grp.getgrnam("atena-lab").gr_gid
    except KeyError:   # fora do servidor (testes)
        return os.getgid()


def pasta_do_estudo(nome):
    """/srv/lab/projetos/receita-<nome>: o executor põe ali o que o Claude Code vai ler (coleta/, alvo/,
    telas/: só leitura para ele), e o Claude Code escreve a receita."""
    pasta = f"{PROJETOS_LAB}/{PREFIXO}{nome}"
    os.makedirs(pasta, exist_ok=True)
    if os.path.islink(pasta) or not os.path.isdir(pasta):
        raise Erro(409, f"{pasta} não é uma pasta")
    if os.stat(pasta).st_uid == os.getuid():
        os.chmod(pasta, 0o2775)   # o Claude Code (grupo atena-lab) escreve a receita aqui
    return pasta


def trocar_pasta(pasta, nome, nova):
    """Põe a pasta nova (já pronta) no lugar de <pasta>/<nome>; a velha (de um refazer) sai depois."""
    destino = f"{pasta}/{nome}"
    if os.path.lexists(destino):
        velha = f"{pasta}/.{nome}-{secrets.token_hex(3)}"
        os.rename(destino, velha)
        shutil.rmtree(velha, ignore_errors=True)
    os.rename(nova, destino)


def copiar_alvo(real, nome):
    """Copia o programa para alvo/ no projeto do estudo, com o alvo.json (o tipo e o SHA-256)."""
    pasta = pasta_do_estudo(nome)
    base = re.sub(r"[^\w.-]", "_", os.path.basename(real))[-100:].lstrip(".") or "programa"
    nova = f"{pasta}/.alvo-novo-{secrets.token_hex(3)}"
    os.mkdir(nova, 0o2755)
    try:
        resumo = hashlib.sha256()
        with open(real, "rb") as origem, open(os.open(f"{nova}/{base}", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), "wb") as copia:
            while bloco := origem.read(1024 * 1024):
                resumo.update(bloco)
                copia.write(bloco)
        tamanho = os.path.getsize(f"{nova}/{base}")
        alvo = {"arquivo": base, "tipo": tipo_do_arquivo(f"{nova}/{base}"), "tamanho": tamanho,
                "sha256": resumo.hexdigest(), "de": real}
        with open(os.open(f"{nova}/alvo.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), "w") as f:
            json.dump(alvo, f, ensure_ascii=False, indent=2)
        trocar_pasta(pasta, "alvo", nova)
    except BaseException:
        shutil.rmtree(nova, ignore_errors=True)
        raise
    return {"titulo": base, "arquivo": base, "tipo": alvo["tipo"], "kb": tamanho // 1024, "sha256": alvo["sha256"],
            "origem": f"{pasta}/alvo/{base}"}


def copiar_telas(imagens, nome):
    """Os prints que o dono mandou vão para telas/tela-<n>.<jpg|png> no projeto do estudo."""
    pasta = pasta_do_estudo(nome)
    nova = f"{pasta}/.telas-novas-{secrets.token_hex(3)}"
    os.mkdir(nova, 0o2755)
    try:
        for n, real in enumerate(imagens, 1):
            with open(real, "rb") as origem:
                dados = origem.read(LIMITE_PRINT + 1)[:LIMITE_PRINT]
            extensao = "png" if dados.startswith(PNG) else "jpg"
            with open(os.open(f"{nova}/tela-{n}.{extensao}", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), "wb") as f:
                f.write(dados)
        trocar_pasta(pasta, "telas", nova)
    except BaseException:
        shutil.rmtree(nova, ignore_errors=True)
        raise


def coletar(url, nome):
    """Roda o coletor e devolve o resumo da coleta. O container escreve como o executor, no grupo
    atena-lab: o Claude Code lê a coleta, mas não a muda."""
    projeto = PREFIXO + nome
    pasta = pasta_do_estudo(nome)
    destino = f"{pasta}/coleta"
    if os.path.lexists(destino):   # refazer: a coleta velha sai do caminho (a receita pronta fica até a nova)
        velha = f"{pasta}/.coleta-{time.strftime('%Y%m%d-%H%M%S')}"
        os.rename(destino, velha)
        shutil.rmtree(velha, ignore_errors=True)
    os.mkdir(destino, 0o2755)
    container = f"coletor-{nome}"
    rodar(["docker", "rm", "-f", container], 30)   # sobra de uma coleta que o executor perdeu no meio
    argv = ["docker", "run", "--rm", "--name", container, "--network", REDE_COLETOR,
            "--read-only", "--tmpfs", "/tmp:size=512m", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true", "--memory", "1g", "--cpus", "1.5", "--pids-limit", "512",
            "--shm-size", "256m", "--cgroup-parent", "atena-lab.slice", "--user", f"{os.getuid()}:{grupo_lab()}",
            "-v", f"{destino}:/saida", COLETOR, url, "/saida"]
    try:
        codigo, saida = rodar(argv, TEMPO_COLETA, cancelavel=projeto)
    except subprocess.TimeoutExpired:
        rodar(["docker", "rm", "-f", container], 30)
        raise Erro(504, f"o coletor passou de {TEMPO_COLETA // 60} min abrindo {url}; tente de novo mais tarde")
    if projeto in CANCELAR:   # app.cancelar no meio
        CANCELAR.discard(projeto)
        rodar(["docker", "rm", "-f", container], 30)
        raise Cancelado()
    try:
        coleta = json.loads(ler_bytes(destino, "coleta.json", limite=LIMITE_DADOS * 4))
    except (Erro, ValueError):
        coleta = {}
    ultima = (saida.strip().splitlines() or ["sem saída"])[-1][:300]
    if codigo != 0 or not isinstance(coleta, dict) or "prints/pc.jpg" not in (coleta.get("arquivos") or {}):
        raise Erro(502, f"o coletor não conseguiu abrir {url}: {ultima}")
    arquivos = coleta.get("arquivos") or {}
    return {"titulo": texto_limpo(coleta.get("titulo"), 120), "status": coleta.get("status"),
            "url_final": texto_limpo(coleta.get("url_final"), 300), "arquivos": len(arquivos),
            "kb": sum(v for v in arquivos.values() if isinstance(v, int)) // 1024,
            "avisos": [texto_limpo(a, 200) for a in (coleta.get("avisos") or [])[:5]]}


def pedir_ao_claude(p, coleta):
    """O trabalho do Claude Code que escreve a receita: um claude.tarefa do mesmo cliente, que aparece com
    os outros (claude.trabalhos, o Lab do painel) e se cancela do mesmo jeito."""
    params = params_do_trabalho(p["params"], coleta)
    cliente = {"cliente": p["cliente"], "zonas": p["zonas"], "acoes": []}
    titulo, _ = preparar_claude_tarefa(cliente, params)
    params["receita"] = p["params"]["nome"]   # depois do preparar, que tira o que vem de fora
    t = criar_pedido(cliente, "claude.tarefa", params, f"receita.estudar {p['id']}", titulo)
    mudar(t, estado="executando")
    executar(t)
    return t


def receita_comecou(nome, trabalho):
    """Um trabalho do Claude Code começou a escrever a receita (o de receita.estudar, ou um continuar dele)."""
    linha = next(iter(linhas_do_indice([nome])), None)
    pronta = bool(linha and linha["estado"] == "pronta" and os.path.isdir(f"{RECEITAS}/{nome}"))
    gravar_no_indice(nome, estado="pronta" if pronta else "estudando", trabalho=trabalho, erro=None)


def receita_terminou(trabalho, r):
    """O trabalho do Claude Code que escrevia a receita acabou (claude.concluir_claude chama)."""
    nome = trabalho["params"]["receita"]
    resumo = (r.get("texto") or "").strip()
    linha = next(iter(linhas_do_indice([nome])), {})
    # refazer que deu errado: a receita anterior continua pronta, com o erro da tentativa anotado
    falhou = "pronta" if linha.get("estado") == "pronta" and os.path.isdir(f"{RECEITAS}/{nome}") else "falhou"
    if not r.get("ok") or r.get("cancelado"):
        gravar_no_indice(nome, estado=falhou, erro=ocultar(resumo)[:500] or "o Claude Code parou com erro")
        avisar(f"A receita {nome} não ficou pronta", f"{resumo[:2500]}\n\nO estudo ficou em "
               f"{PROJETOS_LAB}/{PREFIXO}{nome}; dá para continuar o trabalho {trabalho['id']}.", tags=["x"])
        return
    try:
        dados, texto = guardar_receita(nome, trabalho)
    except (Erro, OSError, ValueError) as e:
        gravar_no_indice(nome, estado=falhou, erro=str(e)[:500])
        avisar(f"A receita {nome} não ficou pronta", f"O Claude Code terminou, mas a receita veio com defeito: {e}. "
               f"Continue o trabalho {trabalho['id']} pedindo para corrigir.", tags=["x"])
        log(evento="receita com defeito", receita=nome, erro=str(e))
        return
    gravar_no_indice(nome, texto, estado="pronta", erro=None, **campos_do_indice(dados))
    avisar(f"Receita pronta: {dados['titulo']}", f"{dados['resumo'] or resumo[:1500]}\n\nPara usar: peça um projeto "
           f"no estilo da receita {nome}.", tags=["white_check_mark"])
    log(evento="receita pronta", receita=nome, trabalho=trabalho["id"])


def guardar_receita(nome, trabalho):
    """Copia a receita do projeto do estudo para /srv/lab/receitas/<nome>, conferida: RECEITA.md,
    receita.json, DESIGN.md (se houver) e os prints da coleta. A versão anterior só sai depois."""
    projeto = f"{PROJETOS_LAB}/{PREFIXO}{nome}"
    texto = ler_seguro(projeto, "RECEITA.md")
    if len(texto.strip()) < 200:
        raise Erro(422, "o RECEITA.md está vazio ou curto demais")
    try:
        dados = dados_validos(json.loads(ler_bytes(projeto, "receita.json", limite=LIMITE_DADOS)), nome)
    except ValueError as e:
        raise Erro(422, f"o receita.json não é JSON válido ({e})")
    try:
        design = ler_seguro(projeto, "DESIGN.md")
    except Erro as e:
        if e.status != 404:
            raise
        design = None
    os.makedirs(RECEITAS, exist_ok=True)
    nova = f"{RECEITAS}/.{nome}.nova-{secrets.token_hex(3)}"
    os.mkdir(nova, 0o2750)
    try:
        escrever(f"{nova}/RECEITA.md", texto)
        if design:
            escrever(f"{nova}/DESIGN.md", design)
        origem = next(iter(linhas_do_indice([nome])), {}).get("origem")
        escrever(f"{nova}/receita.json", json.dumps(
            {**dados, "nome": nome, "origem": origem, "trabalho": trabalho["id"],
             "feita": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False, indent=2) + "\n")
        os.mkdir(f"{nova}/prints", 0o2750)
        candidatos = [(("coleta", "prints", a), a) for a in PRINTS]
        candidatos += [(("telas", f"tela-{n}.{e}"), f"tela-{n}.{e}") for n in range(1, MAX_IMAGENS + 1) for e in ("jpg", "png")]
        for partes, arquivo in candidatos:
            try:
                imagem = ler_bytes(projeto, *partes, limite=LIMITE_PRINT)
            except Erro:
                continue
            if imagem.startswith(PNG if arquivo.endswith(".png") else JPEG):   # imagem de verdade
                escrever(f"{nova}/prints/{arquivo}", imagem)
        atual = f"{RECEITAS}/{nome}"
        velha = f"{RECEITAS}/.{nome}.velha-{secrets.token_hex(3)}"
        if os.path.lexists(atual):
            os.rename(atual, velha)
        os.rename(nova, atual)
        shutil.rmtree(velha, ignore_errors=True)
    except BaseException:
        shutil.rmtree(nova, ignore_errors=True)
        raise
    return dados, texto


# --- consultar, apagar e levar para um projeto -----------------------------------------------------------

def trabalho_rodando(linha):
    with TRAVA:
        t = ESTADO["pedidos"].get(linha["trabalho"] or "")
        return t if t is not None and t["estado"] not in TERMINADOS else None


def estado_de(linha):
    """O estado de uma receita: pronta, estudando, falhou, ou parou (o trabalho acabou sem dar a receita,
    porque passou do prazo ou o executor o perdeu)."""
    if linha["estado"] != "estudando":
        return linha["estado"], linha["erro"]
    if trabalho_rodando(linha):
        return "estudando", None
    with TRAVA:
        t = ESTADO["pedidos"].get(linha["trabalho"] or "") or {}
    return "parou", t.get("erro") or t.get("resumo") or "o trabalho acabou sem a receita"


def prints_de(nome):
    """Os prints da receita: os do coletor, na ordem de PRINTS, e depois os que o dono mandou."""
    pasta = f"{RECEITAS}/{nome}/prints"
    try:
        nomes = [n for n in os.listdir(pasta) if PRINT.fullmatch(n) and not os.path.islink(f"{pasta}/{n}")]
    except OSError:
        return []
    return sorted(nomes, key=lambda n: (PRINTS.index(n) if n in PRINTS else len(PRINTS), n))


def publica(linha):
    estado, erro = estado_de(linha)
    return {"nome": linha["nome"], "titulo": linha["titulo"], "origem": linha["origem"], "estado": estado,
            "de": "site" if str(linha["origem"] or "").startswith("http") else "programa",
            "resumo": linha["resumo"], "tags": json.loads(linha["tags"] or "[]"),
            "paleta": json.loads(linha["paleta"] or "[]"), "fontes": json.loads(linha["fontes"] or "[]"),
            "trabalho": linha["trabalho"], "erro": erro, "criada": linha["criada"], "atualizada": linha["atualizada"],
            "refazendo": estado == "pronta" and trabalho_rodando(linha) is not None,
            "prints": prints_de(linha["nome"]) if estado == "pronta" else []}


def acao_receita_lista(cliente, params):
    return {"receitas": [publica(r) for r in linhas_do_indice()], "pasta": RECEITAS}


def receita_pronta(nome):
    nome_valido(nome)
    linha = next(iter(linhas_do_indice([nome])), None)
    if linha and linha["estado"] != "pronta":
        raise Erro(409, f"a receita {nome} não está pronta ({estado_de(linha)[0]})")
    if not linha or not os.path.isdir(f"{RECEITAS}/{nome}"):
        raise Erro(404, f"não há receita {nome} (veja receita.lista)")
    return linha


def acao_receita_ver(cliente, params):
    nome = params.get("nome")
    linha = receita_pronta(nome)
    pasta = f"{RECEITAS}/{nome}"
    try:
        design = ocultar(ler_seguro(pasta, "DESIGN.md"))
    except Erro:
        design = None
    return {**publica(linha), "texto": ocultar(ler_seguro(pasta, "RECEITA.md")), "design": design,
            "pasta": pasta, "estudo": f"{PROJETOS_LAB}/{PREFIXO}{nome}"}


def acao_receita_procurar(cliente, params):
    texto = params.get("texto")
    if not isinstance(texto, str) or not 2 <= len(texto.strip()) <= 200:
        raise Erro(400, "texto deve ter de 2 a 200 caracteres (ex.: escuro minimalista, serifa)")
    palavras = re.findall(r"\w+", texto.lower())[:8]
    if not palavras:
        raise Erro(400, "texto precisa de pelo menos uma palavra")
    with TRAVA_INDICE:
        con = conectar()
        try:
            if com_busca(con):
                consulta = " ".join(f'"{p}"*' for p in palavras)
                achados = [(r["nome"], r["trecho"]) for r in con.execute(
                    "SELECT nome, snippet(busca, 4, '[', ']', '…', 14) AS trecho FROM busca WHERE busca MATCH ? "
                    "ORDER BY rank LIMIT 20", (consulta,))]
            else:
                filtro = " AND ".join("(lower(titulo || ' ' || resumo || ' ' || tags) LIKE ?)" for _ in palavras)
                achados = [(r["nome"], r["resumo"]) for r in con.execute(
                    f"SELECT nome, resumo FROM receitas WHERE {filtro} LIMIT 20", [f"%{p}%" for p in palavras])]
        finally:
            con.close()
    linhas = {r["nome"]: r for r in linhas_do_indice([n for n, _ in achados])} if achados else {}
    return {"texto": texto, "receitas": [{**publica(linhas[n]), "trecho": trecho} for n, trecho in achados if n in linhas]}


def acao_receita_print(cliente, params):
    nome, arquivo = params.get("nome"), params.get("print")
    receita_pronta(nome)
    if not isinstance(arquivo, str) or not PRINT.fullmatch(arquivo):
        raise Erro(400, "print deve ser um dos prints de receita.lista (ex.: pc.jpg, celular.jpg, tela-1.png)")
    imagem = ler_bytes(f"{RECEITAS}/{nome}", "prints", arquivo, limite=LIMITE_PRINT)
    tipo = "image/png" if imagem.startswith(PNG) else "image/jpeg"
    return {"nome": nome, "print": arquivo, "tipo": tipo, "base64": base64.b64encode(imagem).decode()}


def preparar_receita_apagar(cliente, params):
    nome = nome_valido(params.get("nome"))
    linha = next(iter(linhas_do_indice([nome])), None)
    if not linha and not os.path.isdir(f"{RECEITAS}/{nome}"):
        raise Erro(404, f"não há receita {nome} (veja receita.lista)")
    return (f"Apagar a receita {nome}",
            f"Sai do índice e de {RECEITAS}/{nome}, sem volta. O estudo ({PROJETOS_LAB}/{PREFIXO}{nome}) fica: "
            "app.apagar tira.")


def acao_receita_apagar(p):
    nome = p["params"]["nome"]
    pasta = f"{RECEITAS}/{nome}"
    if os.path.lexists(pasta):
        velha = f"{RECEITAS}/.{nome}.apagada-{secrets.token_hex(3)}"
        os.rename(pasta, velha)
        shutil.rmtree(velha, ignore_errors=True)
    tirar_do_indice(nome)
    log(evento="receita apagada", receita=nome, pedido=p["id"])
    return {"apagada": nome}


def receitas_prontas(nomes):
    """claude.tarefa com receitas: os nomes conferidos (de 1 a 3, todas prontas)."""
    if not isinstance(nomes, list) or not 1 <= len(nomes) <= MAX_RECEITAS_PROJETO:
        raise Erro(400, f"receitas deve ser uma lista de 1 a {MAX_RECEITAS_PROJETO} nomes (veja receita.lista)")
    for nome in nomes:
        receita_pronta(nome)
    return list(dict.fromkeys(nomes))
