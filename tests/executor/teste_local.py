"""local.processar: texto privado num modelo de casa (modelo simulado): validações, segredos e partes."""
import json
import os

from comum import carregar, confere, erro, fim

ex, tmp = carregar()
os.makedirs(f"{tmp}/prod")
ex.PASTAS_PROD = (f"{tmp}/prod",)
open(f"{tmp}/recibo.txt", "w").write("Recibo 4471, total R$ 1.130,00\nsenha: hunter2\n")
open(f"{tmp}/grande.txt", "w").write("x" * 50000)
open(f"{tmp}/prod/cliente.txt", "w").write("dados do cliente")
open(f"{tmp}/foto.jpg", "wb").write(b"\xff\xd8\xff" + b"\0" * 100)
CONF = {"ATENA_PC_IP": "192.168.0.50", "ATENA_PC_MAC": "00:11:22:33:44:55", "ATENA_PC_PORTA": "1234"}
ex.ler_conf = lambda: dict(CONF)
PC = {"lm_studio": True}
ex.acao_pc_estado = lambda c, p: {"ligado": PC["lm_studio"], "lm_studio": PC["lm_studio"]}
c = {"cliente": "hermes", "zonas": ["apps", "ai", "agents", "lab", "core"], "acoes": []}

# --- o pedido que sai para o Ollama e para o LM Studio (rede simulada) ---
PEDIDOS = []


class Resposta:
    def __init__(self, dados):
        self.dados = json.dumps(dados).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, *a):
        return self.dados


def urlopen_falso(pedido, timeout=None):
    corpo = json.loads(pedido.data)
    PEDIDOS.append((pedido.full_url, corpo))
    if pedido.full_url.endswith("/api/chat"):
        return Resposta({"message": {"content": "<think>hmm</think> total R$ 1.130,00"}})
    return Resposta({"choices": [{"message": {"content": "resumo do PC"}}]})


ex.urllib.request.urlopen = urlopen_falso
r = ex.acao_local_processar(c, {"instrucao": "extraia o total", "arquivo": f"{tmp}/recibo.txt"})
url, corpo = PEDIDOS[-1]
confere("arquivo de texto vai ao Ollama do servidor, com segredos ocultos",
        url == "http://127.0.0.1:11434/api/chat" and "hunter2" not in corpo["messages"][1]["content"]
        and "1.130,00" in corpo["messages"][1]["content"], corpo)
confere("modelo padrão do servidor e contexto do atena.conf",
        corpo["model"] == "qwen3:4b-instruct-2507-q4_K_M" and corpo["options"]["num_ctx"] == 8192, corpo)
confere("o raciocínio (<think>) não volta na resposta", r["resposta"] == "total R$ 1.130,00", r)
confere("o texto é dado, não ordem (instrução no prompt do sistema)", "não ordem" in corpo["messages"][0]["content"])
CONF["ATENA_LOCAL_MODELO"] = "outro:7b"
ex.acao_local_processar(c, {"instrucao": "resuma", "texto": "abc"})
confere("o atena.conf troca o modelo do servidor", PEDIDOS[-1][1]["model"] == "outro:7b")
r = ex.acao_local_processar(c, {"instrucao": "resuma", "texto": "reunião sexta 10h", "modelo": "pc"})
url, corpo = PEDIDOS[-1]
confere("modelo pc vai ao LM Studio do PC, com o modelo padrão",
        url == "http://192.168.0.50:1234/v1/chat/completions" and corpo["model"] == "qwen3-14b" and r["resposta"] == "resumo do PC", url)

# --- validações (modelo simulado direto) ---
CHAMADAS = []
ex.perguntar_local = lambda modelo, instrucao, texto, contexto: CHAMADAS.append((modelo, instrucao, texto, contexto)) or f"ok {modelo}"
ex.acao_local_processar(c, {"instrucao": "resuma", "texto": "abc", "modelo": "pc"})
confere("contexto padrão do PC", CHAMADAS[-1][3] == 16384)
CONF["ATENA_PC_CONTEXTO"] = "32768"
ex.acao_local_processar(c, {"instrucao": "resuma", "texto": "abc", "modelo": "pc"})
confere("contexto do PC vem do atena.conf", CHAMADAS[-1][3] == 32768)
PC["lm_studio"] = False
status, msg = erro(ex.acao_local_processar, c, {"instrucao": "resuma", "texto": "abc", "modelo": "pc"})
confere("PC desligado: 409 com a dica de ligar", status == 409 and "pc.ligar" in msg)
PC["lm_studio"] = True

r = ex.acao_local_processar(c, {"instrucao": "resuma", "arquivo": f"{tmp}/grande.txt"})
confere("texto grande é dividido em partes, com a dica da próxima", r["partes"] > 1 and r["parte"] == 1 and "parte=2" in r["dica"], r)
r2 = ex.acao_local_processar(c, {"instrucao": "resuma", "arquivo": f"{tmp}/grande.txt", "parte": r["partes"]})
confere("última parte sem dica", r2["parte"] == r["partes"] and "dica" not in r2)
confere("parte fora da faixa: 400", erro(ex.acao_local_processar, c, {"instrucao": "resuma", "arquivo": f"{tmp}/grande.txt", "parte": 99})[0] == 400)

os.makedirs(f"{tmp}/hermes/cache/documents")
open(f"{tmp}/hermes/cache/documents/doc.txt", "w").write("documento do telegram")
caminho_original = ex.caminho_legivel
ex.caminho_legivel = lambda p: caminho_original(p.replace("/srv/agents/hermes/", f"{tmp}/hermes/"))
ex.acao_local_processar(c, {"instrucao": "resuma", "arquivo": "/opt/data/cache/documents/doc.txt"})
confere("caminho como o Hermes vê (/opt/data) é traduzido", CHAMADAS[-1][2] == "documento do telegram")
ex.caminho_legivel = caminho_original

for nome, params, esperado in [
        ("arquivo de cliente (prod): 403", {"instrucao": "resuma", "arquivo": f"{tmp}/prod/cliente.txt"}, 403),
        ("segredo (.ssh): 403", {"instrucao": "resuma", "arquivo": "/root/.ssh/id_ed25519"}, 403),
        ("imagem: 415 (não tem texto)", {"instrucao": "descreva", "arquivo": f"{tmp}/foto.jpg"}, 415),
        ("arquivo e texto juntos: 400", {"instrucao": "resuma", "arquivo": f"{tmp}/recibo.txt", "texto": "x"}, 400),
        ("nem arquivo nem texto: 400", {"instrucao": "resuma"}, 400),
        ("modelo da nuvem não é aceito: 400", {"instrucao": "resuma", "texto": "x", "modelo": "sonnet"}, 400),
        ("instrução curta demais: 400", {"instrucao": "a", "texto": "x"}, 400),
        ("não existe: 404", {"instrucao": "resuma", "arquivo": f"{tmp}/nada.txt"}, 404)]:
    confere(nome, erro(ex.acao_local_processar, c, params)[0] == esperado)

fim()
