"""A ponte do Claude Code com o dono (dono.py), falando MCP de verdade com um executor de mentira:
pedidos de permissão (Aprovar/Recusar no celular) e perguntas (resposta do dono ou da Atena)."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

from comum import RAIZ, confere, fim

fila = tempfile.mkdtemp(prefix="teste-ponte-")
EMBRULHO = f"""
import importlib.machinery, sys
d = importlib.machinery.SourceFileLoader("dono", {os.path.join(RAIZ, "host", "lab", "dono.py")!r}).load_module()
d.FILA, d.ESPERA, d.ESPERA_PERGUNTA = {fila!r}, 3, 3
sys.argv = ["dono.py", "--trabalho", "abcd1234"]
d.main()
"""
proc = subprocess.Popen([sys.executable, "-I", "-c", EMBRULHO], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        text=True, bufsize=1)
RESPOSTAS, VISTOS = [], []   # o que o "executor" responde a cada pedido (None: fica calado)


def executor_falso():
    while True:
        for nome in sorted(os.listdir(fila)):
            if nome.startswith(".") or not nome.endswith((".pergunta", ".permissao")):
                continue
            caminho = os.path.join(fila, nome)
            with open(caminho) as f:
                dados = json.load(f)
            os.unlink(caminho)
            VISTOS.append((nome, dados))
            r = RESPOSTAS.pop(0)
            if r is not None:
                with open(caminho.rsplit(".", 1)[0] + ".resposta", "w") as f:
                    json.dump({"nonce": dados["nonce"], **r}, f)
        time.sleep(0.05)


threading.Thread(target=executor_falso, daemon=True).start()


def mandar(mensagem):
    proc.stdin.write(json.dumps(mensagem) + "\n")
    proc.stdin.flush()


def rpc(id_, metodo, params=None):
    mandar({"jsonrpc": "2.0", "id": id_, "method": metodo, "params": params or {}})
    return json.loads(proc.stdout.readline())


def permissao(id_, ferramenta, entrada):
    r = rpc(id_, "tools/call", {"name": "permissao", "arguments": {"tool_name": ferramenta, "input": entrada}})
    return json.loads(r["result"]["content"][0]["text"])


def perguntar(id_, **args):
    return rpc(id_, "tools/call", {"name": "perguntar", "arguments": args})["result"]["content"][0]["text"]


r = rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
confere("initialize responde com a versão pedida e tools", r["result"]["protocolVersion"] == "2025-06-18"
        and "tools" in r["result"]["capabilities"])
mandar({"jsonrpc": "2.0", "method": "notifications/initialized"})   # sem resposta
r = rpc(2, "tools/list")
confere("notificação não gera resposta; tools/list vem em seguida", r["id"] == 2)
confere("a ponte oferece permissao e perguntar", [t["name"] for t in r["result"]["tools"]] == ["permissao", "perguntar"])

# --- permissões ---
RESPOSTAS.append({"permitir": True, "motivo": ""})
d = permissao(3, "Bash", {"command": "cat /etc/hostname", "description": "ver o nome do servidor"})
confere("aprovado: allow com a entrada original", d == {"behavior": "allow", "updatedInput": {
    "command": "cat /etc/hostname", "description": "ver o nome do servidor"}}, d)
nome, pedido = VISTOS[-1]
confere("pedido na fila como <trabalho>-<n>.permissao, com comando e motivo", nome == "abcd1234-1.permissao"
        and pedido["detalhe"] == "cat /etc/hostname" and pedido["motivo"] == "ver o nome do servidor")
RESPOSTAS.append({"permitir": False, "motivo": "o dono recusou"})
d = permissao(4, "Edit", {"file_path": "/etc/hosts", "old_string": "a", "new_string": "b"})
confere("recusado: deny com o motivo", d["behavior"] == "deny" and "recusou" in d["message"], d)
confere("Edit mostra o arquivo, e o contador sobe", VISTOS[-1][0] == "abcd1234-2.permissao"
        and VISTOS[-1][1]["detalhe"] == "file_path: /etc/hosts", VISTOS[-1])
RESPOSTAS.append({"permitir": True, "nonce": "forjado"})
d = permissao(5, "Bash", {"command": "ls /"})
confere("resposta com nonce errado: deny", d["behavior"] == "deny" and "inválida" in d["message"], d)
RESPOSTAS.append(None)
inicio = time.time()
d = permissao(6, "Bash", {"command": "ls /opt"})
confere("sem resposta: deny depois do tempo", d["behavior"] == "deny" and "a tempo" in d["message"]
        and time.time() - inicio >= 2.5, d)

# --- perguntas ---
RESPOSTAS.append({"resposta": "Postgres", "quem": "dono"})
texto = perguntar(7, pergunta="SQLite ou Postgres?", opcoes=["SQLite", "Postgres", "MySQL", "Oracle"], por_que="muda o deploy")
nome, dados = VISTOS[-1]
confere("pergunta vai para a fila como <trabalho>-q1.pergunta, com até 3 opções",
        nome == "abcd1234-q1.pergunta" and dados["opcoes"] == ["SQLite", "Postgres", "MySQL"] and dados["por_que"])
confere("resposta do dono chega ao Claude Code", texto == "O dono respondeu: Postgres", texto)
RESPOSTAS.append({"resposta": "Use SQLite", "quem": "atena"})
texto = perguntar(8, pergunta="Qual porta?")
confere("resposta da Atena vem identificada", "a Atena (assistente dele) decidiu: Use SQLite" in texto
        and VISTOS[-1][0] == "abcd1234-q2.pergunta", texto)
RESPOSTAS.append(None)
inicio = time.time()
texto = perguntar(9, pergunta="Alguém aí?")
confere("ninguém responde: segue sozinho depois do tempo", "Ninguém respondeu" in texto and time.time() - inicio >= 2.5, texto)
RESPOSTAS.append({"resposta": "x", "quem": "dono", "nonce": "forjado"})
confere("resposta com nonce errado não vale", perguntar(10, pergunta="Teste de nonce?").startswith("Ninguém respondeu"))
confere("pergunta vazia é recusada sem ir para a fila", perguntar(11, pergunta=" ").startswith("A pergunta veio vazia"))
confere("fila limpa no fim", not [n for n in os.listdir(fila) if not n.startswith(".")], os.listdir(fila))

# --- o resto do protocolo ---
confere("ferramenta desconhecida: erro", "error" in rpc(12, "tools/call", {"name": "outra", "arguments": {}}))
confere("método desconhecido: erro -32601", rpc(13, "resources/list")["error"]["code"] == -32601)
proc.stdin.close()
proc.wait(5)
confere("sai quando o Claude Code fecha a conexão", proc.returncode == 0)

fim()
