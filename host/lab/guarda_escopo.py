#!/usr/bin/env python3
"""Guarda de escopo do lab (hook PreToolUse do Claude Code, matcher Bash).

Dentro do lab: não opina (vale o settings.json e o sandbox).
Fora do lab ou comando sensível: devolve "ask" (o Claude Code pergunta).
É uma lombada, não um muro: o muro é o sandbox do Claude Code.
"""
import json
import os
import re
import shlex
import sys

LAB = "/srv/lab"

# Pedem ok onde quer que apareçam no comando.
CRITICOS = r"\b(sudo|su|doas|pkexec|docker|systemctl|shutdown|reboot|poweroff|halt|mkfs\S*|visudo|chown|chgrp|usermod|useradd|userdel|ufw|iptables|nft|tailscale|crontab)\b"
# Pedem ok quando são o programa executado.
SENSIVEIS = {"service", "apt", "apt-get", "dpkg", "snap", "mount", "umount", "dd", "passwd", "kill", "pkill", "killall"}
# O programa de verdade vem depois destes.
PREFIXOS = {"env", "nice", "nohup", "time", "timeout", "xargs", "command", "exec", "stdbuf", "watch"}
# Caminhos de fora que não são "sair do lab".
LIVRES = ("/dev/null", "/dev/stdout", "/dev/stderr", "/dev/stdin", "/dev/fd/")


def perguntar(motivo):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": motivo,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def dentro_do_lab(caminho, cwd):
    p = os.path.expanduser(caminho)
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    p = os.path.realpath(p)  # resolve .. e links simbólicos
    return p == LAB or p.startswith(LAB + "/")


def sem_heredocs(cmd):
    """Tira o corpo dos heredocs (é texto, não comando)."""
    linhas, saida, fim = cmd.split("\n"), [], None
    for linha in linhas:
        if fim is not None:
            if linha.strip() == fim:
                fim = None
            continue
        saida.append(linha)
        m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", linha)
        if m:
            fim = m.group(1)
    return "\n".join(saida)


def main():
    try:
        dados = json.load(sys.stdin)
    except Exception:
        perguntar("guarda_escopo: entrada ilegível")
    cmd = dados.get("tool_input", {}).get("command", "") or ""
    cwd = dados.get("cwd") or os.getcwd()

    if not dentro_do_lab(cwd, "/"):
        perguntar(f"Sessão fora do lab (cwd = {cwd})")

    cmd = sem_heredocs(cmd)

    m = re.search(CRITICOS, cmd)
    if m:
        perguntar(f"Comando sensível ({m.group(1)}): {cmd}")

    # Shell escondido: $(...), crases, eval, bash -c, <(...).
    if re.search(r"\$\(|`|<\(|>\(|\beval\b|\b(ba|z|da)?sh\s+-c\b", cmd):
        perguntar(f"Comando com subshell/eval, conferir: {cmd}")

    # Variáveis que costumam apontar para fora do lab.
    if re.search(r"\$\{?(HOME|USER|OLDPWD|TMPDIR|XDG_\w+)\b", cmd):
        perguntar(f"Comando usa variável que aponta para fora do lab: {cmd}")

    try:
        linear = cmd.replace("\\\n", " ").replace("\n", " ; ")
        lex = shlex.shlex(linear, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        perguntar(f"Comando com aspas desbalanceadas, conferir: {cmd}")

    inicio = True    # o próximo token é o nome de um programa
    prefixo = False  # veio env/timeout/...: pular opções e números
    prog = ""
    for i, tok in enumerate(tokens):
        if re.fullmatch(r"[;&|()\n]+", tok):
            inicio, prefixo = True, False
            continue
        if re.fullmatch(r"[0-9]*[<>&|]+", tok):  # redirecionamento: o próximo é caminho
            continue
        if inicio:
            if re.fullmatch(r"[A-Za-z_]\w*=.*", tok):
                continue  # VAR=valor programa
            if prefixo and (tok.startswith("-") or re.fullmatch(r"\d+[smhd]?", tok)):
                continue
            prog = os.path.basename(tok)
            if prog in PREFIXOS:
                prefixo = True
                continue
            inicio, prefixo = False, False
            if prog in SENSIVEIS:
                perguntar(f"Comando sensível ({prog}): {cmd}")
            if prog == "cd" and (i + 1 >= len(tokens) or re.fullmatch(r"[;&|()\n]+", tokens[i + 1])):
                perguntar("cd sem destino vai para a home (fora do lab)")
            continue
        # Argumentos do programa atual.
        if prog == "rm" and re.fullmatch(r"-\w*[rRf]\w*|--recursive|--force", tok):
            perguntar(f"rm recursivo/forçado: {cmd}")
        if prog in {"pip", "pip3"} and tok in {"--user", "--break-system-packages"}:
            perguntar(f"pip instalando fora do lab: {cmd}")
        if prog in {"npm", "pnpm", "yarn"} and tok in {"-g", "--global"}:
            perguntar(f"Instalação global (fora do lab): {cmd}")
        valor = tok.split("=", 1)[1] if tok.startswith("-") and "=" in tok else tok
        if valor.startswith(LIVRES):
            continue
        if valor.startswith(("/", "~")) or valor == ".." or valor.startswith("../") or "/../" in valor:
            if not dentro_do_lab(valor, cwd):
                perguntar(f"Caminho fora do lab ({LAB}): {valor}")
    sys.exit(0)


if __name__ == "__main__":
    main()
