"""Leitura: as consultas enxergam o servidor inteiro (o serviço tem só CAP_DAC_READ_SEARCH, que lê
qualquer arquivo e não escreve nada), menos segredos (veja segredos.py).

arquivo.entregar copia um arquivo do servidor para /srv/agents/hermes/entregas (o Hermes vê em
/opt/data/entregas), com segredos ocultos se for texto; a cópia some em 24 h."""

import fnmatch
import glob
import os
import re
import secrets
import shutil
import time

from .base import Erro, log
from .segredos import CHAVE_PRIVADA, caminho_legivel, ocultar, permitido


def ler_texto(real, limite):
    """(texto com segredos ocultos, cortado?); texto None se o arquivo for binário."""
    with open(real, "rb") as f:
        bruto = f.read(limite + 1)
    if b"\0" in bruto[:8192]:
        return None, False
    texto = bruto[:limite].decode("utf-8", errors="replace")
    if CHAVE_PRIVADA.search(texto):
        raise Erro(403, "esse arquivo guarda uma chave privada e não sai do servidor")
    return ocultar(texto), len(bruto) > limite


def acao_arquivo_ler(cliente, params):
    """Lê qualquer arquivo ou pasta do servidor, menos segredos."""
    real = caminho_legivel(params.get("caminho"))
    if fora_da_zona(cliente, real):
        raise Erro(403, "arquivos de clientes (zona prod) estão fora do seu alcance")
    try:
        if os.path.isdir(real):
            nomes = sorted(os.listdir(real))
            return {"pasta": real, "total": len(nomes), "itens": [
                n + "/" if os.path.isdir(os.path.join(real, n)) and not os.path.islink(os.path.join(real, n)) else n
                for n in nomes[:1000]]}
        if not os.path.lexists(real):
            raise Erro(404, "não existe")
        if not os.path.isfile(real):
            raise Erro(400, "não é arquivo nem pasta comum")
        texto, cortado = ler_texto(real, 64 * 1024)
    except FileNotFoundError:
        raise Erro(404, "não existe")
    except PermissionError:
        raise Erro(403, "sem permissão de leitura")
    if texto is None:
        return {"arquivo": real, "binario": True, "tamanho": os.path.getsize(real)}
    return {"arquivo": real, "texto": texto, "cortado": cortado}


def acao_arquivo_buscar(cliente, params):
    """Procura um texto (sem diferenciar maiúsculas) nos arquivos de uma pasta, menos segredos."""
    raiz, texto = caminho_legivel(params.get("pasta")), params.get("texto")
    if not isinstance(texto, str) or not 2 <= len(texto) <= 200:
        raise Erro(400, "texto deve ter de 2 a 200 caracteres")
    if not os.path.isdir(raiz):
        raise Erro(400, "a pasta não existe")
    if fora_da_zona(cliente, raiz):
        raise Erro(403, "arquivos de clientes (zona prod) estão fora do seu alcance")
    alvo, achados, vistos, prazo = texto.lower(), [], 0, time.time() + 20
    for pasta, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = sorted(p for p in subpastas if permitido(os.path.join(pasta, p))
                              and not fora_da_zona(cliente, os.path.join(pasta, p)))
        for nome in sorted(arquivos):
            vistos += 1
            if vistos > 20000 or time.time() > prazo or len(achados) >= 100:
                return {"achados": achados, "incompleta": True}
            caminho = os.path.join(pasta, nome)
            if (not permitido(caminho) or os.path.islink(caminho) or not os.path.isfile(caminho)
                    or os.path.getsize(caminho) > 2 * 1024 * 1024):
                continue
            try:
                conteudo, _ = ler_texto(caminho, 2 * 1024 * 1024)
            except (OSError, Erro):
                continue
            for n, linha in enumerate((conteudo or "").splitlines(), 1):
                if alvo in linha.lower() and len(achados) < 100:
                    achados.append({"arquivo": caminho, "linha": n, "trecho": linha.strip()[:200]})
    return {"achados": achados, "incompleta": False}


ENTREGAS = "/srv/agents/hermes/entregas"   # o Hermes enxerga como /opt/data/entregas
ENTREGAS_HERMES = "/opt/data/entregas"
ESPACO_HERMES = ("/opt/data", "/srv/agents/hermes")   # como a Atena vê o espaço dela → onde ele fica
LIMITE_ENTREGA = 45 * 1024 * 1024          # o Telegram aceita até 50 MB por arquivo enviado por bot
VALIDADE_ENTREGA = 24 * 3600
TIPOS_ARQUIVO = {
    "foto": (".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".bmp", ".tif", ".tiff"),
    "documento": (".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md"),
    "planilha": (".xls", ".xlsx", ".ods", ".csv"),
    "video": (".mp4", ".mov", ".mkv", ".webm", ".avi"),
    "audio": (".mp3", ".ogg", ".oga", ".opus", ".m4a", ".wav"),
}
PASTAS_PROD = ("/srv/prod", "/opt/atena/stacks/prod")


def caminho_do_cliente(caminho):
    """A Atena vê o espaço dela como /opt/data; no servidor ele é /srv/agents/hermes."""
    origem, real = ESPACO_HERMES
    if isinstance(caminho, str) and (caminho == origem or caminho.startswith(origem + "/")):
        return real + caminho[len(origem):]
    return caminho


def fora_da_zona(cliente, real):
    """Arquivos de clientes (zona prod) só saem para quem tem a zona prod."""
    return "prod" not in cliente["zonas"] and any(real == p or real.startswith(p + "/") for p in PASTAS_PROD)


def acao_arquivo_procurar(cliente, params):
    """Procura arquivos pelo nome, pelo tipo e pela data (não pelo conteúdo), menos segredos."""
    raiz = caminho_legivel(params.get("pasta"))
    nome, tipo, dias = params.get("nome"), params.get("tipo"), params.get("dias")
    if nome is not None and (not isinstance(nome, str) or not 1 <= len(nome) <= 100):
        raise Erro(400, "nome deve ter de 1 a 100 caracteres (pedaço do nome, ou padrão como *.jpg)")
    if tipo is not None and tipo not in TIPOS_ARQUIVO:
        raise Erro(400, "tipo deve ser " + ", ".join(TIPOS_ARQUIVO))
    if dias is not None and (not isinstance(dias, int) or not 1 <= dias <= 3650):
        raise Erro(400, "dias deve ser um número de 1 a 3650 (modificados nos últimos N dias)")
    if not os.path.isdir(raiz):
        raise Erro(400, "a pasta não existe")
    if fora_da_zona(cliente, raiz):
        raise Erro(403, "arquivos de clientes (zona prod) estão fora do seu alcance")
    padrao = nome.lower() if nome else None
    curinga = bool(padrao) and any(c in padrao for c in "*?[")
    desde = time.time() - dias * 86400 if dias else None
    achados, vistos, prazo, incompleta = [], 0, time.time() + 20, False
    for pasta, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = sorted(p for p in subpastas if permitido(os.path.join(pasta, p))
                              and not fora_da_zona(cliente, os.path.join(pasta, p)))
        for n in arquivos:
            vistos += 1
            if vistos > 50000 or time.time() > prazo:
                incompleta = True
                break
            minusculo = n.lower()
            if padrao and not (fnmatch.fnmatch(minusculo, padrao) if curinga else padrao in minusculo):
                continue
            if tipo and not minusculo.endswith(TIPOS_ARQUIVO[tipo]):
                continue
            caminho = os.path.join(pasta, n)
            if not permitido(caminho) or os.path.islink(caminho) or not os.path.isfile(caminho):
                continue
            info = os.stat(caminho)
            if desde and info.st_mtime < desde:
                continue
            achados.append((info.st_mtime, {"arquivo": caminho, "tamanho_kb": round(info.st_size / 1024),
                                            "modificado": time.strftime("%Y-%m-%d %H:%M", time.localtime(info.st_mtime))}))
        if incompleta:
            break
    achados.sort(key=lambda a: a[0], reverse=True)   # os mais novos primeiro
    return {"achados": [a for _, a in achados[:100]], "total": len(achados), "incompleta": incompleta}


def limpar_entregas():
    limite = time.time() - VALIDADE_ENTREGA
    for caminho in glob.glob(f"{ENTREGAS}/*"):
        try:
            if os.path.isfile(caminho) and os.path.getmtime(caminho) < limite:
                os.unlink(caminho)
        except OSError:
            pass


def acao_arquivo_entregar(cliente, params):
    """Copia um arquivo do servidor para o espaço da Atena, para ela olhar ou mandar ao dono.
    Texto sai com os segredos ocultos (como em arquivo.ler); a cópia some em 24 h."""
    real = caminho_legivel(params.get("caminho"))
    if fora_da_zona(cliente, real):
        raise Erro(403, "arquivos de clientes (zona prod) estão fora do seu alcance")
    try:
        if not os.path.lexists(real):
            raise Erro(404, "não existe")
        if not os.path.isfile(real):
            raise Erro(400, "não é um arquivo comum (para pastas, use arquivo.procurar)")
        tamanho = os.path.getsize(real)
        if tamanho > LIMITE_ENTREGA:
            raise Erro(413, f"o arquivo tem {tamanho // (1024 * 1024)} MB; o Telegram só aceita até 45 MB")
        texto = None
        if tamanho <= 5 * 1024 * 1024:
            texto, _ = ler_texto(real, 5 * 1024 * 1024)   # None se for binário; 403 se for chave privada
        limpar_entregas()
        nome = re.sub(r"[^\w.-]", "_", os.path.basename(real))[-120:] or "arquivo"
        copia = f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}-{nome}"
        with open(os.open(f"{ENTREGAS}/{copia}", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640), "wb") as destino:
            if texto is not None:
                destino.write(texto.encode("utf-8"))
            else:
                with open(real, "rb") as origem:
                    shutil.copyfileobj(origem, destino)
    except FileNotFoundError:
        raise Erro(404, "não existe")
    except PermissionError:
        raise Erro(403, "sem permissão de leitura")
    log(evento="arquivo entregue", cliente=cliente["cliente"], arquivo=real, tamanho=tamanho)
    return {"arquivo": real, "copia": f"{ENTREGAS_HERMES}/{copia}", "tamanho_kb": round(tamanho / 1024),
            "segredos_ocultos": texto is not None,
            "dica": "para mandar ao dono: MEDIA:<copia> na resposta; a cópia some em 24 h"}
