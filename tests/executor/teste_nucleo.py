"""Núcleo do executor: tokens, zonas, rotas e a lista fechada de ações."""
from comum import carregar, confere, fim, ligar, pedir, token

ex, tmp = carregar()

# docker ps de mentira: stack | pasta do compose | container | estado | status | redes
DOCKER = "\n".join("\t".join(c) for c in [
    ("arca", "/opt/atena/stacks/apps/arca", "arca", "running", "Up 2 hours", "zone-apps"),
    ("litellm", "/opt/atena/stacks/ai/litellm", "litellm", "running", "Up 2 hours", "zone-ai,svc-llm"),
    ("litellm", "/opt/atena/stacks/ai/litellm", "litellm-db", "running", "Up 2 hours", "litellm_interna"),
    ("cliente1", "/opt/atena/dockge/cliente1", "cliente1-web", "running", "Up 1 hour", "zone-prod"),
    ("misto", "/opt/atena/dockge/misto", "misto", "exited", "Exited (1)", "zone-lab,zone-core"),
    ("solto", "/home/alguem/solto", "solto", "running", "Up", "bridge"),
])
CHAMADAS = []


def rodar_falso(argv, tempo=30):
    CHAMADAS.append(argv)
    if argv[:2] == ["docker", "ps"]:
        return 0, DOCKER
    if argv[:2] == ["docker", "logs"]:
        return 0, f"log de {argv[-1]}"
    return 1, "comando inesperado"


ex.rodar = rodar_falso
hermes = token(ex, "hermes", ["status.servicos", "servico.logs"], ["apps", "ai", "lab"])
painel = token(ex, "painel", ["status.recursos"], ["prod", "core", "apps", "ai", "agents", "lab"])
ligar(ex)

# --- zonas ---
zonas = {c["container"]: c["zona"] for c in ex.containers()}
confere("zona pela pasta do compose", zonas["arca"] == "apps" and zonas["litellm"] == "ai")
confere("container sem rede de zona herda a zona da stack", zonas["litellm-db"] == "ai")
confere("stack do Dockge: zona pelas redes zone-*", zonas["cliente1-web"] == "prod")
confere("na dúvida, vale a zona mais restrita", zonas["misto"] == "core")
confere("fora das zonas: '?'", zonas["solto"] == "?")

# --- autenticação e rotas ---
status, r = pedir(ex, "GET", "/acoes")
confere("sem token: 401", status == 401 and not r["ok"])
status, r = pedir(ex, "GET", "/acoes", "atx-inventado")
confere("token desconhecido: 401", status == 401)
status, r = pedir(ex, "GET", "/acoes", hermes)
confere("/acoes mostra só as ações e zonas do cliente",
        status == 200 and set(r["acoes"]) == {"status.servicos", "servico.logs"} and r["zonas"] == ["apps", "ai", "lab"], r)
status, r = pedir(ex, "GET", "/outra", hermes)
confere("rota desconhecida: 404", status == 404)
status, r = pedir(ex, "POST", "/acao/sistema.desligar", hermes, {})
confere("ação que não existe: 404", status == 404)
status, r = pedir(ex, "POST", "/acao/status.recursos", hermes, {})
confere("ação existente, mas fora do token: 403", status == 403 and "não pode pedir" in r["erro"])
status, r = pedir(ex, "POST", "/acao/status.servicos", hermes, {"params": ["x"]})
confere("params que não é objeto: 400", status == 400)
status, r = pedir(ex, "POST", "/acao/status.servicos", hermes, cru=b"{nada")
confere("JSON quebrado: 400", status == 400)
confere("o pedido aceita até 1 MB", ex.LIMITE_PEDIDO == 1024 * 1024)
# acima do limite, o executor lê e joga fora o corpo antes de recusar: o cliente recebe o 413, não um
# broken pipe (antes, o teste usava um corpo pequeno e às vezes falhava no CI)
for _ in range(5):
    status, r = pedir(ex, "POST", "/acao/status.servicos", hermes, {"params": {"x": "a" * (2 * 1024 * 1024)}})
    confere("corpo acima do limite: 413", status == 413 and "grande demais" in r.get("erro", ""), (status, r))

# --- ações ---
status, r = pedir(ex, "POST", "/acao/status.servicos", hermes, {"params": {}, "origem": "teste"})
confere("status.servicos só devolve as zonas do cliente",
        status == 200 and {c["container"] for c in r["resultado"]} == {"arca", "litellm", "litellm-db"}, r)
status, r = pedir(ex, "POST", "/acao/servico.logs", hermes, {"params": {"stack": "litellm", "linhas": 20}})
confere("servico.logs junta os containers da stack",
        status == 200 and set(r["resultado"]) == {"litellm", "litellm-db"} and CHAMADAS[-1][:4] == ["docker", "logs", "--tail", "20"], r)
status, r = pedir(ex, "POST", "/acao/servico.logs", hermes, {"params": {"stack": "cliente1"}})
confere("stack da zona prod para quem não tem prod: 403", status == 403)
status, r = pedir(ex, "POST", "/acao/servico.logs", hermes, {"params": {"stack": "nao-existe"}})
confere("stack inexistente: 404", status == 404)
status, r = pedir(ex, "POST", "/acao/servico.logs", hermes, {"params": {"stack": "arca; rm -rf /"}})
confere("nome de stack com caracteres estranhos: 400", status == 400)
status, r = pedir(ex, "POST", "/acao/servico.logs", hermes, {"params": {"stack": "arca", "linhas": 9999}})
confere("linhas fora da faixa: 400", status == 400)
status, r = pedir(ex, "POST", "/acao/status.recursos", painel, {})
confere("status.recursos lê CPU, RAM e discos", status == 200 and r["resultado"]["ram_total_mb"] > 0 and "/" in r["resultado"]["discos"], r)

# --- administração dos tokens (linha de comando) ---
def sai(funcao, *args):
    """Mensagem do sys.exit da função, ou None se ela não saiu."""
    try:
        funcao(*args)
    except SystemExit as e:
        return str(e)
    return None


antes = ex.carregar_tokens()
ex.token_novo("hermes", "status.servicos", "apps")
depois = ex.carregar_tokens()
confere("token-novo de um cliente que já existe troca o token antigo",
        len(depois) == len(antes) and ex.hash_token(hermes) not in depois)
confere("token-novo guarda só o hash", all(len(h) == 64 for h in depois))
confere("token-novo recusa ação desconhecida", "acao.inventada" in (sai(ex.token_novo, "x", "acao.inventada", "apps") or ""))
confere("token-novo recusa zona desconhecida", "zona-inventada" in (sai(ex.token_novo, "x", "status.servicos", "zona-inventada") or ""))
confere("token-remover de quem não existe avisa", sai(ex.token_remover, "ninguem") is not None)
ex.token_remover("painel")
confere("token-remover revoga", all(c["cliente"] != "painel" for c in ex.carregar_tokens().values()))
status, _ = pedir(ex, "GET", "/acoes", painel)
confere("token revogado: 401 na hora, sem reiniciar", status == 401)

fim()
