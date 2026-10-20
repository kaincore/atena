#!/usr/bin/env python3
"""Atena: ponte entre o Claude Code sem tela e o dono (servidor MCP com duas ferramentas).

permissao: pedidos de permissão (uso automático, nunca pelo modelo).
perguntar: o Claude Code faz uma pergunta ao dono e espera a resposta. A pergunta vai para a fila
(fila/<trabalho>-q<n>.pergunta); o executor avisa o celular, a Atena repassa no Telegram, e a
resposta volta em fila/<trabalho>-q<n>.resposta (do dono, ou da Atena se ele não responder em 10 min).
Sem resposta em 30 min, o Claude Code segue sozinho.

O atena-claude-runner liga o Claude Code com --permission-prompt-tool mcp__dono__permissao. Quando
algo pede permissão (sair do lab, comando sensível, rodar fora do sandbox), o Claude Code chama
esta ferramenta. Ela deixa o pedido na fila (fila/<trabalho>-<n>.permissao) e espera a resposta
(fila/<trabalho>-<n>.resposta), que o executor escreve depois do toque do dono em Aprovar ou
Recusar no celular. Só vale a resposta com o nonce deste pedido. Sem resposta em 11 min, nega.

Uso: dono.py --trabalho <id>   (fala JSON-RPC do MCP por stdin/stdout, uma mensagem por linha)
"""
import json
import os
import re
import secrets
import sys
import time

FILA = "/var/lib/atena-claude/fila"
ESPERA = 11 * 60   # o executor dá 10 min ao dono; depois disso nega sozinho
ESPERA_PERGUNTA = 30 * 60   # o dono tem 10 min; depois a Atena decide; 30 min é o limite final

PERGUNTAR = {
    "name": "perguntar",
    "description": ("Faz uma pergunta ao dono (pelo Telegram e pelo celular) e espera a resposta, por até 30 min. "
                    "Use só para decisões que são dele e mudam o resultado (ex.: qual de duas abordagens, um dado "
                    "que só ele sabe). Não use para confirmar o óbvio nem para pedir permissão. Se ele não "
                    "responder em 10 min, a Atena, assistente dele, decide no lugar."),
    "inputSchema": {
        "type": "object",
        "properties": {
            "pergunta": {"type": "string", "description": "A pergunta, curta e completa, em português."},
            "opcoes": {"type": "array", "items": {"type": "string"}, "maxItems": 3,
                       "description": "Até 3 respostas prontas e curtas (viram botões no celular)."},
            "por_que": {"type": "string", "description": "Em uma frase, por que a resposta importa."},
        },
        "required": ["pergunta"],
    },
}

FERRAMENTA = {
    "name": "permissao",
    "description": "Pede ao dono, no celular, permissão para uma ação do Claude Code. Uso automático.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string"},
            "input": {"type": "object"},
            "tool_use_id": {"type": "string"},
        },
        "required": ["tool_name", "input"],
    },
}


def detalhe(ferramenta, entrada):
    """O que aparece na notificação: o comando, o arquivo ou o endereço."""
    if not isinstance(entrada, dict):
        return str(entrada)
    if ferramenta == "Bash" and "command" in entrada:
        return str(entrada["command"])
    for campo in ("file_path", "notebook_path", "path", "url", "pattern"):
        if campo in entrada:
            return f"{campo}: {entrada[campo]}"
    return json.dumps(entrada, ensure_ascii=False)


def pedir(trabalho, numero, ferramenta, entrada):
    """Deixa o pedido na fila e espera o dono. Devolve (permitir, motivo)."""
    chave = f"{trabalho}-{numero}"
    nonce = secrets.token_hex(16)
    pedido = {"nonce": nonce, "ferramenta": ferramenta, "detalhe": detalhe(ferramenta, entrada)[:600],
              "motivo": str(entrada.get("description", ""))[:300] if isinstance(entrada, dict) else ""}
    temporario = f"{FILA}/.{chave}.permissao.novo"   # o executor só pega *.permissao
    with open(os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640), "w") as f:
        json.dump(pedido, f, ensure_ascii=False)
    os.replace(temporario, f"{FILA}/{chave}.permissao")
    dados = esperar(chave, nonce, ESPERA, "permissao")
    if dados is None:
        return False, "o dono não respondeu a tempo"
    if dados is False:
        return False, "resposta inválida"
    return dados.get("permitir") is True, str(dados.get("motivo") or "")


def esperar(chave, nonce, segundos, tipo):
    """Espera fila/<chave>.resposta. Devolve os dados, None (sem resposta) ou False (nonce errado)."""
    resposta = f"{FILA}/{chave}.resposta"
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        try:
            with open(resposta) as f:
                dados = json.load(f)
        except FileNotFoundError:
            time.sleep(2)
            continue
        except ValueError:   # ainda sendo escrita
            time.sleep(1)
            continue
        os.unlink(resposta)
        if not isinstance(dados, dict) or not secrets.compare_digest(str(dados.get("nonce")), nonce):
            return False
        return dados
    try:   # o executor nem pegou o pedido: tira da fila
        os.unlink(f"{FILA}/{chave}.{tipo}")
    except FileNotFoundError:
        pass
    return None


def perguntar(trabalho, numero, argumentos):
    """Deixa a pergunta na fila e espera a resposta. Devolve o texto que o Claude Code recebe."""
    pergunta = str(argumentos.get("pergunta") or "").strip()
    if len(pergunta) < 3:
        return "A pergunta veio vazia. Escreva a pergunta completa."
    opcoes = argumentos.get("opcoes") if isinstance(argumentos.get("opcoes"), list) else []
    chave, nonce = f"{trabalho}-q{numero}", secrets.token_hex(16)
    temporario = f"{FILA}/.{chave}.pergunta.novo"   # o executor só pega *.pergunta
    with open(os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640), "w") as f:
        json.dump({"nonce": nonce, "pergunta": pergunta[:1500],
                   "opcoes": [str(o)[:60] for o in opcoes][:3],
                   "por_que": str(argumentos.get("por_que") or "")[:500]}, f, ensure_ascii=False)
    os.replace(temporario, f"{FILA}/{chave}.pergunta")
    dados = esperar(chave, nonce, ESPERA_PERGUNTA, "pergunta")
    if not dados:
        return ("Ninguém respondeu em 30 min. Decida com bom senso, siga em frente e registre a decisão "
                "no resumo final.")
    resposta, quem = str(dados.get("resposta") or "").strip(), str(dados.get("quem") or "")
    if quem == "atena":
        return (f"O dono não respondeu em 10 min, então a Atena (assistente dele) decidiu: {resposta}\n"
                "Siga com isso e diga no resumo que foi decisão da Atena.")
    if quem.startswith("dono"):
        return f"O dono respondeu: {resposta}"
    return resposta or "Sem resposta. Decida com bom senso e registre a decisão no resumo."


def decisao(trabalho, numero, argumentos):
    ferramenta = str(argumentos.get("tool_name") or "?")
    entrada = argumentos.get("input")
    entrada = entrada if isinstance(entrada, dict) else {}
    permitir, motivo = pedir(trabalho, numero, ferramenta, entrada)
    if permitir:
        return {"behavior": "allow", "updatedInput": entrada}
    return {"behavior": "deny",
            "message": f"Permissão negada ({motivo or 'o dono recusou'}). Siga sem isso, dentro da "
                       "pasta do projeto, e explique no resumo o que ficou faltando."}


def responder(id_, resultado=None, erro=None):
    mensagem = {"jsonrpc": "2.0", "id": id_}
    if erro:
        mensagem["error"] = erro
    else:
        mensagem["result"] = resultado
    sys.stdout.write(json.dumps(mensagem, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    if len(sys.argv) != 3 or sys.argv[1] != "--trabalho" or not re.fullmatch(r"[0-9a-f]{8}", sys.argv[2]):
        sys.exit(__doc__)
    trabalho, numero, perguntas = sys.argv[2], 0, 0
    for linha in sys.stdin:
        try:
            mensagem = json.loads(linha)
        except ValueError:
            continue
        metodo, id_ = mensagem.get("method"), mensagem.get("id")
        if id_ is None:   # notificação (ex.: notifications/initialized): não tem resposta
            continue
        if metodo == "initialize":
            versao = (mensagem.get("params") or {}).get("protocolVersion") or "2025-06-18"
            responder(id_, {"protocolVersion": versao, "capabilities": {"tools": {}},
                            "serverInfo": {"name": "atena-dono", "version": "1.0.0"}})
        elif metodo == "ping":
            responder(id_, {})
        elif metodo == "tools/list":
            responder(id_, {"tools": [FERRAMENTA, PERGUNTAR]})
        elif metodo == "tools/call":
            params = mensagem.get("params") or {}
            if params.get("name") == "perguntar":
                perguntas += 1
                try:
                    texto = perguntar(trabalho, perguntas, params.get("arguments") or {})
                except Exception as e:
                    texto = f"Não consegui fazer a pergunta ({e}). Decida com bom senso e registre no resumo."
                responder(id_, {"content": [{"type": "text", "text": texto}]})
                continue
            if params.get("name") != "permissao":
                responder(id_, erro={"code": -32602, "message": "ferramenta desconhecida"})
                continue
            numero += 1
            try:
                corpo = decisao(trabalho, numero, params.get("arguments") or {})
            except Exception as e:   # na dúvida, nega
                corpo = {"behavior": "deny", "message": f"Permissão negada (erro na ponte: {e})."}
            responder(id_, {"content": [{"type": "text", "text": json.dumps(corpo, ensure_ascii=False)}]})
        else:
            responder(id_, erro={"code": -32601, "message": f"método desconhecido: {metodo}"})


if __name__ == "__main__":
    main()
