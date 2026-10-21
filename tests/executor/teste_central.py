"""Central do painel: aprovacoes.lista, aprovacoes.decidir e atividade.lista."""
import json
import os
import time

from comum import carregar, confere, fim, ligar, pedir, token

ex, tmp = carregar()
ex.PEDIDOS = f"{tmp}/pedidos.json"
ex.CLAUDE = f"{tmp}/claude"
os.makedirs(f"{ex.CLAUDE}/fila")
ex.ler = lambda caminho: "token-do-ntfy"
ex.ler_conf = lambda: {"ATENA_NTFY_URL": "https://ntfy.exemplo:2586/", "ATENA_LAN_IP": "192.168.0.10"}
ENVIADOS = []
ex.ntfy = lambda topico, titulo, texto, prioridade=3, tags=(), acoes=(): ENVIADOS.append(
    {"topico": topico, "titulo": titulo, "texto": texto})
ZONA = {"arca": "apps", "clientes": "prod"}
REINICIADOS = []


def rodar_falso(argv, tempo=30):
    if argv[:2] == ["docker", "ps"]:
        return 0, "\n".join(f"{s}\t/opt/atena/stacks/{z}/{s}\t{s}\trunning\tUp\tzone-{z}" for s, z in ZONA.items())
    if argv[:2] == ["docker", "restart"]:
        REINICIADOS.append(argv[2:])
        return 0, ""
    return 1, "inesperado"


ex.rodar = rodar_falso
CENTRAL = ["aprovacoes.lista", "aprovacoes.decidir", "atividade.lista"]
hermes = token(ex, "hermes", ["servico.reiniciar", "aprovacoes.lista"], ["apps", "lab"])
painel = token(ex, "painel", CENTRAL + ["servico.reiniciar"], ["core", "apps", "lab"], aprovar=[])
prod = token(ex, "prod", ["servico.reiniciar"], ["prod"])
ligar(ex)


def reiniciar(t, stack="arca"):
    return pedir(ex, "POST", "/acao/servico.reiniciar", t, {"params": {"stack": stack}, "origem": "teste"})


def lista(t=painel):
    return pedir(ex, "POST", "/acao/aprovacoes.lista", t, {"params": {}})


def decidir(id_, decisao, resposta=None, t=painel):
    params = {"pedido": id_, "decisao": decisao}
    if resposta is not None:
        params["resposta"] = resposta
    return pedir(ex, "POST", "/acao/aprovacoes.decidir", t, {"params": params})


def esperar(id_, estados=("concluido", "falhou")):
    for _ in range(50):
        if ex.ESTADO["pedidos"][id_]["estado"] in estados:
            return
        time.sleep(0.05)


def esperar_aviso(comeco):
    """O aviso ao celular sai logo depois do estado mudar, na mesma thread."""
    for _ in range(50):
        if ENVIADOS and ENVIADOS[-1]["titulo"].startswith(comeco):
            return True
        time.sleep(0.05)
    return False


# --- lista: o pedido da Atena aparece com o texto que foi ao celular ---
status, r = reiniciar(hermes)
id_ = r["pedido"]
status, r = lista()
item = next((p for p in r["resultado"]["pendentes"] if p["id"] == id_), None)
confere("o pedido da Atena aparece na central", status == 200 and item and item["cliente"] == "hermes", r)
confere("com o texto que foi ao celular", item and item["texto"] == "Containers: arca"
        and ENVIADOS[-1]["texto"].startswith(item["texto"]), item)
confere("sem o código dos botões nem as zonas", item and not {"segredo", "zonas", "nonce"} & set(item), item)
status, r = pedir(ex, "GET", f"/pedido/{id_}", hermes)
confere("o texto também fica no pedido (campo aviso)", "Containers: arca" in r["pedido"].get("aviso", ""), r)

# --- decidir ---
status, r = decidir(id_, "aprovar", t=hermes)
confere("quem não tem aprovacoes.decidir não decide (403)", status == 403, r)
status, r = decidir(id_, "aprovar")
esperar(id_)
confere("o painel aprova: roda como o toque no celular", status == 200 and r["resultado"]["resultado"] == "aprovado"
        and REINICIADOS == [["arca"]] and ex.ESTADO["pedidos"][id_]["estado"] == "concluido", r)
confere("o pedido guarda quem decidiu", ex.ESTADO["pedidos"][id_].get("decidido_por") == "painel")
confere("o celular recebe o 'Feito'", esperar_aviso("Feito"), ENVIADOS[-1])
status, r = decidir(id_, "aprovar")
confere("decidir de novo: 409, nada roda", status == 409 and REINICIADOS == [["arca"]], r)
status, r = lista()
recente = next((p for p in r["resultado"]["recentes"] if p["id"] == id_), {})
confere("o decidido sai dos pendentes e vai para os recentes, com quem decidiu",
        all(p["id"] != id_ for p in r["resultado"]["pendentes"]) and recente.get("por") == "painel"
        and recente.get("estado") == "concluido", r)

status, r = reiniciar(hermes)
id2 = r["pedido"]
status, r = decidir(id2, "recusar")
confere("o painel recusa: nada roda e o celular sabe", r["resultado"]["resultado"] == "recusado"
        and ex.ESTADO["pedidos"][id2]["estado"] == "recusado" and len(REINICIADOS) == 1
        and ENVIADOS[-1]["titulo"].startswith("Recusado"), r)

status, r = reiniciar(hermes)
id3 = r["pedido"]
ex.ESTADO["pedidos"][id3]["expira"] = time.time() - 1
status, r = decidir(id3, "aprovar")
confere("aprovar um vencido: expirado, nada roda", r["resultado"]["resultado"] == "expirado" and len(REINICIADOS) == 1, r)
status, r = lista()
confere("vencido não aparece como pendente", all(p["id"] != id3 for p in r["resultado"]["pendentes"]), r)

for params, nome in (({"pedido": id_, "decisao": "talvez"}, "decisão inválida"),
                     ({"pedido": "00000000", "decisao": "aprovar"}, "pedido inexistente"),
                     ({"pedido": 5, "decisao": "aprovar"}, "pedido que não é texto")):
    status, r = pedir(ex, "POST", "/acao/aprovacoes.decidir", painel, {"params": params})
    confere(f"{nome}: recusado ({status})", status in (400, 404), r)

# --- limites: o próprio pedido e as zonas ---
eu = token(ex, "eu", CENTRAL + ["servico.reiniciar"], ["apps"])
status, r = reiniciar(eu)
status, r = decidir(r["pedido"], "aprovar", t=eu)
confere("ninguém aprova o próprio pedido (403)", status == 403 and len(REINICIADOS) == 1, r)
status, r = reiniciar(prod, "clientes")
id_prod = r["pedido"]
status, r = lista()
confere("pedido de um cliente com zona fora do alcance não aparece",
        all(p["id"] != id_prod for p in r["resultado"]["pendentes"]), r)
status, r = decidir(id_prod, "aprovar")
confere("e não pode ser decidido (404)", status == 404 and ex.ESTADO["pedidos"][id_prod]["estado"] == "aguardando", r)

# --- permissão do Claude Code ---
cliente_lab = {"cliente": "hermes", "zonas": ["apps", "lab"]}


def permissao():
    p = ex.criar_pedido(cliente_lab, "claude.permissao",
                        {"trabalho": "abcd0001", "chave": "abcd0001-1", "ferramenta": "Bash", "detalhe": "git push"},
                        "claude", "Claude Code quer usar Bash")
    ex.mudar(p, nonce="nonce-1")
    ex.pedir_aprovacao(p, "Claude Code pede: Bash", "Trabalho abcd0001: git push")
    return p["id"]


def resposta_da_ponte():
    with open(f"{ex.CLAUDE}/fila/abcd0001-1.resposta") as f:
        return json.load(f)


idp = permissao()
status, r = lista()
item = next(p for p in r["resultado"]["pendentes"] if p["id"] == idp)
confere("permissão do Claude Code aparece, sem a chave da fila", item["acao"] == "claude.permissao"
        and "chave" not in item["params"] and item["params"]["ferramenta"] == "Bash", item)
status, r = decidir(idp, "aprovar")
esperar(idp)
confere("aprovar a permissão responde à ponte com o nonce", resposta_da_ponte() == {"nonce": "nonce-1", "permitir": True, "motivo": ""},
        resposta_da_ponte())
idp = permissao()
decidir(idp, "recusar")
confere("recusar a permissão responde que não", resposta_da_ponte()["permitir"] is False
        and ex.ESTADO["pedidos"][idp]["estado"] == "recusado")

# permissão e pergunta são do Claude Code: o painel decide as dos trabalhos que ele mesmo mandou
do_painel = {"cliente": "painel", "zonas": ["core", "apps", "lab"]}
p = ex.criar_pedido(do_painel, "claude.permissao",
                    {"trabalho": "abcd0003", "chave": "abcd0003-1", "ferramenta": "Bash", "detalhe": "npm test"},
                    "claude", "Claude Code quer usar Bash")
ex.mudar(p, nonce="nonce-3")
ex.pedir_aprovacao(p, "Claude Code pede: Bash", "Trabalho abcd0003: npm test")
status, r = decidir(p["id"], "aprovar")
esperar(p["id"])
with open(f"{ex.CLAUDE}/fila/abcd0003-1.resposta") as f:
    resp = json.load(f)
confere("o painel aprova a permissão de um trabalho que ele mandou", status == 200 and resp["permitir"] is True, r)
p = ex.criar_pedido(do_painel, "claude.pergunta",
                    {"trabalho": "abcd0004", "chave": "abcd0004-q1", "projeto": "lista", "pergunta": "Porta 8000?",
                     "opcoes": ["sim", "não"], "por_que": "a porta"}, "claude", "Claude Code pergunta (lista)")
ex.mudar(p, estado="perguntando", nonce="nonce-q4", segredo="s" * 24)
status, r = decidir(p["id"], "responder", "sim")
confere("e responde a pergunta de um trabalho que ele mandou", status == 200 and r["resultado"]["resultado"] == "respondida", r)

# --- pergunta do Claude Code ---
p = ex.criar_pedido(cliente_lab, "claude.pergunta",
                    {"trabalho": "abcd0002", "chave": "abcd0002-q1", "projeto": "lista", "pergunta": "Azul ou verde?",
                     "opcoes": ["azul", "verde"], "por_que": "o tema"}, "claude", "Claude Code pergunta (lista)")
ex.mudar(p, estado="perguntando", nonce="nonce-q", segredo="s" * 24)
status, r = lista()
item = next(x for x in r["resultado"]["pendentes"] if x["id"] == p["id"])
confere("a pergunta aparece com as opções", item["tipo"] == "pergunta" and item["opcoes"] == ["azul", "verde"]
        and item["pergunta"] == "Azul ou verde?", item)
status, r = decidir(p["id"], "aprovar")
confere("pergunta não se aprova (400)", status == 400, r)
status, r = decidir(p["id"], "responder", "  ")
confere("resposta vazia: 400", status == 400, r)
status, r = decidir(p["id"], "responder", "verde, com borda azul")
with open(f"{ex.CLAUDE}/fila/abcd0002-q1.resposta") as f:
    resp = json.load(f)
confere("responder pelo painel devolve a resposta à ponte", r["resultado"]["resultado"] == "respondida"
        and resp == {"nonce": "nonce-q", "resposta": "verde, com borda azul", "quem": "dono (painel)"}, resp)
status, r = decidir(id2, "responder", "x")
confere("aprovação não se responde (400)", status == 400, r)

# --- aviso no celular (os agendamentos do painel avisam por aqui) ---
painel_cliente = {"cliente": "painel", "zonas": ["core", "apps", "lab"]}
r = ex.acao_aviso_celular(painel_cliente, {"titulo": "Agendamento falhou", "texto": "ligar o PC falhou\ntoken=abc123def"})
confere("aviso.celular manda ao ntfy, com os segredos ocultos", r == {"avisado": True}
        and ENVIADOS[-1]["titulo"] == "Agendamento falhou" and "abc123def" not in ENVIADOS[-1]["texto"], ENVIADOS[-1])
for params, nome in (({}, "sem título"), ({"titulo": "x" * 121}, "título longo"), ({"titulo": "a", "texto": 5}, "texto que não é texto")):
    try:
        ex.acao_aviso_celular(painel_cliente, params)
        confere(f"aviso {nome}: recusado", False)
    except ex.Erro as e:
        confere(f"aviso {nome}: recusado (400)", e.status == 400)
ntfy_antes = ex.ntfy
def ntfy_fora(*a, **k):
    raise OSError("conexão recusada")
ex.ntfy = ntfy_fora
try:
    ex.acao_aviso_celular(painel_cliente, {"titulo": "teste"})
    confere("ntfy fora do ar: 502", False)
except ex.Erro as e:
    confere("ntfy fora do ar: 502 (quem pediu fica sabendo)", e.status == 502)
ex.ntfy = ntfy_antes

# --- o botão do celular continua igual ---
status, r = reiniciar(hermes)
segredo = ex.ESTADO["pedidos"][r["pedido"]]["segredo"]
ex.tratar_resposta(f"aprovar {r['pedido']} {segredo}")
esperar(r["pedido"])
confere("aprovar pelo celular continua funcionando", ex.ESTADO["pedidos"][r["pedido"]]["estado"] == "concluido"
        and ex.ESTADO["pedidos"][r["pedido"]].get("decidido_por") == "celular" and len(REINICIADOS) == 2)

# --- atividade ---
def entrada(segundos, mensagem):
    return json.dumps({"__REALTIME_TIMESTAMP": str(int(segundos * 1e6)), "MESSAGE": mensagem})


REGISTRO = "\n".join([
    entrada(100, json.dumps({"evento": "executor no ar", "socket": "/x"})),
    entrada(110, json.dumps({"cliente": "hermes", "origem": "telegram", "acao": "stack.editar",
                             "params": {"stack": "arca", "conteudo": "x" * 500 + " password=abc123"}, "ok": True, "segundos": 0.2})),
    entrada(120, json.dumps({"cliente": "painel", "origem": "painel", "acao": "pc.ligar", "params": {}, "ok": False,
                             "erro": "PC gamer não configurado"})),
    entrada(130, json.dumps({"evento": "decisão do dono", "pedido": "abcd1234", "acao": "servico.reiniciar",
                             "decisao": "aprovar", "por": "painel"})),
    entrada(140, "Traceback (most recent call last): algo quebrou"),
    json.dumps({"__REALTIME_TIMESTAMP": "150000000", "MESSAGE": [1, 2, 3]}),
    "linha que não é JSON",
])
PEDIDAS = []
ex.ler_registro = lambda quantas: PEDIDAS.append(quantas) or REGISTRO


def atividade(**params):
    return pedir(ex, "POST", "/acao/atividade.lista", painel, {"params": params})


status, r = atividade()
itens = r["resultado"]["itens"]
confere("atividade do mais novo ao mais velho, pulando o que não dá para ler",
        status == 200 and [i["quando"] for i in itens] == [140, 130, 120, 110, 100], r)
confere("pede ao journal só as linhas que vai mostrar", PEDIDAS[-1] == 200, PEDIDAS)
confere("a decisão aparece com quem decidiu", itens[1].get("decisao") == "aprovar" and itens[1].get("por") == "painel", itens[1])
editar = itens[3]
confere("params longos saem cortados e sem segredos", len(editar["params"]["conteudo"]) <= 161
        and "abc123" not in json.dumps(editar), editar)
confere("linha que não é do log vira evento", itens[0]["evento"].startswith("Traceback"), itens[0])
status, r = atividade(cliente="hermes")
confere("filtro por cliente", [i.get("cliente") for i in r["resultado"]["itens"]] == ["hermes"] and PEDIDAS[-1] == 5000, r)
status, r = atividade(so_erros=True)
confere("só os erros", [i.get("acao") for i in r["resultado"]["itens"]] == ["pc.ligar"], r)
status, r = atividade(linhas=2)
confere("limite de linhas", len(r["resultado"]["itens"]) == 2, r)
for params, nome in (({"linhas": 0}, "linhas 0"), ({"linhas": 5000}, "linhas demais"), ({"cliente": "a b"}, "cliente inválido"),
                     ({"so_erros": "sim"}, "so_erros que não é booleano")):
    status, r = atividade(**params)
    confere(f"{nome}: 400", status == 400, r)
status, r = pedir(ex, "POST", "/acao/atividade.lista", hermes, {"params": {}})
confere("quem não tem atividade.lista: 403", status == 403, r)

fim()
