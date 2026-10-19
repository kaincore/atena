"""Aprovação no celular: pedido, botões, aprovar, recusar, expirar e os limites."""
import threading
import time

from comum import carregar, confere, fim, ligar, pedir, token

ex, tmp = carregar()
ex.PEDIDOS = f"{tmp}/pedidos.json"
ex.ler = lambda caminho: "token-do-ntfy"
CONF = {"ATENA_NTFY_URL": "https://ntfy.exemplo:2586/", "ATENA_LAN_IP": "192.168.0.10"}
ex.ler_conf = lambda: dict(CONF)
ENVIADOS, NTFY = [], {"no_ar": True}


def ntfy_falso(topico, titulo, texto, prioridade=3, tags=(), acoes=()):
    if not NTFY["no_ar"]:
        raise OSError("conexão recusada")
    ENVIADOS.append({"topico": topico, "titulo": titulo, "texto": texto, "acoes": list(acoes)})


ex.ntfy = ntfy_falso
ZONA = {"arca": "apps"}
REINICIADOS = []


def rodar_falso(argv, tempo=30):
    if argv[:2] == ["docker", "ps"]:
        return 0, "\n".join(f"{s}\t/opt/atena/stacks/{z}/{s}\t{s}\trunning\tUp\tzone-{z}" for s, z in ZONA.items())
    if argv[:2] == ["docker", "restart"]:
        REINICIADOS.append(argv[2:])
        return 0, ""
    return 1, "inesperado"


ex.rodar = rodar_falso
hermes = token(ex, "hermes", ["servico.reiniciar", "status.servicos"], ["apps"])
painel = token(ex, "painel", ["servico.reiniciar"], ["apps"], aprovar=[])
ligar(ex)


def segredo(aviso, rotulo):
    return next(a["body"] for a in aviso["acoes"] if a["label"] == rotulo).split()[2]


def reiniciar(t):
    return pedir(ex, "POST", "/acao/servico.reiniciar", t, {"params": {"stack": "arca"}, "origem": "teste"})


# --- pedido e notificação ---
status, r = pedir(ex, "GET", "/acoes", hermes)
confere("/acoes avisa que reiniciar precisa do celular", "[precisa de aprovação no celular]" in r["acoes"]["servico.reiniciar"]
        and "aprovação" not in r["acoes"]["status.servicos"], r)
status, r = reiniciar(hermes)
confere("token sem o campo aprovar: 202 e nada roda ainda", status == 202 and r["estado"] == "aguardando" and not REINICIADOS, r)
id_ = r["pedido"]
aviso = ENVIADOS[-1]
confere("notificação no tópico aprovacoes, com Aprovar e Recusar",
        aviso["topico"] == "aprovacoes" and [a["label"] for a in aviso["acoes"]] == ["Aprovar", "Recusar"], aviso)
botao = aviso["acoes"][0]
confere("o botão chama o endereço do ntfy do atena.conf, tópico respostas",
        botao["url"] == "https://ntfy.exemplo:2586/respostas" and botao["headers"]["Authorization"] == "Bearer token-do-ntfy", botao)
status, r = pedir(ex, "GET", f"/pedido/{id_}", hermes)
confere("o cliente vê o pedido, sem o código dos botões nem as zonas",
        r["pedido"]["estado"] == "aguardando" and "segredo" not in r["pedido"] and "zonas" not in r["pedido"], r)
status, _ = pedir(ex, "GET", f"/pedido/{id_}", painel)
confere("outro cliente não vê o pedido: 404", status == 404)

# --- decisões ---
ex.tratar_resposta(f"aprovar {id_} " + "x" * 24)
confere("código errado não aprova", ex.ESTADO["pedidos"][id_]["estado"] == "aguardando" and not REINICIADOS)
ex.tratar_resposta(f"aprovar {id_}")
confere("mensagem incompleta é ignorada", ex.ESTADO["pedidos"][id_]["estado"] == "aguardando")


def aprovar_depois():
    time.sleep(0.3)
    ex.tratar_resposta(f"aprovar {id_} {segredo(aviso, 'Aprovar')}")


threading.Thread(target=aprovar_depois).start()
inicio = time.monotonic()
status, r = pedir(ex, "GET", f"/pedido/{id_}?esperar=5", hermes)
confere("GET /pedido?esperar segura até terminar", r["pedido"]["estado"] == "concluido" and time.monotonic() - inicio < 4, r)
confere("aprovado: reiniciou a stack e avisou 'Feito'", REINICIADOS == [["arca"]] and ENVIADOS[-1]["titulo"].startswith("Feito"))
ex.tratar_resposta(f"aprovar {id_} {segredo(aviso, 'Aprovar')}")
confere("toque repetido não roda de novo", REINICIADOS == [["arca"]])

status, r = reiniciar(hermes)
aviso2 = ENVIADOS[-1]
ex.tratar_resposta(f"recusar {r['pedido']} {segredo(aviso2, 'Recusar')}")
confere("recusado: nada roda", ex.ESTADO["pedidos"][r["pedido"]]["estado"] == "recusado" and len(REINICIADOS) == 1)

status, r = reiniciar(hermes)
ex.ESTADO["pedidos"][r["pedido"]]["expira"] = time.time() - 1
ex.tratar_resposta(f"aprovar {r['pedido']} {segredo(ENVIADOS[-1], 'Aprovar')}")
confere("aprovar depois de vencido: expirado, nada roda",
        ex.ESTADO["pedidos"][r["pedido"]]["estado"] == "expirado" and len(REINICIADOS) == 1)

status, r = reiniciar(hermes)
ex.ESTADO["pedidos"][r["pedido"]]["expira"] = time.time() - 1
original = ex.time.sleep
voltas = {"n": 0}


def uma_volta(_):
    voltas["n"] += 1
    if voltas["n"] > 1:
        raise StopIteration


ex.time.sleep = uma_volta
try:
    ex.acompanhar()
except StopIteration:
    pass
ex.time.sleep = original
confere("o acompanhamento vence pedidos sem resposta", ex.ESTADO["pedidos"][r["pedido"]]["estado"] == "expirado")

# --- a zona é conferida de novo na hora de rodar ---
status, r = reiniciar(hermes)
ZONA["arca"] = "prod"
ex.tratar_resposta(f"aprovar {r['pedido']} {segredo(ENVIADOS[-1], 'Aprovar')}")
time.sleep(0.3)
confere("stack que mudou para fora da zona enquanto esperava: falha",
        ex.ESTADO["pedidos"][r["pedido"]]["estado"] == "falhou" and len(REINICIADOS) == 1, ex.ESTADO["pedidos"][r["pedido"]])
ZONA["arca"] = "apps"

# --- tokens sem aprovação e limites ---
status, r = reiniciar(painel)
confere("token com aprovar vazio: roda na hora (200)", status == 200 and len(REINICIADOS) == 2, r)
for _ in range(ex.MAX_AGUARDANDO):
    reiniciar(hermes)
status, r = reiniciar(hermes)
confere("pedidos demais esperando: 429", status == 429, r)
for p in ex.ESTADO["pedidos"].values():
    p["estado"] = "expirado"
NTFY["no_ar"] = False
status, r = reiniciar(hermes)
confere("ntfy fora do ar: 503 e o pedido não fica pendurado",
        status == 503 and ex.ESTADO["pedidos"][max(ex.ESTADO["pedidos"], key=lambda i: ex.ESTADO["pedidos"][i]["criado"])]["estado"] == "falhou", r)
NTFY["no_ar"] = True
status, r = pedir(ex, "POST", "/acao/servico.reiniciar", hermes, {"params": {"stack": "outra"}})
confere("stack que não existe: 404 antes de incomodar o celular", status == 404)

# --- estado guardado em disco ---
ex.ESTADO["pedidos"].clear()
ex.carregar_estado()
confere("os pedidos sobrevivem a um reinício do executor", len(ex.ESTADO["pedidos"]) > 5)
CONF.pop("ATENA_NTFY_URL")
confere("sem ATENA_NTFY_URL, os botões usam o IP da rede de casa", ex.endereco_ntfy() == "http://192.168.0.10:2586")

fim()
