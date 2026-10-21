"""Gerenciar apps do lab com o Docker simulado (reiniciar, cancelar, apagar, restaurar, lista e publicar
depois de editar) e o script que esvazia a lixeira. A lixeira e as pastas são reais, numa pasta temporária."""
import os
import subprocess
import threading
import time

from comum import RAIZ, carregar_executor, confere, erro as erro_ex, executor, fim

ex, tmp, _ = executor(contas="pro", prontas=("pro",))
ex.log = lambda **campos: None
ex.time.sleep = lambda s: None
AVISOS, CELULAR, TOKENS = [], [], {}
ex.avisar = lambda titulo, texto, tags=(), acoes=(): AVISOS.append((titulo, texto))
ex.ntfy = lambda topico, titulo, texto, **kw: CELULAR.append((titulo, texto))
ex.carregar_tokens = lambda: TOKENS
ex.botao = lambda rotulo, decisao, p, segredo: {"label": rotulo}   # o botão de verdade lê o token do ntfy

DOCKER = {"containers": set(), "imagens": set(), "volumes": set()}
CHAMADAS, CENARIO = [], {"atende": True}


def rodar_falso(argv, tempo=30, cancelavel=None):
    CHAMADAS.append(argv)
    if argv[:1] == ["ss"]:
        return 0, ""
    if argv[:2] == ["docker", "ps"]:
        return 0, "".join(f"{c}\t/x\t{c}\trunning\tUp 1 minute\tzone-lab\n" for c in sorted(DOCKER["containers"]))
    if argv[:3] == ["docker", "volume", "ls"]:
        return 0, "".join(f"{v}\n" for v in sorted(DOCKER["volumes"]))
    if argv[:2] == ["docker", "logs"]:
        return 0, "log"
    if len(argv) == 4 and argv[0] == "docker" and argv[2] == "inspect":
        tipo = {"container": "containers", "image": "imagens", "volume": "volumes"}[argv[1]]
        return (0 if argv[3] in DOCKER[tipo] else 1), ""
    if argv[:3] == ["docker", "volume", "rm"]:
        DOCKER["volumes"].discard(argv[3])
        return 0, ""
    if argv[:3] == ["docker", "image", "rm"]:
        DOCKER["imagens"].discard(argv[3])
        return 0, ""
    if argv[:2] == ["docker", "compose"]:
        nome = argv[argv.index("-p") + 1]
        imagem = f"atena-lab/{nome[4:]}:latest"
        if "down" in argv:
            DOCKER["containers"].discard(nome)
            if "--rmi" in argv:
                DOCKER["imagens"].discard(imagem)
            return 0, ""
        if "restart" in argv:
            return 0, ""
        if "up" in argv:
            if "--no-build" in argv and imagem not in DOCKER["imagens"]:
                return 1, "no such image"
            DOCKER["containers"].add(nome)
            DOCKER["imagens"].add(imagem)
            DOCKER["volumes"].add(f"{nome}_dados")
            return 0, "Started"
    return 0, ""


def conexao_falsa(endereco, timeout=None):
    if CENARIO["atende"]:
        class S:
            def close(self):
                pass
        return S()
    raise OSError("recusada")


ex.rodar = rodar_falso
ex.socket.create_connection = conexao_falsa

if hasattr(ex, "link_tailscale"):   # etapa 4: o link do Tailscale não sai do teste
    ex.link_tailscale = lambda porta, ligar: ((f"https://teste.ts.net:{porta}" if ligar else None), None)
    ex.portas_no_tailscale = lambda: set()
    ex.tailscale_host = lambda: None
def erro(funcao, *args):
    return erro_ex(ex, funcao, *args)


def projeto(nome, publicado=False):
    os.makedirs(f"{ex.PROJETOS_LAB}/{nome}/src", exist_ok=True)
    with open(f"{ex.PROJETOS_LAB}/{nome}/Dockerfile", "w") as f:
        f.write("FROM python:3.14-slim\n")
    if publicado:
        p = {"projeto": nome}
        ex.preparar_app_publicar(hermes, p)
        ex.acao_app_publicar({"id": "00000000", "zonas": hermes["zonas"], "params": p})


def pedido(cliente, acao, params, estado, id_):
    p = {"id": id_, "cliente": cliente["cliente"], "zonas": cliente["zonas"], "acao": acao, "params": params,
         "titulo": f"{acao} {params.get('projeto')}", "estado": estado, "criado": time.time(),
         "expira": time.time() + 600, "fase": "executar"}
    ex.ESTADO["pedidos"][id_] = p
    return p


hermes = {"cliente": "hermes", "zonas": ["apps", "ai", "agents", "lab", "core"],
          "acoes": ["app.publicar", "app.apagar", "claude.tarefa"], "aprovar": ["app.publicar", "app.apagar"]}
painel = {"cliente": "painel", "zonas": ["lab"], "acoes": []}
sem_lab = {"cliente": "x", "zonas": ["apps"], "acoes": []}
TOKENS["h"] = hermes

# --- quem pede aprovação ---
confere("app.apagar pede aprovação no celular", ex.precisa_aprovacao(hermes, "app.apagar")
        and ex.ACOES["app.apagar"][2] is not None)
confere("reiniciar, cancelar, restaurar e lista rodam direto",
        all(ex.ACOES[a][2] is None for a in ("app.reiniciar", "app.cancelar", "app.restaurar", "app.lista")))
confere("token sem o campo aprovar: app.apagar também pede", ex.precisa_aprovacao(painel, "app.apagar"))
confere("fora da zona lab: 403 em todas",
        all(erro(f, sem_lab, {"projeto": "a"})[0] == 403 for f in
            (ex.preparar_app_apagar, ex.acao_app_reiniciar, ex.acao_app_cancelar, ex.acao_app_restaurar, ex.acao_app_lista)))

# --- apagar: validação e descrição ---
projeto("loja", publicado=True)
confere("publicado de verdade no Docker simulado", "lab-loja" in DOCKER["containers"] and "lab-loja_dados" in DOCKER["volumes"])
confere("sem partes: 400", erro(ex.preparar_app_apagar, hermes, {"projeto": "loja"})[0] == 400)
confere("parte desconhecida: 400", erro(ex.preparar_app_apagar, hermes, {"projeto": "loja", "partes": ["tudo"]})[0] == 400)
confere("partes não-lista: 400", erro(ex.preparar_app_apagar, hermes, {"projeto": "loja", "partes": "docker"})[0] == 400)
confere("projeto com caminho: 400", erro(ex.preparar_app_apagar, hermes, {"projeto": "../etc", "partes": ["codigo"]})[0] == 400)
confere("nada para apagar: 404", erro(ex.preparar_app_apagar, hermes, {"projeto": "nada", "partes": ["docker", "codigo"]})[0] == 404)

params = {"projeto": "loja", "partes": ["docker"]}
titulo, texto = ex.preparar_app_apagar(hermes, params)
confere("só docker: avisa que dados e código ficam", "Fica:" in texto and "lab-loja_dados" in texto
        and "loja" in titulo and "NÃO TEM VOLTA" not in texto, texto)
params = {"projeto": "loja", "partes": ["dados"]}
titulo, texto = ex.preparar_app_apagar(hermes, params)
confere("dados leva docker junto e avisa que não tem volta", params["partes"] == ["docker", "dados"]
        and "NÃO TEM VOLTA" in texto, params)

p = pedido(hermes, "claude.tarefa", {"projeto": "loja", "pedido": "x", "conta": "pro"}, "executando", "aaaa0001")
status, msg = erro(ex.preparar_app_apagar, hermes, {"projeto": "loja", "partes": ["codigo"]})
confere("Claude Code trabalhando: 409 pedindo app.cancelar", status == 409 and "app.cancelar" in msg)
status, msg = erro(ex.acao_app_apagar, {"id": "x", "zonas": hermes["zonas"], "params": {"projeto": "loja", "partes": ["codigo"]}})
confere("começou algo enquanto esperava o celular: 409 e nada apagado", status == 409
        and os.path.isdir(f"{ex.PROJETOS_LAB}/loja"))
p["estado"] = "concluido"

# --- apagar: Docker, dados e código ---
def apagar(projeto_, partes):
    params = {"projeto": projeto_, "partes": partes}
    ex.preparar_app_apagar(hermes, params)
    return ex.acao_app_apagar({"id": "bbbb0001", "zonas": hermes["zonas"], "params": params})


CHAMADAS.clear()
r = apagar("loja", ["docker"])
confere("docker: compose down --rmi all, tira container e imagem", any("--rmi" in c and "all" in c for c in CHAMADAS)
        and "lab-loja" not in DOCKER["containers"] and "atena-lab/loja:latest" not in DOCKER["imagens"], r)
confere("docker: apaga a pasta da stack, dados e código ficam", not os.path.exists(f"{ex.STACKS_LAB}/lab-loja")
        and "lab-loja_dados" in DOCKER["volumes"] and os.path.isdir(f"{ex.PROJETOS_LAB}/loja"))
lista = ex.acao_app_lista(hermes, {})
item = next(i for i in lista["projetos"] if i["projeto"] == "loja")
confere("app.lista: não publicado, com código e dados guardados", item["app"] == "não publicado" and item["codigo"]
        and item["dados_guardados"], item)

r = apagar("loja", ["dados"])
confere("dados depois (sem compose): apaga o volume", "lab-loja_dados" not in DOCKER["volumes"]
        and any("dados" in f for f in r["apagado"]), r)
r = apagar("loja", ["codigo"])
na_lixeira = os.listdir(ex.LIXEIRA_LAB)
confere("código vai para a lixeira com data no nome", not os.path.exists(f"{ex.PROJETOS_LAB}/loja")
        and len(na_lixeira) == 1 and na_lixeira[0].startswith("loja.") and os.path.isdir(f"{ex.LIXEIRA_LAB}/{na_lixeira[0]}/src"), na_lixeira)
confere("resposta diz até quando dá para restaurar", "app.restaurar" in r["apagado"][0], r)
lista = ex.acao_app_lista(hermes, {})
confere("app.lista mostra a lixeira", [i["projeto"] for i in lista["lixeira"]] == ["loja"]
        and not any(i["projeto"] == "loja" for i in lista["projetos"]), lista)

ex.ESTADO["pedidos"]["aaaa0001"]["sessao"] = "s"
status, msg = erro(ex.preparar_claude_tarefa, hermes, {"pedido": "mais coisa", "continuar": "aaaa0001"})
confere("continuar um trabalho de projeto apagado: 409 sugerindo app.restaurar", status == 409 and "app.restaurar" in msg, msg)

# --- restaurar ---
confere("restaurar o que não está na lixeira: 404", erro(ex.acao_app_restaurar, hermes, {"projeto": "nada"})[0] == 404)
os.makedirs(f"{ex.PROJETOS_LAB}/loja")
confere("restaurar por cima de uma pasta que existe: 409", erro(ex.acao_app_restaurar, hermes, {"projeto": "loja"})[0] == 409)
os.rmdir(f"{ex.PROJETOS_LAB}/loja")
r = ex.acao_app_restaurar(hermes, {"projeto": "loja"})
confere("restaurar traz de volta com o conteúdo", os.path.isdir(f"{ex.PROJETOS_LAB}/loja/src")
        and not os.listdir(ex.LIXEIRA_LAB), r)
os.symlink("/etc", f"{ex.LIXEIRA_LAB}/falso.20260101-000000")
confere("atalho na lixeira é ignorado", ex.lixeira() == [] and erro(ex.acao_app_restaurar, hermes, {"projeto": "falso"})[0] == 404)
os.unlink(f"{ex.LIXEIRA_LAB}/falso.20260101-000000")

# apagar tudo de uma vez (um toque só no celular)
projeto("blog", publicado=True)
r = apagar("blog", ["docker", "dados", "codigo"])
confere("tudo de uma vez: container, imagem, dados e código", len(r["apagado"]) == 3
        and not any("blog" in x for x in DOCKER["containers"] | DOCKER["imagens"] | DOCKER["volumes"])
        and not os.path.exists(f"{ex.PROJETOS_LAB}/blog"), r)

# --- reiniciar ---
confere("reiniciar o que não está publicado: 404", erro(ex.acao_app_reiniciar, hermes, {"projeto": "loja"})[0] == 404)
projeto("loja", publicado=True)
CHAMADAS.clear()
r = ex.acao_app_reiniciar(hermes, {"projeto": "loja"})
confere("reiniciar: compose restart e endereço", CHAMADAS[-1][-1] == "restart" and r["endereco"].endswith(":8000")
        and "obs" not in r, r)
ex.acao_app_parar(hermes, {"projeto": "loja"})
r = ex.acao_app_reiniciar(hermes, {"projeto": "loja"})
confere("reiniciar depois de app.parar: sobe com a imagem que existe", "--no-build" in CHAMADAS[-1] and "obs" in r, r)
CENARIO["atende"] = False
status, msg = erro(ex.acao_app_reiniciar, hermes, {"projeto": "loja"})
confere("reiniciou e não respondeu: 502 com a dica dos logs", status == 502 and "servico.logs" in msg)
CENARIO["atende"] = True

# --- cancelar ---
confere("nada em andamento: 404", erro(ex.acao_app_cancelar, hermes, {"projeto": "loja"})[0] == 404)
t = pedido(hermes, "claude.tarefa", {"projeto": "loja", "pedido": "x"}, "executando", "cccc0001")
open(f"{ex.CLAUDE}/fila/cccc0001.executar.json", "w").write("{}")
a = pedido(hermes, "app.apagar", {"projeto": "loja", "partes": ["docker"]}, "aguardando", "cccc0002")
a["segredo"] = "s" * 24
outro = pedido(painel, "claude.tarefa", {"projeto": "loja", "pedido": "x"}, "executando", "cccc0003")
r = ex.acao_app_cancelar(hermes, {"projeto": "loja"})
confere("cancela o trabalho que ainda estava na fila", t["estado"] == "cancelado"
        and not os.path.exists(f"{ex.CLAUDE}/fila/cccc0001.executar.json"), t["estado"])
confere("cancela o pedido que esperava o celular (o botão perde o efeito)", a["estado"] == "cancelado" and not a["segredo"])
confere("não mexe no que é de outro cliente", outro["estado"] == "executando")
confere("resposta lista o que parou", len(r["cancelado"]) == 2, r)
outro["estado"] = "concluido"

t2 = pedido(hermes, "claude.tarefa", {"projeto": "loja", "pedido": "x"}, "executando", "cccc0004")
ex.acao_app_cancelar(hermes, {"projeto": "loja"})
confere("trabalho já rodando: deixa o aviso para o runner parar", os.path.exists(f"{ex.CLAUDE}/fila/cccc0004.cancelar")
        and t2.get("cancelando"))
t2["estado"] = "cancelado"
dono = {"cliente": "painel", "zonas": ["core", "apps", "ai", "agents", "lab"], "acoes": ["aprovacoes.decidir"]}
t3 = pedido(hermes, "claude.tarefa", {"projeto": "loja", "pedido": "x"}, "executando", "cccc0006")
r = ex.acao_app_cancelar(dono, {"projeto": "loja"})
confere("o painel (fala pelo dono) cancela o trabalho da Atena no projeto",
        os.path.exists(f"{ex.CLAUDE}/fila/cccc0006.cancelar") and t3.get("cancelando") and len(r["cancelado"]) == 1, r)
t3["estado"] = "cancelado"

# cancelar uma publicação no meio da construção
class Processo:
    parado = False

    def terminate(self):
        Processo.parado = True


pub = pedido(hermes, "app.publicar", {"projeto": "loja", "porta": 8000}, "executando", "cccc0005")
ex.PROCESSOS["loja"] = Processo()
ex.acao_app_cancelar(hermes, {"projeto": "loja"})
confere("publicação: interrompe o docker compose", Processo.parado and "loja" in ex.CANCELAR)
ex.PROCESSOS.clear()
original = ex.rodar


def rodar_cancelado(argv, tempo=30, cancelavel=None):
    if cancelavel:
        ex.CANCELAR.add(cancelavel)   # o dono cancelou durante a construção
        return -15, "interrompido"
    return original(argv, tempo)


ex.rodar = rodar_cancelado
CHAMADAS.clear()
try:
    ex.executar(pub)
except ex.Erro:
    pass
ex.rodar = original
confere("publicação cancelada: estado cancelado, sem derrubar o que estava no ar",
        pub["estado"] == "cancelado" and "lab-loja" in DOCKER["containers"]
        and not any("down" in c for c in CHAMADAS), pub)
confere("depois do cancelamento, a marca some (a próxima publicação não é cancelada)", "loja" not in ex.CANCELAR)

# rodar(cancelavel=...) de verdade: interrompe um processo real
real = carregar_executor()
inicio = time.monotonic()
threading.Timer(0.3, lambda: real.PROCESSOS["teste"].terminate()).start()
codigo, _ = real.rodar(["sleep", "30"], 60, cancelavel="teste")
confere("rodar cancelável: terminate interrompe o processo de verdade", codigo != 0 and time.monotonic() - inicio < 5
        and "teste" not in real.PROCESSOS, codigo)
try:
    real.rodar(["sleep", "5"], 0.2, cancelavel="teste")
    confere("rodar cancelável: estoura o tempo", False)
except subprocess.TimeoutExpired:
    confere("rodar cancelável: estoura o tempo e mata o processo", "teste" not in real.PROCESSOS)

# --- editar e publicar de novo (claude.tarefa com publicar) ---
ex.contas_prontas = lambda: {"pro"}
base = {"pedido": "muda a cor", "conta": "pro", "projeto": "loja"}
confere("publicar com somente_plano: 400", erro(ex.preparar_claude_tarefa, hermes, {**base, "publicar": True, "somente_plano": True})[0] == 400)
confere("publicar sem poder app.publicar: 403", erro(ex.preparar_claude_tarefa, {**hermes, "acoes": ["claude.tarefa"]},
                                                       {**base, "publicar": True})[0] == 403)
params = {**base, "publicar": True}
titulo, _ = ex.preparar_claude_tarefa(hermes, params)
confere("título avisa que vai publicar", "publicar" in titulo, titulo)

trabalho = pedido(hermes, "claude.tarefa", params, "executando", "dddd0001")
FILA = []
ex.enfileirar = lambda p, fase, **extra: FILA.append(extra)
ex.acao_claude_tarefa(trabalho)
confere("o Claude Code fica sabendo que vai ser publicado", "publica o app de novo" in FILA[-1]["pedido"]
        and params["pedido"] == "muda a cor")

CELULAR.clear()
ex.concluir_claude(trabalho, {"ok": True, "texto": "mudei a cor", "mudancas": ["app.py"]})
pub2 = ex.ESTADO["pedidos"].get(trabalho.get("publicacao"))
confere("terminou bem: pede a publicação no celular (token exige)", pub2 and pub2["acao"] == "app.publicar"
        and pub2["estado"] == "aguardando" and pub2["params"]["porta"] == 8000
        and any("Versão nova" in t for _, t in CELULAR), pub2)
pub2["estado"] = "recusado"

trabalho2 = pedido(hermes, "claude.tarefa", {**params}, "executando", "dddd0002")
ex.concluir_claude(trabalho2, {"ok": False, "texto": "quebrou"})
confere("terminou com erro: não publica", "publicacao" not in trabalho2)

direto = {**hermes, "cliente": "painel2", "aprovar": []}
TOKENS["p"] = direto
FEITO = []
ex.executar_aprovado = lambda p: FEITO.append(p["id"])
trabalho3 = pedido(direto, "claude.tarefa", {**params}, "executando", "dddd0003")
ex.concluir_claude(trabalho3, {"ok": True, "texto": "ok"})
time.sleep(0)
confere("token sem aprovação: publica direto", trabalho3.get("publicacao") and
        ex.ESTADO["pedidos"][trabalho3["publicacao"]]["estado"] == "executando")

del TOKENS["p"]
AVISOS.clear()
trabalho4 = pedido(direto, "claude.tarefa", {**params}, "executando", "dddd0004")
ex.concluir_claude(trabalho4, {"ok": True, "texto": "ok"})
confere("token revogado no meio: não publica e avisa", "publicacao" not in trabalho4
        and any("Não publiquei" in t for t, _ in AVISOS))

# --- esvaziar a lixeira (script do timer, como root, com a pasta trocada) ---
SCRIPT = os.path.join(RAIZ, "host", "sbin", "atena-lab-lixeira")
if os.path.exists(SCRIPT):
    lix = f"{tmp}/lixeira-timer"
    fora = f"{tmp}/fora"
    os.makedirs(fora)
    with open(f"{fora}/importante", "w") as f:
        f.write("x")
    velho = time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time() - 40 * 86400))
    novo = time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time() - 5 * 86400))
    for nome in (f"velho.{velho}", f"novo.{novo}", "sem-data"):
        os.makedirs(f"{lix}/{nome}/sub")
    os.symlink(fora, f"{lix}/atalho.{velho}")
    r = subprocess.run(["bash", SCRIPT], env={**os.environ, "ATENA_LIXEIRA": lix}, capture_output=True, text=True)
    sobrou = sorted(os.listdir(lix))
    confere("lixeira: apaga só o que passou de 30 dias", r.returncode == 0
            and sobrou == sorted([f"novo.{novo}", "sem-data", f"atalho.{velho}"]), (r.stderr, sobrou))
    confere("lixeira: atalho não é seguido", os.path.exists(f"{fora}/importante"))
else:
    confere("script da lixeira existe ao lado do executor", False, SCRIPT)

fim()
