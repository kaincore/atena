"""Segredos: o que as consultas nunca leem (áreas do sistema, arquivos de chave, token e senha, e o
conteúdo dos bancos de dados) e as linhas com senha, token ou chave, que saem ocultas (***)."""

import json
import os
import re

from .base import Erro


# Áreas que nunca saem do executor, nem como lista de nomes (prefixos do caminho real).
NUNCA_LER = ("/proc", "/sys", "/dev", "/run", "/var/lib/docker", "/var/lib/containerd",
             "/var/lib/tailscale", "/var/lib/atena-executor", "/var/lib/atena-claude/contas",
             "/etc/atena/executor", "/etc/ssl/private", "/etc/letsencrypt")
# Pastas (em qualquer lugar) e nomes de arquivo que guardam segredos.
PASTA_SEGREDO = re.compile(r"(^|/)(\.ssh|\.gnupg|\.claude|\.docker|\.aws|\.kube|\.password-store|"
                           r"\.vscode-server|\.config/atena|keys|secrets?)(/|$)", re.I)
SEGREDO = re.compile(r"(^|/)(\.env[^/]*|[^/]*\.(key|token|pem|p12|pfx|kdbx)|id_(?![^/]*\.pub$)[^/]+|[^/]*_key|"
                     r"g?shadow-?|tokens\.json|auth\.json|\.netrc|\.git-credentials|\.npmrc|\.pgpass|"
                     r"tailscaled\.state|\.[a-z]*_?history|\.viminfo|[^/]*permitidos[^/]*|[^/]*(secret|senha|password|credential)[^/]*)$", re.I)
# Dentro do texto: o valor de linhas com senha, token ou chave, e formatos conhecidos de token.
_SENSIVEL = (r"(?:(?:api|access|master|secret|private)[_-]?key|secret|token|senha|password|passwd|"
             r"bearer|authorization|credential|cookie|salt|webhook|dsn)")
OCULTAR = [
    (re.compile(r"(?im)^([\s-]*(?:export\s+)?[\"']?[\w.-]*" + _SENSIVEL + r"[\w.-]*[\"']?\s*[:=]\s*)(\S.*)$"), r"\1***"),
    (re.compile(r'(?i)("[\w.-]*' + _SENSIVEL + r'[\w.-]*"\s*:\s*)"[^"]*"'), r'\1"***"'),
    # no meio da linha (registros: "... login ok, password=abc")
    (re.compile(r"(?i)(\b[\w.-]*" + _SENSIVEL + r"[\w.-]*\s*[:=]\s*)(?!\*\*\*)[^\s,;&]+"), r"\1***"),
    (re.compile(r"(?i)(\w+://[^:/\s@]+:)[^@\s]+@"), r"\1***@"),
    (re.compile(r"\b(sk-[\w-]{16,}|gh[pousr]_\w{20,}|github_pat_\w{20,}|xox[abpr]-[\w-]{10,}|AKIA[0-9A-Z]{16}|"
                r"tskey-[\w-]{10,}|\d{8,10}:[\w-]{35}|eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,})"), "***"),
    (re.compile(r"(?i)\b(bearer\s+)[\w.~+/-]{8,}=*"), r"\1***"),
]
# o começo de um bloco PEM de verdade (só "PRIVATE KEY-----" pegava o próprio código do executor)
CHAVE_PRIVADA = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
# Bancos de dados: o conteúdo não sai nem lido nem copiado (os usuários e tokens do ntfy, os gastos do
# LiteLLM, as conversas). SQLite pelo nome e pelo começo do arquivo; Redis pelo nome (o AOF é texto);
# Postgres pela pasta de dados, que tem um PG_VERSION na raiz.
BANCO = re.compile(r"(^|/)([^/]*\.(db|sqlite3?|db3|rdb|aof)(-(wal|shm|journal))?|appendonlydir)(/|$)", re.I)
CABECA_SQLITE = b"SQLite format 3\0"


def ocultar(texto):
    for regra, troca in OCULTAR:
        texto = regra.sub(troca, texto)
    return texto


def caminho_legivel(caminho):
    if not isinstance(caminho, str) or not caminho.startswith("/") or len(caminho) > 4096:
        raise Erro(400, "caminho deve ser absoluto")
    real = os.path.realpath(caminho)
    if any(real == p or real.startswith(p + "/") for p in NUNCA_LER):
        raise Erro(403, "essa área do sistema não sai do executor")
    if PASTA_SEGREDO.search(real) or SEGREDO.search(real):
        raise Erro(403, "esse arquivo guarda segredos e não sai do servidor")
    return real


def pasta_do_postgres(pasta):
    while pasta not in ("/", ""):
        if os.path.isfile(os.path.join(pasta, "PG_VERSION")):
            return True
        pasta = os.path.dirname(pasta)
    return False


def e_banco(real):
    """real: um caminho já resolvido (caminho_legivel). Pastas valem pelo nome e pelo Postgres."""
    if BANCO.search(real) or pasta_do_postgres(real if os.path.isdir(real) else os.path.dirname(real)):
        return True
    try:
        with open(real, "rb") as f:
            return f.read(16) == CABECA_SQLITE
    except OSError:
        return False


def recusar_banco(real):
    if e_banco(real):
        raise Erro(403, "é um banco de dados: o conteúdo não sai do executor (para gastos, serviços e "
                        "pedidos, use as consultas próprias)")


def permitido(caminho):
    try:
        caminho_legivel(caminho)
        return True
    except Erro:
        return False


def curto(valor, tamanho=160):
    """Um valor de params para mostrar: texto curto e sem segredos (stack.editar manda o arquivo inteiro)."""
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
    texto = ocultar(texto)
    return texto if len(texto) <= tamanho else texto[:tamanho] + "…"
