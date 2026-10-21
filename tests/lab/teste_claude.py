"""O Claude Code no executor, sem root, sem ntfy e sem runner: validação do pedido, fila, permissões e
perguntas pelo celular, fim do trabalho, cancelar, continuar (inclusive em outra conta) e as contas."""
import json
import os
import time

from comum import SESSAO, botao, confere, erro, esperar, executor, fim, ligar, pedir, token, uma_volta

ex, tmp, avisos = executor()
for d in ("lista-compras", "outro", "terceiro", "quarto"):
    os.makedirs(f"{ex.PROJETOS_LAB}/{d}")
cliente = {"cliente": "hermes", "zonas": ["apps", "ai", "agents", "lab", "core"],
           "acoes": ["claude.tarefa", "app.publicar"], "aprovar": []}


def ler_json(caminho):
    with open(caminho) as f:
        return json.load(f)


def escrever_json(caminho, dados):
    with open(caminho, "w") as f:
        json.dump(dados, f)


def comecar(params):
    """O mesmo caminho do POST /acao/claude.tarefa sem aprovação; devolve o pedido e o que foi para a fila."""
    titulo, _ = ex.preparar_claude_tarefa(cliente, params)
    p = ex.criar_pedido(cliente, "claude.tarefa", params, "chat", titulo)
    ex.mudar(p, estado="executando")
    confere(f"claude.tarefa segue sozinho ({p['id']})", ex.executar(p) is None)
    return p, ler_json(f"{tmp}/fila/{p['id']}.{p['fase']}.json")


def terminar(p, **resultado):
    """O runner tira da fila, trabalha e deixa o resultado; uma volta do acompanhar() o leva adiante."""
    os.remove(f"{tmp}/fila/{p['id']}.{p['fase']}.json")
    escrever_json(f"{tmp}/resultados/{p['id']}.{p['fase']}.json", {"id": p["id"], "fase": p["fase"], **resultado})
    uma_volta(ex)


def permissao(p, n, **dados):
    escrever_json(f"{tmp}/fila/{p['id']}-{n}.permissao", {"nonce": f"n{n}", "ferramenta": "Bash", **dados})
    ex.levar_permissoes()
    return [q for q in ex.ESTADO["pedidos"].values() if q["acao"] == "claude.permissao"][-1]


def pergunta(p, n, **dados):
    escrever_json(f"{tmp}/fila/{p['id']}-q{n}.pergunta", {"nonce": f"q{n}", "pergunta": "SQLite ou Postgres?", **dados})
    ex.levar_perguntas()


# --- validação do pedido ---
base = {"pedido": "faz um app", "conta": "pessoal"}
for nome, params, status in [
        ("sem projeto", {}, 400), ("projeto com caminho", {"projeto": "../etc"}, 400),
        ("projeto com maiúscula", {"projeto": "Lista"}, 400), ("modelo desconhecido", {"projeto": "x", "modelo": "gpt"}, 400),
        ("esforço desconhecido", {"projeto": "x", "esforco": "turbo"}, 400), ("minutos demais", {"projeto": "x", "minutos": 900}, 400),
        ("pedido curto", {"projeto": "x", "pedido": "oi"}, 400), ("conta fora do atena.conf", {"projeto": "x", "conta": "root"}, 400),
        ("publicar com somente_plano", {"projeto": "x", "publicar": True, "somente_plano": True}, 400)]:
    confere(f"{nome}: {status}", erro(ex, ex.preparar_claude_tarefa, cliente, {**base, **params})[0] == status)
status, msg = erro(ex, ex.preparar_claude_tarefa, cliente, {**base, "projeto": "x", "conta": "trabalho"})
confere("conta sem login: 409, com o comando para entrar", status == 409 and "atena-claude-conta entrar trabalho" in msg, msg)
status, msg = erro(ex, ex.preparar_claude_tarefa, cliente, {"pedido": "faz um app", "projeto": "x"})
confere("duas contas no atena.conf e nenhuma escolhida: 400 com as opções", status == 400 and "pessoal ou trabalho" in msg, msg)
status, _ = erro(ex, ex.preparar_claude_tarefa, {**cliente, "acoes": ["claude.tarefa"]}, {**base, "projeto": "x", "publicar": True})
confere("publicar sem poder pedir app.publicar: 403", status == 403)
confere("claude.tarefa pede aprovação sem o campo aprovar", ex.precisa_aprovacao({"cliente": "x", "acoes": []}, "claude.tarefa"))
confere("claude.permissao não é pedível por POST", "claude.permissao" not in ex.ACOES and "claude.permissao" in ex.INTERNAS)

# --- começar ---
avisos.clear()
p, fila = comecar({"pedido": "faz um app de lista de compras", "conta": "pessoal", "projeto": "lista-compras",
                   "modelo": "sonnet", "esforco": "high", "minutos": 120})
confere("fila com projeto, conta, modelo, esforço e minutos", fila["projeto"] == "lista-compras" and fila["conta"] == "pessoal"
        and fila["modelo"] == "sonnet" and fila["esforco"] == "high" and fila["minutos"] == 120 and "sessao" not in fila, fila)
confere("aviso de início com Cancelar e a pasta", [a["label"] for a in avisos[-1]["acoes"]] == ["Cancelar"]
        and "/srv/lab/projetos/lista-compras" in avisos[-1]["texto"])
status, msg = erro(ex, comecar, {**base, "projeto": "lista-compras"})
confere("mesmo projeto em andamento: 409", status == 409 and p["id"] in msg, msg)

# --- permissões ---
avisos.clear()
perm = permissao(p, 1, detalhe="cat /etc/hostname", motivo="ver o nome do servidor")
confere("permissão vira pedido aguardando, e o arquivo sai da fila", perm["estado"] == "aguardando"
        and not os.path.exists(f"{tmp}/fila/{p['id']}-1.permissao"))
confere("celular recebe Aprovar/Recusar com o comando e o porquê", [a["label"] for a in avisos[-1]["acoes"]] == ["Aprovar", "Recusar"]
        and "cat /etc/hostname" in avisos[-1]["texto"] and "ver o nome" in avisos[-1]["texto"])
confere("nonce não aparece para o cliente", "nonce" not in ex.publico(perm))
segredo = botao(avisos[-1], "Aprovar")
avisos.clear()
ex.tratar_resposta(f"aprovar {perm['id']} {segredo}")
resposta = f"{tmp}/fila/{p['id']}-1.resposta"
confere("aprovar devolve permitir com o nonce certo", esperar(lambda: os.path.exists(resposta))
        and ler_json(resposta) == {"nonce": "n1", "permitir": True, "motivo": ""})
confere("sem aviso extra 'Feito' depois de aprovar", esperar(lambda: perm["estado"] == "concluido")
        and not any("Feito" in a["titulo"] for a in avisos))
os.remove(resposta)
perm = permissao(p, 2, detalhe="sudo apt install x")
segredo = botao(avisos[-1], "Recusar")
avisos.clear()
ex.tratar_resposta(f"recusar {perm['id']} {segredo}")
r = ler_json(f"{tmp}/fila/{p['id']}-2.resposta")
confere("recusar: nega com motivo, sem aviso extra", r["permitir"] is False and "recusou" in r["motivo"] and avisos == [], r)
perm = permissao(p, 3, detalhe="file_path: /etc/hosts")
perm["expira"] = time.time() - 1
uma_volta(ex)
confere("sem resposta a tempo: nega", perm["estado"] == "expirado" and ler_json(f"{tmp}/fila/{p['id']}-3.resposta")["permitir"] is False)
escrever_json(f"{tmp}/fila/deadbeef-1.permissao", {"nonce": "x", "ferramenta": "Bash"})
ex.levar_permissoes()
confere("trabalho desconhecido: nega na hora", ler_json(f"{tmp}/fila/deadbeef-1.resposta")["permitir"] is False)
with open(f"{tmp}/fila/{p['id']}-4.permissao", "w") as f:
    f.write("{quebrado")
ex.levar_permissoes()
confere("permissão com defeito é descartada sem quebrar", not os.path.exists(f"{tmp}/fila/{p['id']}-4.permissao"))

# --- perguntas ---
avisos.clear()
pergunta(p, 1, opcoes=["SQLite", "Postgres"], por_que="muda o Dockerfile")
abertas = ex.acao_claude_perguntas(cliente, {})
confere("pergunta vira pendente, com o projeto e as opções", len(abertas) == 1 and abertas[0]["projeto"] == "lista-compras"
        and abertas[0]["opcoes"] == ["SQLite", "Postgres"], abertas)
confere("celular avisado na hora, com um botão por opção", [a["label"] for a in avisos[-1]["acoes"]] == ["SQLite", "Postgres"])
q = ex.ESTADO["pedidos"][abertas[0]["id"]]
ex.tratar_resposta(f"opcao1 {q['id']} {botao(avisos[-1], 'Postgres')}")
confere("botão do celular responde com o texto da opção", ler_json(f"{tmp}/fila/{p['id']}-q1.resposta")
        == {"nonce": "q1", "resposta": "Postgres", "quem": "dono (botão no celular)"})
confere("responder de novo uma pergunta encerrada: 409",
        erro(ex, ex.acao_claude_responder, cliente, {"pergunta": q["id"], "resposta": "SQLite"})[0] == 409)
pergunta(p, 2)
q2 = ex.acao_claude_perguntas(cliente, {})[0]
confere("quem inválido: 400", erro(ex, ex.acao_claude_responder, cliente, {"pergunta": q2["id"], "resposta": "x", "quem": "eu"})[0] == 400)
confere("pergunta de outro cliente: 404",
        erro(ex, ex.acao_claude_responder, {**cliente, "cliente": "painel"}, {"pergunta": q2["id"], "resposta": "x"})[0] == 404)
ex.acao_claude_responder(cliente, {"pergunta": q2["id"], "resposta": "Use SQLite", "quem": "atena"})
confere("a Atena responde no lugar do dono", ler_json(f"{tmp}/fila/{p['id']}-q2.resposta")["quem"] == "atena")
escrever_json(f"{tmp}/fila/deadbeef-q1.pergunta", {"nonce": "q9", "pergunta": "oi?"})
ex.levar_perguntas()
confere("pergunta de trabalho inexistente: responde na hora", ler_json(f"{tmp}/fila/deadbeef-q1.resposta")["quem"] == "executor")
pergunta(p, 3)
velha = ex.ESTADO["pedidos"][ex.acao_claude_perguntas(cliente, {})[0]["id"]]
velha["criado"] = time.time() - ex.ESPERA_PERGUNTA - 700
uma_volta(ex)
confere("pergunta velha (a ponte já desistiu) vence", velha["estado"] == "expirado")

# --- fim do trabalho, com permissão e pergunta pendentes ---
pendente = permissao(p, 5, detalhe="ls /opt")
pergunta(p, 4)
aberta = ex.ESTADO["pedidos"][ex.acao_claude_perguntas(cliente, {})[0]["id"]]
avisos.clear()
terminar(p, ok=True, texto="Fiz o app. Rode com npm start.", sessao=SESSAO, conta="pessoal",
         commits=["abc123 primeiro", "def456 segundo"], uso={"turnos": 12}, segundos=600)
confere("trabalho concluído com o resumo e a sessão", p["estado"] == "concluido" and p["resumo"].startswith("Fiz o app")
        and p["sessao"] == SESSAO)
confere("aviso final com a pasta e os commits", any("terminou" in a["titulo"]
        and "/srv/lab/projetos/lista-compras (2 commits)" in a["texto"] for a in avisos), avisos)
confere("pendentes encerram quando o trabalho acaba", pendente["estado"] == "expirado" and aberta["estado"] == "expirado"
        and ler_json(f"{tmp}/fila/{p['id']}-5.resposta")["permitir"] is False)

# --- consultar e cancelar ---
lista = ex.acao_claude_trabalhos(cliente, {})
confere("claude.trabalhos: contas, as com login e o trabalho", lista["contas"] == ["pessoal", "trabalho"]
        and lista["contas_com_login"] == ["pessoal"] and lista["trabalhos"][0]["id"] == p["id"]
        and lista["trabalhos"][0]["modelo"] == "sonnet", lista)
confere("cancelar trabalho terminado: 409", erro(ex, ex.acao_claude_cancelar, cliente, {"pedido": p["id"]})[0] == 409)
confere("cancelar trabalho de outro cliente: 404",
        erro(ex, ex.acao_claude_cancelar, {**cliente, "cliente": "painel"}, {"pedido": p["id"]})[0] == 404)
# o painel fala pelo dono (tem aprovacoes.decidir): vê os trabalhos dos outros clientes no alcance
dono = {"cliente": "painel", "zonas": ["core", "apps", "ai", "agents", "lab"], "acoes": ["aprovacoes.decidir"]}
item = next((t for t in ex.acao_claude_trabalhos(dono, {})["trabalhos"] if t["id"] == p["id"]), None)
confere("o painel vê o trabalho da Atena, com quem pediu, o resumo e os commits", item and item["cliente"] == "hermes"
        and item["resumo"].startswith("Fiz o app") and item["commits"] == 2, item)
confere("a Atena não ganha os campos do painel", "resumo" not in ex.acao_claude_trabalhos(cliente, {})["trabalhos"][0])
confere("painel com zonas menores que as do trabalho não vê",
        all(t["id"] != p["id"] for t in ex.acao_claude_trabalhos({**dono, "zonas": ["lab"]}, {})["trabalhos"]))
q, _ = comecar({**base, "projeto": "outro"})
ex.acao_claude_cancelar(cliente, {"pedido": q["id"]})
confere("cancelar trabalho ainda na fila: sai da fila", q["estado"] == "cancelado"
        and not os.path.exists(f"{tmp}/fila/{q['id']}.executar.json"))
c, _ = comecar({**base, "projeto": "terceiro"})
os.remove(f"{tmp}/fila/{c['id']}.executar.json")   # o runner já pegou
ex.acao_claude_cancelar(cliente, {"pedido": c["id"]})
confere("cancelar trabalho rodando deixa o sinal para o runner", os.path.exists(f"{tmp}/fila/{c['id']}.cancelar") and c.get("cancelando"))
escrever_json(f"{tmp}/resultados/{c['id']}.executar.json", {"id": c["id"], "fase": "executar", "cancelado": True,
                                                           "texto": "interrompido pelo dono", "sessao": SESSAO})
uma_volta(ex)
confere("cancelado guarda a sessão para continuar", c["estado"] == "cancelado" and c["sessao"] == SESSAO)

# --- continuar ---
r, fila = comecar({"pedido": "continue de onde parou", "continuar": c["id"], "modelo": "opus", "esforco": "low"})
confere("continuar depois de cancelar, trocando modelo e esforço", fila["sessao"] == SESSAO and fila["sessao_conta"] == "pessoal"
        and fila["conta"] == "pessoal" and fila["modelo"] == "opus" and fila["esforco"] == "low" and fila["projeto"] == "terceiro", fila)
terminar(r, ok=True, texto="Pronto.", sessao=SESSAO, conta="pessoal")
r2, fila = comecar({"pedido": "agora adiciona login", "continuar": r["id"]})
confere("continuar sem dizer nada herda conta, projeto, modelo e esforço", fila["conta"] == "pessoal"
        and fila["projeto"] == "terceiro" and fila["modelo"] == "opus" and fila["esforco"] == "low", fila)
terminar(r2, ok=False, texto="Parou: a conta pessoal bateu o limite de uso (volta às 21:00).", sessao=SESSAO, conta="pessoal")
confere("limite de uso: o trabalho falha com a sessão guardada", r2["estado"] == "falhou" and r2["sessao"] == SESSAO)
with open(f"{tmp}/contas.json", "w") as f:
    json.dump({"pessoal": True, "trabalho": True}, f)
r3, fila = comecar({"pedido": "continue na outra conta", "continuar": r2["id"], "conta": "trabalho"})
confere("continuar em outra conta, a pedido do dono: o runner leva a conversa", fila["conta"] == "trabalho"
        and fila["sessao_conta"] == "pessoal" and fila["sessao"] == SESSAO, fila)
avisos.clear()
terminar(r3, ok=True, texto="Pronto.", sessao=SESSAO, conta="pessoal", trocas=[
    {"de": "trabalho", "para": "pessoal", "motivo": "limite de uso da trabalho, que volta às 21:00"}])
confere("troca automática: guardada e avisada", r3.get("conta_final") == "pessoal"
        and any("Trocou de conta: trabalho → pessoal" in a["texto"] for a in avisos))
_, fila = comecar({"pedido": "mais um ajuste", "continuar": r3["id"]})
confere("continuar segue na conta em que terminou", fila["sessao_conta"] == "pessoal" and fila["conta"] == "pessoal", fila)
confere("continuar trabalho de outro cliente: 404", erro(ex, ex.preparar_claude_tarefa, {**cliente, "cliente": "painel"},
                                                         {"pedido": "faz algo", "continuar": r3["id"]})[0] == 404)

# --- limites da fila ---
for nome in os.listdir(f"{tmp}/fila"):
    os.remove(f"{tmp}/fila/{nome}")
ocupados = []
for i in range(ex.MAX_FILA_CLAUDE - 1):   # um ainda roda (o continuar acima)
    os.makedirs(f"{ex.PROJETOS_LAB}/fila{i}")
    ocupados.append(comecar({**base, "projeto": f"fila{i}"})[0])
confere("fila cheia: 429", erro(ex, ex.preparar_claude_tarefa, cliente, {**base, "projeto": "quarto"})[0] == 429)

# --- uma conta só: não precisa escolher ---
ex2, tmp2, _ = executor(contas="principal", prontas=("principal",))
os.makedirs(f"{ex2.PROJETOS_LAB}/x")
params = {"pedido": "faz um app", "projeto": "x"}
ex2.preparar_claude_tarefa(cliente, params)
confere("uma conta só no atena.conf: vale ela", params["conta"] == "principal")
ex2.CLAUDE = f"{tmp2}/nao-instalado"
confere("lab não instalado: 503", erro(ex2, ex2.preparar_claude_tarefa, cliente, dict(params))[0] == 503)
confere("sem lab, consultar não quebra", ex2.acao_claude_trabalhos(cliente, {})["trabalhos"] == [])

# --- pelo socket: 202 com o pedido ---
ex3, tmp3, _ = executor()
os.makedirs(f"{ex3.PROJETOS_LAB}/app")
servidor = ligar(ex3)
hermes = token(ex3, "hermes", ["claude.tarefa", "claude.trabalhos"], ["lab"], aprovar=[])
status, r = pedir(ex3, "POST", "/acao/claude.tarefa", hermes, {"params": {"pedido": "faz um app", "conta": "pessoal", "projeto": "app"}})
confere("POST claude.tarefa: 202 executando, com o pedido", status == 202 and r["estado"] == "executando"
        and os.path.exists(f"{tmp3}/fila/{r['pedido']}.executar.json"), r)
status, r = pedir(ex3, "GET", f"/pedido/{r['pedido']}", hermes)
confere("GET /pedido sem o segredo nem as zonas", status == 200 and "segredo" not in r["pedido"] and "zonas" not in r["pedido"], r)
servidor.shutdown()

fim()
