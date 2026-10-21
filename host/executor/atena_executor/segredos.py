"""Segredos: o que as consultas nunca leem (áreas do sistema e arquivos de chave, token e senha) e as
linhas com senha, token ou chave, que saem ocultas (***)."""

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
