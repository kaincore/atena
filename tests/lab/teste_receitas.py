"""As receitas de estilo no executor, sem root, sem Docker e sem runner: o endereço (só internet), o nome,
a coleta (um docker run de mentira), o trabalho do Claude Code que escreve a receita, a receita guardada
e conferida (sem seguir links), o índice e a busca, refazer, continuar, apagar, refazer o índice e as
receitas levadas a um projeto pelo claude.tarefa."""
import json
import os
import sqlite3

from comum import RAIZ, SESSAO, confere, erro, esperar, executor, fim, uma_volta

ex, tmp, avisos = executor(conf="ATENA_CLAUDE_SKILLS=sim\n")
ex.RECEITAS, ex.INDICE_RECEITAS = f"{tmp}/receitas", f"{tmp}/receitas.db"
ex.SKILLS_CLAUDE = f"{tmp}/skills.json"
with open(ex.SKILLS_CLAUDE, "w") as f:
    json.dump({"frontend-design": "/frontend-design:frontend-design", "receita": "/receita"}, f)
cliente = {"cliente": "hermes", "zonas": ["apps", "ai", "agents", "lab", "core"], "acoes": ["claude.tarefa"], "aprovar": []}
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 2000
RECEITA = "# Receita\n\n" + "Fundo quase preto, texto cinza claro, Inter Variable com tracking negativo. " * 10

# --- o endereço -------------------------------------------------------------------------------------------
enderecos = {"exemplo.com": {"93.184.215.14"}, "linear.app": {"76.76.21.21"}, "casa.exemplo": {"192.168.0.20"},
             "dupla.exemplo": {"93.184.215.14", "10.10.40.1"}, "local.exemplo": {"::1"}}


def resolver(host, porta):
    if host not in enderecos:
        raise OSError("nome desconhecido")
    return enderecos[host]


ex.resolver_nome = resolver
confere("sem esquema vira https e ganha a barra", ex.endereco_publico("linear.app") == "https://linear.app/")
confere("o fragmento sai, a busca fica", ex.endereco_publico("https://Exemplo.com/a?b=1#c") == "https://exemplo.com/a?b=1")
for url, motivo in (("ftp://exemplo.com", "esquema"), ("https://eu:senha@exemplo.com", "usuário e senha"),
                    ("https://casa.exemplo", "rede de casa"), ("https://dupla.exemplo", "um dos IPs é privado"),
                    ("https://local.exemplo", "o próprio servidor"), ("https://nao.existe", "nome que não resolve"),
                    ("x", "curto demais"), (None, "sem url")):
    confere(f"endereço recusado: {motivo}", erro(ex, ex.endereco_publico, url)[0] == 400)
confere("o IP de casa no erro (o dono entende o porquê)", "192.168.0.20" in erro(ex, ex.endereco_publico, "casa.exemplo")[1])
confere("nome do site: linear.app → linear-app", ex.nome_do_site("https://linear.app/") == "linear-app")
confere("nome do site: sem www", ex.nome_do_site("https://www.exemplo.com.br/x") == "exemplo-com-br")

# --- o docker de mentira: a imagem existe e o docker run grava uma coleta --------------------------------
docker = []


def rodar_falso(argv, tempo=30, cancelavel=None):
    docker.append(argv)
    if argv[:3] == ["docker", "image", "inspect"]:
        return (0 if COLETOR_EXISTE["sim"] else 1), ""
    if argv[:2] == ["docker", "run"]:
        destino = argv[argv.index("-v") + 1].split(":")[0]
        if COLETA["falha"]:
            return 1, "a coleta falhou: page.goto: Timeout 45000ms exceeded."
        os.makedirs(f"{destino}/prints")
        for nome in ("pc.jpg", "celular.jpg"):
            with open(f"{destino}/prints/{nome}", "wb") as f:
                f.write(JPEG)
        with open(f"{destino}/prints/tablet.jpg", "wb") as f:
            f.write(b"<svg>nao sou jpeg</svg>")
        with open(f"{destino}/coleta.json", "w") as f:
            json.dump({"titulo": "Linear – The system", "status": 200, "url_final": argv[-2], "avisos": [],
                       "arquivos": {"prints/pc.jpg": 2004, "prints/celular.jpg": 2004, "estilo.json": 9000}}, f)
        if cancelavel in CANCELAR_NO_MEIO:
            ex.CANCELAR.add(cancelavel)
        return 0, "coleta pronta: 3 arquivos (Linear)"
    return 0, ""


COLETOR_EXISTE, COLETA, CANCELAR_NO_MEIO = {"sim": True}, {"falha": False}, set()
ex.rodar = rodar_falso


def estudar(params, esperar_fim=True):
    """O caminho do POST /acao/receita.estudar sem aprovação: devolve o pedido (e espera a thread)."""
    titulo, _ = ex.preparar_receita_estudar(cliente, params)
    p = ex.criar_pedido(cliente, "receita.estudar", params, "chat", titulo)
    ex.mudar(p, estado="executando")
    confere(f"receita.estudar segue sozinha ({p['id']})", ex.executar(p) is None)
    if esperar_fim:
        esperar(lambda: p["estado"] in ex.TERMINADOS, 5)
    return p


def trabalho_de(p):
    return ex.ESTADO["pedidos"][p["resultado"]["trabalho"]]


def escrever(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w") as f:
        f.write(texto)


def terminar(t, ok=True, texto="Receita escrita."):
    """O runner tira da fila, trabalha e deixa o resultado; uma volta do acompanhar() leva adiante."""
    os.remove(f"{tmp}/fila/{t['id']}.executar.json")
    with open(f"{tmp}/resultados/{t['id']}.executar.json", "w") as f:
        json.dump({"id": t["id"], "fase": "executar", "ok": ok, "texto": texto, "sessao": SESSAO}, f)
    uma_volta(ex)


# --- preparar ---------------------------------------------------------------------------------------------
COLETOR_EXISTE["sim"] = False
confere("sem a imagem do coletor: 503", erro(ex, ex.preparar_receita_estudar, cliente, {"url": "linear.app"})[0] == 503)
COLETOR_EXISTE["sim"] = True
for params, motivo in (({"url": "linear.app", "nome": "Linear"}, "nome com maiúscula"),
                       ({"url": "linear.app", "nome": "a" * 40}, "nome comprido"),
                       ({"url": "linear.app", "foco": "x" * 600}, "foco comprido"),
                       ({"url": "linear.app", "modelo": "gpt"}, "modelo que não existe")):
    confere(f"receita.estudar recusa: {motivo}", erro(ex, ex.preparar_receita_estudar, cliente, params)[0] == 400)
confere("conta sem login: 409 (conferida antes da coleta)",
        erro(ex, ex.preparar_receita_estudar, cliente, {"url": "linear.app", "conta": "trabalho"})[0] == 409)
with open(ex.SKILLS_CLAUDE, "w") as f:
    json.dump({"frontend-design": "/frontend-design:frontend-design"}, f)
confere("sem a skill receita no catálogo: 503", erro(ex, ex.preparar_receita_estudar, cliente, {"url": "linear.app"})[0] == 503)
with open(ex.SKILLS_CLAUDE, "w") as f:
    json.dump({"frontend-design": "/frontend-design:frontend-design", "receita": "/receita"}, f)

# --- estudar: coleta, trabalho, receita guardada ----------------------------------------------------------
p = estudar({"url": "linear.app", "foco": "o menu do topo"})
confere("a coleta terminou e o trabalho entrou na fila", p["estado"] == "concluido", p.get("erro"))
pasta = f"{ex.PROJETOS_LAB}/receita-linear-app"
confere("a coleta ficou no projeto do estudo", os.path.isfile(f"{pasta}/coleta/coleta.json"))
run = next(a for a in docker if a[:2] == ["docker", "run"])
confere("o coletor roda na rede lab-coletor, sem capacidades e só leitura",
        run[run.index("--network") + 1] == "lab-coletor" and "--read-only" in run and "ALL" in run
        and "no-new-privileges:true" in run and run[-1] == "/saida" and run[-2] == "https://linear.app/")
confere("o container da coleta tem nome fixo (sobra de antes sai primeiro)",
        ["docker", "rm", "-f", "coletor-linear-app"] in docker)
t = trabalho_de(p)
fila = json.load(open(f"{tmp}/fila/{t['id']}.executar.json"))
confere("o trabalho usa a skill receita no projeto receita-linear-app",
        fila["skill"] == "receita" and fila["projeto"] == "receita-linear-app" and fila["minutos"] == ex.MINUTOS_RECEITA)
confere("o pedido leva o site, a coleta e o foco",
        "https://linear.app/" in fila["pedido"] and "coleta/" in fila["pedido"] and "o menu do topo" in fila["pedido"])
confere("o trabalho é marcado como o da receita", t["params"].get("receita") == "linear-app")
lista = ex.acao_receita_lista(cliente, {})["receitas"]
confere("a lista mostra a receita estudando, com o título da coleta",
        lista and lista[0]["estado"] == "estudando" and lista[0]["titulo"] == "Linear – The system"
        and lista[0]["origem"] == "https://linear.app/")
confere("estudar de novo enquanto estuda: 409 (o projeto está ocupado)",
        erro(ex, ex.preparar_receita_estudar, cliente, {"url": "linear.app"})[0] == 409)

escrever(f"{pasta}/RECEITA.md", RECEITA)
escrever(f"{pasta}/DESIGN.md", "---\ncolors:\n  fundo: '#08090a'\n---\n# Design\n")
escrever(f"{pasta}/receita.json", json.dumps({
    "titulo": "Linear: escuro e preciso", "resumo": "Escuro, denso, letras pequenas e cinzas em camadas.",
    "tags": ["escuro", "minimalista", "produto", 3], "paleta": [{"nome": "fundo", "valor": "#08090a", "uso": "página"},
                                                                 {"nome": "sem valor"}, "solto"],
    "fontes": [{"familia": "Inter Variable", "uso": "tudo", "licenca": "OFL"}], "extra": "x" * 100}))
avisos.clear()
terminar(t)
r = f"{ex.RECEITAS}/linear-app"
confere("a receita foi guardada", all(os.path.isfile(f"{r}/{a}") for a in ("RECEITA.md", "DESIGN.md", "receita.json")))
confere("os prints JPEG vieram; o que não é JPEG não",
        sorted(os.listdir(f"{r}/prints")) == ["celular.jpg", "pc.jpg"])
dados = json.load(open(f"{r}/receita.json"))
confere("o receita.json guardado só tem o que vale",
        dados["tags"] == ["escuro", "minimalista", "produto"] and len(dados["paleta"]) == 1 and "extra" not in dados
        and dados["origem"] == "https://linear.app/" and dados["trabalho"] == t["id"])
confere("o celular avisa a receita pronta (e não o fim genérico do trabalho)",
        len(avisos) == 1 and avisos[0]["titulo"] == "Receita pronta: Linear: escuro e preciso", avisos)
lista = ex.acao_receita_lista(cliente, {})["receitas"]
confere("a lista mostra a receita pronta, com paleta e prints",
        lista[0]["estado"] == "pronta" and lista[0]["paleta"][0]["valor"] == "#08090a"
        and lista[0]["prints"] == ["pc.jpg", "celular.jpg"] and not lista[0]["refazendo"])
ver = ex.acao_receita_ver(cliente, {"nome": "linear-app"})
confere("receita.ver traz o texto e o DESIGN.md", ver["texto"].startswith("# Receita") and "#08090a" in ver["design"])
confere("receita.print devolve o JPEG em base64",
        ex.acao_receita_print(cliente, {"nome": "linear-app", "print": "pc.jpg"})["base64"].startswith("/9j/"))
confere("receita.print recusa outro arquivo",
        erro(ex, ex.acao_receita_print, cliente, {"nome": "linear-app", "print": "../receita.json"})[0] == 400)
achou = ex.acao_receita_procurar(cliente, {"texto": "Inter tracking"})["receitas"]
confere("a busca acha pelo texto da receita, com o trecho", achou and achou[0]["nome"] == "linear-app" and "[" in achou[0]["trecho"])
confere("a busca acha sem acento e pelo começo da palavra",
        ex.acao_receita_procurar(cliente, {"texto": "minimal"})["receitas"][0]["nome"] == "linear-app")
confere("a busca sem resultado é lista vazia", ex.acao_receita_procurar(cliente, {"texto": "serifa barroca"})["receitas"] == [])
confere("estudar o mesmo nome de novo: 409 (refazer=true para refazer)",
        erro(ex, ex.preparar_receita_estudar, cliente, {"url": "linear.app"})[0] == 409)

# --- claude.tarefa com receitas ---------------------------------------------------------------------------
os.makedirs(f"{ex.PROJETOS_LAB}/loja")
params = {"pedido": "Faça a loja", "projeto": "loja", "conta": "pessoal", "receitas": ["linear-app", "linear-app"],
          "receita": "linear-app"}
titulo, _ = ex.preparar_claude_tarefa(cliente, params)
confere("claude.tarefa leva as receitas (sem repetir) e o título diz o estilo",
        params["receitas"] == ["linear-app"] and "no estilo de linear-app" in titulo)
confere("o cliente não marca um trabalho como o de uma receita", "receita" not in params)
q = ex.criar_pedido(cliente, "claude.tarefa", params, "chat", titulo)
ex.mudar(q, estado="executando")
ex.executar(q)
confere("as receitas vão para o runner na fila", json.load(open(f"{tmp}/fila/{q['id']}.executar.json"))["receitas"] == ["linear-app"])
for receitas, status, motivo in ((["nao-existe"], 404, "receita que não existe"), ([], 400, "lista vazia"),
                                 (["linear-app"] * 4, 400, "mais de 3"), ("linear-app", 400, "texto em vez de lista"),
                                 (["../x"], 400, "nome inválido")):
    confere(f"claude.tarefa recusa receitas: {motivo}",
            erro(ex, ex.preparar_claude_tarefa, cliente, {"pedido": "x" * 5, "projeto": "outro", "receitas": receitas})[0] == status)
terminar(q)

# --- refazer: a receita pronta vale até a nova; uma tentativa que falha não a perde -----------------------
p2 = estudar({"url": "linear.app", "refazer": True})
t2 = trabalho_de(p2)
lista = ex.acao_receita_lista(cliente, {})["receitas"]
confere("refazendo: continua pronta e marcada", lista[0]["estado"] == "pronta" and lista[0]["refazendo"])
confere("refazendo: dá para usar num projeto enquanto isso", ex.receitas_prontas(["linear-app"]) == ["linear-app"])
confere("a coleta nova trocou a velha", os.path.isfile(f"{pasta}/coleta/coleta.json")
        and not [n for n in os.listdir(pasta) if n.startswith(".coleta-")])
terminar(t2, ok=False, texto="parou: limite de uso")
linha = ex.acao_receita_lista(cliente, {})["receitas"][0]
confere("refazer que falhou: a receita segue pronta, com o erro anotado",
        linha["estado"] == "pronta" and "limite de uso" in (linha["erro"] or ""))

# --- continuar o estudo: a marca vai junto e a receita é guardada no fim ---------------------------------
params = {"pedido": "termine a receita", "continuar": t2["id"]}
titulo, _ = ex.preparar_claude_tarefa(cliente, params)
confere("continuar o trabalho de uma receita leva a marca", params.get("receita") == "linear-app")
t3 = ex.criar_pedido(cliente, "claude.tarefa", params, "chat", titulo)
ex.mudar(t3, estado="executando")
ex.executar(t3)
escrever(f"{pasta}/receita.json", json.dumps({"titulo": "Linear (de novo)", "resumo": "Refeita."}))
terminar(t3)
confere("o continuar guardou a receita nova", json.load(open(f"{r}/receita.json"))["titulo"] == "Linear (de novo)")
confere("a versão anterior saiu sem deixar sobra", not [n for n in os.listdir(ex.RECEITAS) if n.startswith(".")])

# --- uma receita com defeito não entra (e um link não faz o executor ler outra coisa) ---------------------
enderecos["site.exemplo"] = {"93.184.215.15"}
p4 = estudar({"url": "https://site.exemplo/", "nome": "site"})
t4 = trabalho_de(p4)
segredo = f"{tmp}/segredo.txt"
escrever(segredo, "CHAVE=123\n" * 100)
os.symlink(segredo, f"{ex.PROJETOS_LAB}/receita-site/RECEITA.md")
escrever(f"{ex.PROJETOS_LAB}/receita-site/receita.json", "{}")
avisos.clear()
terminar(t4)
linha = next(x for x in ex.acao_receita_lista(cliente, {})["receitas"] if x["nome"] == "site")
confere("RECEITA.md que é um link: a receita falha e nada é copiado",
        linha["estado"] == "falhou" and "não é um arquivo comum" in linha["erro"] and not os.path.exists(f"{ex.RECEITAS}/site"))
confere("o celular avisa o defeito e como corrigir", avisos and "continue o trabalho" in avisos[-1]["texto"].lower())
confere("receita que falhou não vai a um projeto", erro(ex, ex.receitas_prontas, ["site"])[0] == 409)

# --- a coleta que falha, e a que o dono cancela ----------------------------------------------------------
enderecos["fora.exemplo"] = {"93.184.215.16"}
COLETA["falha"] = True
avisos.clear()
p5 = estudar({"url": "fora.exemplo"})
confere("coleta que falha: o pedido falha com a última linha do coletor",
        p5["estado"] == "falhou" and "Timeout" in p5["erro"] and avisos and "não começou" in avisos[-1]["titulo"])
confere("coleta que falha: nenhum trabalho do Claude Code", not any(
    q["params"].get("receita") == "fora-exemplo" for q in ex.ESTADO["pedidos"].values() if q["acao"] == "claude.tarefa"))
COLETA["falha"] = False
CANCELAR_NO_MEIO.add("receita-fora-exemplo")
p6 = estudar({"url": "fora.exemplo"})
confere("app.cancelar no meio da coleta: cancelado, e o container sai", p6["estado"] == "cancelado"
        and docker[-1] == ["docker", "rm", "-f", "coletor-fora-exemplo"])
CANCELAR_NO_MEIO.clear()

# --- o executor reiniciou no meio da coleta ---------------------------------------------------------------
falso = ex.criar_pedido(cliente, "receita.estudar", {"url": "https://fora.exemplo/", "nome": "x"}, "chat", "x")
ex.mudar(falso, estado="executando")
ex.pedidos_interrompidos()
confere("coleta interrompida pelo reinício: falhou, com o que fazer", falso["estado"] == "falhou" and "de novo" in falso["erro"])

# --- apagar e refazer o índice ----------------------------------------------------------------------------
titulo, texto = ex.preparar_receita_apagar(cliente, {"nome": "linear-app"})
confere("apagar explica o que fica", "fica" in texto)
confere("apagar é destrutivo: pede o celular", ex.precisa_aprovacao({"aprovar": ["app.publicar"]}, "receita.apagar"))
os.remove(ex.INDICE_RECEITAS)
ex.indexar()
confere("índice perdido: a receita pronta volta das pastas",
        [x["nome"] for x in ex.acao_receita_lista(cliente, {})["receitas"]] == ["linear-app"]
        and ex.acao_receita_procurar(cliente, {"texto": "Inter"})["receitas"])
pa = ex.criar_pedido(cliente, "receita.apagar", {"nome": "linear-app"}, "chat", titulo)
ex.mudar(pa, estado="executando")
ex.executar(pa)
confere("apagada: some da pasta, do índice e da busca", not os.path.exists(r)
        and ex.acao_receita_lista(cliente, {})["receitas"] == []
        and ex.acao_receita_procurar(cliente, {"texto": "Inter"})["receitas"] == [])
confere("apagada: o estudo no lab fica", os.path.isfile(f"{pasta}/RECEITA.md"))
confere("receita.ver de quem não existe: 404", erro(ex, ex.acao_receita_ver, cliente, {"nome": "linear-app"})[0] == 404)
os.makedirs(f"{ex.RECEITAS}/quebrada")
ex.indexar()
confere("pasta sem receita.json não entra no índice", ex.acao_receita_lista(cliente, {})["receitas"] == [])
con = sqlite3.connect(ex.INDICE_RECEITAS)
confere("o índice tem a busca por texto (FTS5)", con.execute("SELECT 1 FROM sqlite_master WHERE name = 'busca'").fetchone())
con.close()

# --- um programa (o que o dono mandou pelo Telegram), com prints dele -----------------------------------
import zipfile  # noqa: E402

hermes, fora = f"{tmp}/hermes", f"{tmp}/fora"
for d in (f"{hermes}/cache/documents", fora):
    os.makedirs(d)
with open(ex.CONF, "a") as f:
    f.write(f"ATENA_PASTAS_ENTREGA={hermes}\n")
ex.ESPACO_HERMES = ("/opt/data", hermes)
apk = f"{hermes}/cache/documents/Notas-2.1.apk"
with zipfile.ZipFile(apk, "w") as z:
    z.writestr("AndroidManifest.xml", "manifesto")
    z.writestr("res/values/colors.xml", "<resources/>")
PNGB = b"\x89PNG\r\n\x1a\n" + b"0" * 500
for nome, dados in (("tela1.png", PNGB), ("tela2.jpg", JPEG), ("nota.txt", b"texto")):
    with open(f"{hermes}/cache/documents/{nome}", "wb") as f:
        f.write(dados)
with open(f"{fora}/app.apk", "wb") as f:
    f.write(b"PK\x03\x04")
with open(f"{hermes}/cache/documents/banco.bin", "wb") as f:
    f.write(b"SQLite format 3\x00" + b"0" * 100)
for params, status, motivo in (({}, 400, "sem url nem arquivo"), ({"url": "linear.app", "arquivo": apk}, 400, "os dois"),
                               ({"arquivo": f"{fora}/app.apk"}, 403, "fora das pastas de entrega"),
                               ({"arquivo": "/opt/data/cache/documents/banco.bin"}, 403, "um banco de dados"),
                               ({"arquivo": "/opt/data/cache/documents/nao.apk"}, 404, "que não existe"),
                               ({"arquivo": apk, "imagens": ["/opt/data/cache/documents/nota.txt"]}, 400, "imagem que não é imagem"),
                               ({"arquivo": apk, "imagens": [f"{hermes}/cache/documents/tela1.png"] * 7}, 400, "imagens demais")):
    confere(f"receita de programa recusa: {motivo}", erro(ex, ex.preparar_receita_estudar, cliente, params)[0] == status,
            erro(ex, ex.preparar_receita_estudar, cliente, params))
ex.LIMITE_ALVO = 10
confere("programa grande demais: 413", erro(ex, ex.preparar_receita_estudar, cliente, {"arquivo": apk})[0] == 413)
ex.LIMITE_ALVO = 1024 ** 3
COLETOR_EXISTE["sim"] = False   # o programa não precisa do coletor
docker.clear()
p7 = estudar({"arquivo": "/opt/data/cache/documents/Notas-2.1.apk", "foco": "o tema escuro",
              "imagens": ["/opt/data/cache/documents/tela1.png", f"{hermes}/cache/documents/tela2.jpg"]})
COLETOR_EXISTE["sim"] = True
confere("receita de programa: o nome vem do arquivo e o coletor não roda",
        p7["estado"] == "concluido" and p7["params"]["nome"] == "notas-2-1" and not [a for a in docker if a[:2] == ["docker", "run"]],
        p7.get("erro"))
estudo = f"{ex.PROJETOS_LAB}/receita-notas-2-1"
alvo = json.load(open(f"{estudo}/alvo/alvo.json"))
confere("o programa foi para alvo/, com o tipo e o SHA-256", os.path.isfile(f"{estudo}/alvo/Notas-2.1.apk")
        and alvo["tipo"] == "APK (Android)" and len(alvo["sha256"]) == 64 and alvo["de"] == apk, alvo)
confere("os prints do dono foram para telas/", sorted(os.listdir(f"{estudo}/telas")) == ["tela-1.png", "tela-2.jpg"])
t7 = trabalho_de(p7)
pedido = json.load(open(f"{tmp}/fila/{t7['id']}.executar.json"))["pedido"]
confere("o pedido diz o programa, o tipo, não rodar, os prints e o foco",
        "Notas-2.1.apk" in pedido and "APK (Android)" in pedido and "Não rode" in pedido and "telas/" in pedido
        and "o tema escuro" in pedido, pedido)
escrever(f"{estudo}/RECEITA.md", RECEITA)
escrever(f"{estudo}/receita.json", json.dumps({"titulo": "Notas: tema escuro", "resumo": "Material, escuro."}))
terminar(t7)
linha = next(x for x in ex.acao_receita_lista(cliente, {})["receitas"] if x["nome"] == "notas-2-1")
confere("receita de programa pronta, com os prints do dono e a origem no estudo",
        linha["estado"] == "pronta" and linha["de"] == "programa" and linha["prints"] == ["tela-1.png", "tela-2.jpg"]
        and linha["origem"] == f"{estudo}/alvo/Notas-2.1.apk", linha)
confere("receita.print de um PNG do dono", ex.acao_receita_print(cliente, {"nome": "notas-2-1", "print": "tela-1.png"})["tipo"] == "image/png")
p8 = estudar({"arquivo": linha["origem"], "nome": "notas-2-1", "refazer": True})
confere("refazer a partir da cópia no estudo (o alvo velho é a origem)", p8["estado"] == "concluido"
        and os.path.isfile(f"{estudo}/alvo/Notas-2.1.apk") and not [n for n in os.listdir(estudo) if n.startswith(".alvo")], p8.get("erro"))
confere("refazer sem imagens não apaga as telas de antes", os.path.isdir(f"{estudo}/telas"))
terminar(trabalho_de(p8))

# o tipo do programa, pelos primeiros bytes
amostras = {"elf": (b"\x7fELF\x02\x01\x01" + b"\0" * 60, "ELF (Linux)"),
            "appimage": (b"\x7fELF\x02\x01\x01\0AI\x02" + b"\0" * 60, "AppImage (Linux)"),
            "exe": (b"MZ" + b"\0" * 60, "PE (Windows: .exe ou .dll)"),
            "asar": (b'\x04\x00\x00\x00\x10\x00\x00\x00{"files":{}}', "ASAR (Electron)"),
            "nada": (b"oi", "desconhecido")}
for nome, (dados, esperado) in amostras.items():
    with open(f"{tmp}/{nome}", "wb") as f:
        f.write(dados)
    confere(f"tipo do programa: {esperado}", ex.tipo_do_arquivo(f"{tmp}/{nome}") == esperado, ex.tipo_do_arquivo(f"{tmp}/{nome}"))
with zipfile.ZipFile(f"{tmp}/app.zip", "w") as z:
    z.writestr("App/resources/app.asar", "x")
confere("tipo do programa: ZIP com Electron", ex.tipo_do_arquivo(f"{tmp}/app.zip") == "ZIP com um app Electron (.asar)")
confere("nome do arquivo: sem a extensão", ex.nome_do_arquivo("/x/Linear-1.2.AppImage") == "linear-1-2")

# --- a imagem do coletor: a mesma no executor, no instalador e no Dockerfile do repositório ---------------
with open(os.path.join(RAIZ, "install", "88-lab.sh")) as f:
    confere("o instalador constrói a mesma imagem que o executor roda", f"COLETOR={ex.COLETOR} " in f.read())
confere("o Dockerfile do coletor está no repositório", os.path.isfile(os.path.join(RAIZ, "host", "lab", "coletor", "Dockerfile")))

fim()
