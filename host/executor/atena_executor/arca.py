"""Arca: arca.lista lê os metadados, arca.guardar copia um arquivo para os uploads e acrescenta a
entrada no metadata.json (escrito no lugar, para o Arca continuar dono), arca.pegar traz uma cópia."""

import json
import mimetypes
import os
import re
import shutil
import time

from .arquivos import acao_arquivo_entregar, caminho_do_cliente, fora_da_zona, ler_texto
from .base import Erro, ler_conf, log
from .segredos import caminho_legivel


ARCA_UPLOADS = "/srv/apps/arca/uploads"
ARCA_META = "/srv/apps/arca/data/metadata.json"
LIMITE_ARCA = 50 * 1024 * 1024                   # o mesmo limite do envio pelo navegador


def endereco_arca():
    return f"http://{ler_conf().get('ATENA_LAN_IP')}:3002"


def arca_alcance(cliente):
    if "apps" not in cliente["zonas"]:
        raise Erro(403, "a zona apps (Arca) está fora do alcance deste cliente")


def arca_metadados():
    try:
        with open(ARCA_META, encoding="utf-8") as f:
            lista = json.load(f)
    except FileNotFoundError:
        raise Erro(503, "o Arca ainda não tem metadata.json (envie um arquivo pelo navegador uma vez)")
    except ValueError:
        raise Erro(500, "o metadata.json do Arca está corrompido")
    if not isinstance(lista, list):
        raise Erro(500, "o metadata.json do Arca está num formato inesperado")
    return lista


def arca_gravar(lista):
    """No lugar (r+ e truncate): o arquivo continua do Arca, que o reescreve a cada envio."""
    with open(ARCA_META, "r+", encoding="utf-8") as f:
        f.write(json.dumps(lista, indent=2, ensure_ascii=False))
        f.truncate()


def arca_item(m):
    return {"id": m.get("id"), "nome": m.get("originalName"), "tamanho_kb": round((m.get("size") or 0) / 1024),
            "data": m.get("uploadDate"), "tipo": m.get("mimetype"),
            "caminho": os.path.join(ARCA_UPLOADS, m.get("savedName") or "")}


def acao_arca_lista(cliente, params):
    arca_alcance(cliente)
    nome = params.get("nome")
    if nome is not None and (not isinstance(nome, str) or len(nome) > 200):
        raise Erro(400, "nome deve ser um pedaço do nome do arquivo")
    lista = arca_metadados()
    if nome:
        lista = [m for m in lista if nome.lower() in str(m.get("originalName", "")).lower()]
    lista.sort(key=lambda m: str(m.get("uploadDate", "")), reverse=True)
    return {"total": len(lista), "total_mb": round(sum(m.get("size") or 0 for m in lista) / 1e6, 1),
            "arquivos": [arca_item(m) for m in lista[:100]], "endereco": endereco_arca()}


def acao_arca_guardar(cliente, params):
    """Copia um arquivo do servidor (ou do espaço da Atena) para o Arca; texto vai com segredos ocultos."""
    arca_alcance(cliente)
    real = caminho_legivel(caminho_do_cliente(params.get("arquivo")))
    if fora_da_zona(cliente, real):
        raise Erro(403, "arquivos de clientes (zona prod) estão fora do seu alcance")
    if not os.path.lexists(real):
        raise Erro(404, "não existe")
    if not os.path.isfile(real):
        raise Erro(400, "não é um arquivo comum")
    tamanho = os.path.getsize(real)
    if tamanho > LIMITE_ARCA:
        raise Erro(413, f"o arquivo tem {tamanho // (1024 * 1024)} MB; o Arca aceita até 50 MB")
    nome = params.get("nome") or os.path.basename(real)
    if not isinstance(nome, str):
        raise Erro(400, "nome deve ser texto")
    nome = re.sub(r"[\x00-\x1f/\\]", "_", nome).strip()[:200]
    if nome in ("", ".", ".."):
        raise Erro(400, "nome inválido")
    texto = None
    if tamanho <= 5 * 1024 * 1024:
        texto, _ = ler_texto(real, 5 * 1024 * 1024)   # None se for binário; 403 se for chave privada
    ids = {str(m.get("id")) for m in arca_metadados()}
    agora = int(time.time() * 1000)
    while str(agora) in ids:
        agora += 1
    salvo = f"{agora}-{nome}"   # como o Arca nomeia os envios
    destino = os.path.join(ARCA_UPLOADS, salvo)
    with open(os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), "wb") as f:
        if texto is not None:
            f.write(texto.encode("utf-8"))
        else:
            with open(real, "rb") as origem:
                shutil.copyfileobj(origem, f)
    item = {"id": str(agora), "originalName": nome, "savedName": salvo, "size": os.path.getsize(destino),
            "mimetype": mimetypes.guess_type(nome)[0] or "application/octet-stream",
            "uploadDate": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(agora / 1000)) + f".{agora % 1000:03d}Z"}
    try:
        lista = arca_metadados()   # lê de novo logo antes de gravar: o dono pode ter enviado algo agora
        lista.append(item)
        arca_gravar(lista)
    except BaseException:
        os.remove(destino)
        raise
    log(evento="guardado no Arca", cliente=cliente["cliente"], arquivo=real, nome=nome, tamanho=item["size"])
    return {"guardado": nome, "id": item["id"], "tamanho_kb": round(item["size"] / 1024),
            "segredos_ocultos": texto is not None, "endereco": endereco_arca()}


def acao_arca_pegar(cliente, params):
    """Traz uma cópia de um arquivo do Arca para /opt/data/entregas (como arquivo.entregar)."""
    arca_alcance(cliente)
    id_ = params.get("id")
    if not isinstance(id_, (str, int)) or isinstance(id_, bool):
        raise Erro(400, "id deve ser o id do arquivo (arca.lista mostra)")
    m = next((m for m in arca_metadados() if str(m.get("id")) == str(id_)), None)
    if not m:
        raise Erro(404, "não há arquivo com esse id no Arca (arca.lista mostra os ids)")
    salvo = str(m.get("savedName") or "")
    if "/" in salvo or salvo in ("", ".", ".."):
        raise Erro(500, "o metadata.json do Arca tem um nome de arquivo inválido")
    resultado = acao_arquivo_entregar(cliente, {"caminho": os.path.join(ARCA_UPLOADS, salvo)})
    resultado["nome"] = m.get("originalName")
    return resultado
