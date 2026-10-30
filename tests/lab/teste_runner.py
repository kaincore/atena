"""O atena-claude-runner com um Claude Code de mentira: trabalho normal, plano, recusas, cancelar,
contas do atena.conf, limite de uso (com e sem troca automática), continuar em outra conta, as
travas de git, o fechamento depois do resumo final, os trabalhos em paralelo, as skills e o runner que
morre no meio de um trabalho."""
import json
import os
import signal
import subprocess
import sys
import threading
import time

from comum import RAIZ, SESSAO, confere, esperar, executor, fim, runner, uma_volta

rn, tmp = runner()
base, projetos = rn.BASE, rn.PROJETOS

# Claude Code de mentira: anota como foi chamado e responde em stream-json. O pedido escolhe o caso:
# COMMIT faz um commit (antes de tudo); DEMORA espera 60 s; PRESO manda o resumo e fica aberto (com um filho);
# PARALELO anota início e fim. Uma conta listada em <tmp>/limitadas bate o limite de uso.
FALSO = f"{tmp}/claude-falso"
with open(FALSO, "w") as f:
    f.write(f"""#!/usr/bin/env python3
import json, os, subprocess, sys, time
T, SESSAO = {tmp!r}, {SESSAO!r}
conta = os.path.basename(os.environ["CLAUDE_CONFIG_DIR"])
pedido = sys.argv[-1]
with open(T + "/chamadas.jsonl", "a") as f:
    f.write(json.dumps({{"conta": conta, "argv": sys.argv[1:], "cwd": os.getcwd(), "env": dict(os.environ),
                        "pid": os.getpid()}}) + "\\n")
proj = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "projects", "-proj")
os.makedirs(proj, exist_ok=True)
sessao_aqui = os.path.exists(os.path.join(proj, SESSAO + ".jsonl"))
print(json.dumps({{"type": "system", "subtype": "init", "session_id": SESSAO}}), flush=True)
if "COMMIT" in pedido:
    subprocess.run(["git", "init", "-q"], check=True)
    open("app.py", "w").write("print('oi')\\n")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-q", "-m", "primeiro commit"], check=True)
if "DEMORA" in pedido:
    time.sleep(60)
if "PARALELO" in pedido:
    open(T + "/eventos.log", "a").write(f"inicio {{time.time()}}\\n")
    time.sleep(3)
    open(T + "/eventos.log", "a").write(f"fim {{time.time()}}\\n")
limitadas = open(T + "/limitadas").read().split() if os.path.exists(T + "/limitadas") else []
if conta in limitadas:
    open(os.path.join(proj, SESSAO + ".jsonl"), "a").write('{{"conversa": "metade"}}\\n')
    print(json.dumps({{"type": "rate_limit_event", "rate_limit_info": {{"status": "rejected", "resetsAt": 1792279800}}}}))
    print(json.dumps({{"type": "result", "is_error": True, "result": "Claude AI usage limit reached", "session_id": SESSAO}}))
    sys.exit(0)
if "PRESO" in pedido:
    open(T + "/filho.pid", "w").write(str(subprocess.Popen(["sleep", "300"]).pid))
final = {{"type": "result", "is_error": False, "result": f"Terminei em {{os.path.basename(os.getcwd())}} "
         f"(conversa nesta conta: {{sessao_aqui}})", "session_id": SESSAO, "num_turns": 4, "total_cost_usd": 0.12}}
print(json.dumps(final, separators=(",", ":") if "COMPACTO" in pedido else (", ", ": ")), flush=True)
if "PRESO" in pedido:
    time.sleep(300)
""")
os.chmod(FALSO, 0o755)
rn.CLAUDE = FALSO


def chamadas():
    try:
        with open(f"{tmp}/chamadas.jsonl") as f:
            return [json.loads(linha) for linha in f]
    finally:
        os.remove(f"{tmp}/chamadas.jsonl")


def contas_prontas(**prontas):
    with open(f"{base}/contas.json", "w") as f:
        json.dump(prontas, f)


def limitadas(*nomes):
    with open(f"{tmp}/limitadas", "w") as f:
        f.write(" ".join(nomes))


def trabalho(id_, **job):
    caminho = f"{base}/fila/{id_}.{job.get('fase', 'executar')}.json"
    with open(caminho, "w") as f:
        json.dump({"id": id_, "fase": "executar", "conta": "pessoal", "projeto": "app", **job}, f)
    inicio = time.monotonic()
    rn.processar(caminho)
    try:
        with open(f"{base}/resultados/{id_}.{job.get('fase', 'executar')}.json") as f:
            return json.load(f), time.monotonic() - inicio
    except FileNotFoundError:
        return None, time.monotonic() - inicio


contas_prontas(pessoal=True, trabalho=True)

# --- trabalho normal ---
r, _ = trabalho("aaaa0001", projeto="lista-compras", modelo="sonnet", esforco="high", minutos=5,
                pedido="COMMIT faz um app de lista de compras")
c = chamadas()[-1]
argv = c["argv"]
confere("terminou ok com resumo e sessão", r["ok"] and r["texto"].startswith("Terminei em lista-compras")
        and r["sessao"] == SESSAO, r)
confere("roda na pasta do projeto", c["cwd"] == f"{projetos}/lista-compras")
confere("pasta herda o setgid de projetos (grupo atena-lab)", os.stat(f"{projetos}/lista-compras").st_mode & 0o2000)
confere("usa a conta escolhida", c["env"]["CLAUDE_CONFIG_DIR"] == f"{base}/contas/pessoal")
confere("HOME do trabalhador e PATH sem sbin nem as ferramentas das skills", c["env"]["HOME"] == base
        and "sbin" not in c["env"]["PATH"] and rn.FERRAMENTAS not in c["env"]["PATH"])
confere("sandbox pelo --settings lab.json", argv[argv.index("--settings") + 1] == rn.CONFIG)
confere("só a configuração da conta (--setting-sources user)", argv[argv.index("--setting-sources") + 1] == "user")
confere("permissões vão para a ponte", argv[argv.index("--permission-prompt-tool") + 1] == "mcp__dono__permissao"
        and "--strict-mcp-config" in argv)
confere("modo acceptEdits (nada de bypassPermissions)", argv[argv.index("--permission-mode") + 1] == "acceptEdits"
        and "bypassPermissions" not in argv)
confere("modelo e esforço escolhidos", argv[argv.index("--model") + 1] == "sonnet" and argv[argv.index("--effort") + 1] == "high")
regras = argv[argv.index("--append-system-prompt") + 1]
confere("regras citam a pasta do projeto, sem skills nem atena-tela", f"{projetos}/lista-compras" in regras
        and "atena-tela" not in regras and "impeccable" not in regras)
confere("regras: a imagem do app precisa de sh e python3, node ou wget, ou de um HEALTHCHECK próprio",
        "sh e python3, node ou wget" in regras and "HEALTHCHECK" in regras)
with open(argv[argv.index("--mcp-config") + 1]) as f:
    mcp = json.load(f)
confere("MCP da ponte com o id do trabalho", mcp["mcpServers"]["dono"]["args"][-2:] == ["--trabalho", "aaaa0001"])
confere("git seguro no ambiente (sem fsmonitor e sem hooks)", c["env"].get("GIT_CONFIG_KEY_0") == "core.fsmonitor"
        and c["env"].get("GIT_CONFIG_VALUE_1") == "/dev/null")
confere("commits do trabalho no resultado", r.get("commits") and r["commits"][0].endswith("primeiro commit"), r.get("commits"))
autor = subprocess.run(["git", "-C", f"{projetos}/lista-compras", "log", "-1", "--format=%an"],
                       capture_output=True, text=True).stdout
confere("commit com o nome do trabalhador (gitconfig)", "Claude Code (Atena)" in autor, autor)
confere("trabalho sai da fila", not os.path.exists(f"{base}/fila/aaaa0001.executar.json"))
confere("registro da conversa guardado", os.path.getsize(f"{base}/registros/aaaa0001.executar.jsonl") > 0)

# --- plano, continuando uma sessão ---
r, _ = trabalho("aaaa0002", fase="plano", conta="trabalho", projeto="lista-compras", pedido="planeja login",
                sessao=SESSAO, sessao_conta="trabalho")
argv = chamadas()[-1]["argv"]
confere("plano: modo plan e --resume", argv[argv.index("--permission-mode") + 1] == "plan"
        and argv[argv.index("--resume") + 1] == SESSAO and "--model" not in argv)
confere("plano sem lista de commits", "commits" not in r)

# --- recusas ---
r, _ = trabalho("aaaa0003", projeto="../../etc", pedido="x")
confere("projeto com caminho: erro sem rodar", "projeto inválido" in r["texto"] and not os.path.exists(f"{tmp}/chamadas.jsonl"))
r, _ = trabalho("aaaa0004", conta="root", pedido="x")
confere("conta fora do atena.conf: erro sem rodar", "sem conta" in r["texto"] and not os.path.exists(f"{tmp}/chamadas.jsonl"))
r, _ = trabalho("aaaa0005", pedido="x", sessao="$(rm -rf /)")
confere("sessão inválida: erro", "sessão inválida" in r["texto"])
trabalho("aaaa0006", pedido="x", modelo="gpt-9", esforco="infinito")
argv = chamadas()[-1]["argv"]
confere("modelo e esforço desconhecidos são ignorados", "--model" not in argv and "--effort" not in argv)
r, _ = trabalho("ZZZ", pedido="x")
confere("id fora do padrão: descartado", r is None and not os.path.exists(f"{base}/fila/ZZZ.executar.json"))

# --- cancelar no meio ---
threading.Timer(3, lambda: open(f"{base}/fila/aaaa0007.cancelar", "w").close()).start()
r, s = trabalho("aaaa0007", projeto="demorado", pedido="DEMORA bastante")
confere("cancelado no meio, em segundos, com a sessão guardada", r.get("cancelado") and s < 20 and r.get("sessao") == SESSAO, r)
confere("sinal de cancelar é consumido", not os.path.exists(f"{base}/fila/aaaa0007.cancelar"))
chamadas()

# --- contas do atena.conf ---
confere("contas na ordem do atena.conf", rn.contas() == ["pessoal", "trabalho"], rn.contas())
with open(rn.CONF, "w") as f:
    f.write('ATENA_CLAUDE_CONTAS="pessoal, Trabalho;x, pessoal"\n')
confere("nomes inválidos e repetidos ficam de fora", rn.contas() == ["pessoal"], rn.contas())
with open(rn.CONF, "w") as f:
    f.write("ATENA_TZ=America/Sao_Paulo\n")
confere("sem ATENA_CLAUDE_CONTAS: a conta principal", rn.contas() == ["principal"], rn.contas())
with open(rn.CONF, "w") as f:
    f.write('ATENA_CLAUDE_CONTAS="pessoal trabalho"\nATENA_TZ=America/Sao_Paulo\n')

# --- limite de uso, sem troca automática (o padrão) ---
limitadas("pessoal")
r, _ = trabalho("bbbb0001", pedido="faz")
c = chamadas()
confere("sem troca: para no limite, numa chamada só, com a hora de volta", not r["ok"] and len(c) == 1
        and "bateu o limite" in r["texto"] and "volta às" in r["texto"] and "trocas" not in r, r)
confere("sem troca: a sessão fica para continuar depois", r.get("sessao") == SESSAO)

# --- limite de uso, com ATENA_CLAUDE_TROCA=sim ---
with open(rn.CONF, "a") as f:
    f.write("ATENA_CLAUDE_TROCA=sim\n")
r, _ = trabalho("bbbb0002", pedido="faz", modelo="sonnet")
c = chamadas()
confere("com troca: a pessoal bateu o limite e continuou na trabalho", r["ok"] and r["conta"] == "trabalho"
        and [x["conta"] for x in c] == ["pessoal", "trabalho"], r)
confere("com troca: a conversa foi levada (o --resume acha a sessão)", r["texto"].endswith("(conversa nesta conta: True)"), r["texto"])
confere("com troca: a segunda chamada continua a sessão, com o mesmo modelo", c[1]["argv"][-3:-1] == ["--resume", SESSAO]
        and "sonnet" in c[1]["argv"] and c[1]["argv"][-1].startswith("A conta anterior bateu o limite"))
confere("com troca: troca registrada com o horário de volta", r["trocas"][0]["de"] == "pessoal"
        and r["trocas"][0]["para"] == "trabalho" and "volta às" in r["trocas"][0]["motivo"], r.get("trocas"))
contas_prontas(pessoal=True, trabalho=False)
r, _ = trabalho("bbbb0003", pedido="faz")
confere("com troca, outra sem login: para e explica", not r["ok"] and len(chamadas()) == 1
        and "não há outra conta com login" in r["texto"], r)
contas_prontas(pessoal=True, trabalho=True)
limitadas("pessoal", "trabalho")
r, _ = trabalho("bbbb0004", pedido="faz")
confere("com troca, todas no limite: passa uma vez por cada e para",
        not r["ok"] and [x["conta"] for x in chamadas()] == ["pessoal", "trabalho"], r)
limitadas()
with open(rn.CONF, "w") as f:
    f.write('ATENA_CLAUDE_CONTAS="pessoal trabalho"\nATENA_TZ=America/Sao_Paulo\n')

# --- continuar em outra conta, a pedido do dono ---
for conta in ("pessoal", "trabalho"):
    for nome in os.listdir(f"{base}/contas/{conta}/projects/-proj"):
        os.remove(f"{base}/contas/{conta}/projects/-proj/{nome}")
with open(f"{base}/contas/pessoal/projects/-proj/{SESSAO}.jsonl", "w") as f:
    f.write('{"conversa": "anterior"}\n')
r, _ = trabalho("cccc0001", conta="trabalho", pedido="continua", sessao=SESSAO, sessao_conta="pessoal")
confere("continuar em outra conta: a conversa vai junto", r["ok"] and r["texto"].endswith("(conversa nesta conta: True)"), r)
chamadas()
r, _ = trabalho("cccc0002", conta="trabalho", pedido="continua", sessao="22222222-2222-3333-4444-555555555555",
                sessao_conta="pessoal")
confere("continuar em outra conta sem a conversa: erro sem rodar", not r["ok"] and "não consegui levar" in r["texto"]
        and not os.path.exists(f"{tmp}/chamadas.jsonl"), r)
r, _ = trabalho("cccc0003", conta="trabalho", pedido="continua", sessao=SESSAO, sessao_conta="root")
confere("continuar de uma conta fora do atena.conf: erro", not r["ok"] and "não consegui levar" in r["texto"], r)

# --- travas de git: a Atena também escreve nos projetos ---
for chave in ("core.fsmonitor", "core.hooksPath", "filter.lfs.clean", "diff.pdf.textconv", "include.path",
              "includeif.gitdir:/x/.path", "core.sshCommand", "credential.helper"):
    confere(f"chave perigosa reconhecida: {chave}", bool(rn.GIT_PERIGOSO.fullmatch(chave)))
for chave in ("core.bare", "user.name", "remote.origin.url", "branch.main.remote"):
    confere(f"chave comum não é perigosa: {chave}", not rn.GIT_PERIGOSO.fullmatch(chave))
limpo = f"{projetos}/lista-compras"
GIT = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
marca = f"{tmp}/fsmonitor-rodou"
with open(f"{tmp}/fsmonitor.sh", "w") as f:
    f.write(f"#!/bin/sh\ntouch {marca}\nexit 1\n")
os.chmod(f"{tmp}/fsmonitor.sh", 0o755)
subprocess.run(["git", "-C", limpo, "config", "core.fsmonitor", f"{tmp}/fsmonitor.sh"], check=True, env=GIT)
with open(f"{limpo}/app.py", "a") as f:
    f.write("# mudou\n")
rn.git(limpo, "status", "--short")
confere("o git do runner não roda o fsmonitor do projeto", not os.path.exists(marca))
subprocess.run(["git", "-C", limpo, "status", "--short"], capture_output=True)
confere("(controle: sem a trava, o fsmonitor roda)", os.path.exists(marca))
r, _ = trabalho("dddd0001", projeto="lista-compras", pedido="faz")
confere("projeto com fsmonitor: trabalho recusado, sem abrir o Claude Code",
        not r["ok"] and ".git/config" in r["texto"] and not os.path.exists(f"{tmp}/chamadas.jsonl"), r)
subprocess.run(["git", "-C", limpo, "config", "--unset", "core.fsmonitor"], check=True)
confere("pasta sem git: nada a conferir", rn.git_config_perigosa(projetos) == [])

# --- fecha o Claude Code que ficou preso depois do resumo final ---
rn.FOLGA_FINAL = 3
r, s = trabalho("eeee0001", pedido="PRESO")
confere("preso depois do resumo: fecha sozinho e termina bem", r.get("ok") and s < 20 and "Terminei" in r["texto"], f"{s:.0f} s {r}")
with open(f"{tmp}/filho.pid") as f:
    filho = int(f.read())
time.sleep(1)
try:
    with open(f"/proc/{filho}/stat") as f:
        vivo = f.read().split()[2] != "Z"
except FileNotFoundError:
    vivo = False
confere("o processo que sobrou também foi encerrado", not vivo)
with open(f"{base}/registros/eeee0001.executar.jsonl") as f:
    notas = [json.loads(linha) for linha in f if '"atena"' in linha]
confere("o registro anota que foi fechado", notas and "fechado" in notas[0].get("nota", ""), notas)
r, s = trabalho("eeee0002", pedido="COMPACTO PRESO")
confere("evento final sem espaços também é visto", r.get("ok") and s < 20, f"{s:.0f} s")
chamadas()

# --- até 3 trabalhos ao mesmo tempo ---
ids = ["ffff0001", "ffff0002", "ffff0003", "ffff0004"]
for i, id_ in enumerate(ids):
    with open(f"{base}/fila/{id_}.executar.json", "w") as f:
        json.dump({"id": id_, "fase": "executar", "conta": "pessoal", "projeto": f"p{i}", "pedido": "PARALELO"}, f)
    time.sleep(0.05)   # ordem de chegada
with open(f"{base}/fila/quebrado.json", "w") as f:
    f.write("[1, 2")   # arquivo com defeito no meio da fila
rn.atender_fila()
with open(f"{tmp}/eventos.log") as f:
    eventos = [linha.split() for linha in f]
ativos, pico = 0, 0
for tipo, _ in sorted(eventos, key=lambda e: float(e[1])):
    ativos += 1 if tipo == "inicio" else -1
    pico = max(pico, ativos)
resultados = {}
for id_ in ids:
    with open(f"{base}/resultados/{id_}.executar.json") as f:
        resultados[id_] = json.load(f)
confere("os 4 trabalhos terminaram", all(x["ok"] for x in resultados.values()))
confere("no máximo 3 ao mesmo tempo", pico == 3, pico)
inicios = sorted(float(t) for tipo, t in eventos if tipo == "inicio")
confere("o 4º só começa quando abre uma vaga", inicios[3] - inicios[0] >= 3, round(inicios[3] - inicios[0], 1))
confere("arquivo com defeito saiu da fila sem travar", not os.listdir(f"{base}/fila"), os.listdir(f"{base}/fila"))
confere("cada um na pasta do seu projeto", resultados["ffff0003"]["texto"].startswith("Terminei em p2"))
original = rn.executar_trabalho
rn.executar_trabalho = lambda job: (_ for _ in ()).throw(RuntimeError("bug de teste"))
with open(f"{base}/fila/ffff0005.executar.json", "w") as f:
    json.dump({"id": "ffff0005", "fase": "executar", "conta": "pessoal", "projeto": "x", "pedido": "faz"}, f)
rn.atender_fila()
with open(f"{base}/resultados/ffff0005.executar.json") as f:
    r = json.load(f)
confere("erro inesperado vira resultado de falha", r["ok"] is False and "bug de teste" in r["texto"], r)
rn.executar_trabalho = original

# --- skills (ATENA_CLAUDE_SKILLS) ---
if os.path.exists(f"{tmp}/chamadas.jsonl"):
    os.remove(f"{tmp}/chamadas.jsonl")
rn.SKILLS = os.path.join(RAIZ, "host", "lab", "skills.json")
r, _ = trabalho("abab0001", projeto="site", skill="impeccable polish", pedido="capricha")
confere("skill com as skills desligadas: falha sem chamar o Claude Code", not r["ok"] and "catálogo" in r["texto"]
        and not os.path.exists(f"{tmp}/chamadas.jsonl"), r)
with open(rn.CONF, "a") as f:
    f.write("ATENA_CLAUDE_SKILLS=sim\n")
r, _ = trabalho("abab0002", projeto="site", skill="impeccable polish", pedido="capricha")
c = chamadas()[-1]
argv = c["argv"]
regras = argv[argv.index("--append-system-prompt") + 1]
confere("skill: o comando dela na primeira linha do pedido", r["ok"] and argv[-1].startswith("/impeccable polish\n\n")
        and "capricha" in argv[-1], argv[-1][:80])
confere("com as skills: atena-tela e os servidores de linguagem no PATH",
        c["env"]["PATH"].startswith(f"{rn.FERRAMENTAS}/bin:{rn.FERRAMENTAS}/node_modules/.bin:"), c["env"]["PATH"])
confere("com as skills: as regras dizem quando usar cada uma", "atena-tela" in regras and "frontend-design" in regras
        and regras.index("Skills instaladas") < regras.index("revise o próprio diff"))
r, _ = trabalho("abab0003", projeto="site", pedido="sem skill")
argv = chamadas()[-1]["argv"]
confere("sem skill no pedido, o pedido começa normal", r["ok"] and argv[-1].startswith("Pedido do dono:"), argv[-1][:40])
r, _ = trabalho("abab0004", projeto="site", skill="impeccable rm", pedido="faz")
confere("skill fora do catálogo: falha", not r["ok"] and "impeccable rm" in r["texto"], r)

# --- receitas de estilo e o Node do lab ---
rn.RECEITAS, rn.NODE = f"{tmp}/receitas", f"{tmp}/node"
os.makedirs(f"{rn.RECEITAS}/linear-app/prints")
for nome, conteudo in (("RECEITA.md", "# Linear\n"), ("receita.json", "{}"), ("prints/pc.jpg", "jpeg")):
    with open(f"{rn.RECEITAS}/linear-app/{nome}", "w") as f:
        f.write(conteudo)
os.symlink("/etc/hostname", f"{rn.RECEITAS}/linear-app/DESIGN.md")   # link na biblioteca: não vai junto
r, _ = trabalho("abab0005", projeto="loja", skill="frontend-design", receitas=["linear-app"], pedido="faz a loja")
c = chamadas()[-1]
destino = f"{projetos}/loja/.atena/receitas/linear-app"
confere("receitas: copiadas para .atena/receitas no projeto (sem links)",
        r["ok"] and os.path.isfile(f"{destino}/RECEITA.md") and os.path.isfile(f"{destino}/prints/pc.jpg")
        and not os.path.exists(f"{destino}/DESIGN.md"), r)
confere("receitas: a skill segue na primeira linha, e o pedido diz para seguir o estilo",
        c["argv"][-1].startswith("/frontend-design:frontend-design\n\nReceitas de estilo")
        and ".atena/receitas/linear-app/" in c["argv"][-1] and "não copie" in c["argv"][-1], c["argv"][-1][:120])
confere("sem o Node do lab instalado, o PATH fica como era", not c["env"]["PATH"].startswith(rn.NODE))
os.makedirs(f"{rn.NODE}/bin")
with open(f"{rn.NODE}/bin/node", "w") as f:
    f.write("")
r, _ = trabalho("abab0006", projeto="loja", receitas=["nao-existe"], pedido="faz")
confere("receita que sumiu da biblioteca: falha sem chamar o Claude Code", not r["ok"] and "nao-existe" in r["texto"], r)
r, _ = trabalho("abab0007", projeto="loja", pedido="faz")
caminho = chamadas()[-1]["env"]["PATH"]
confere("com o Node do lab: ele vem antes do Node do sistema", f"{rn.NODE}/bin:/usr/local/bin:/usr/bin" in caminho and r["ok"], caminho)

# --- o runner morreu no meio (queda de energia): o próximo que sobe fecha o trabalho como interrompido ---
# O executor de verdade põe o trabalho na fila; um runner de verdade (outro processo) pega e morre com SIGKILL.
ex, _, avisos = executor()
ex.CLAUDE, ex.PROJETOS_LAB = base, projetos
atena = {"cliente": "hermes", "zonas": ["lab"], "acoes": ["claude.tarefa"], "aprovar": []}
params = {"pedido": "COMMIT DEMORA faz um app grande", "conta": "pessoal", "projeto": "orfao"}
titulo, _ = ex.preparar_claude_tarefa(atena, params)
p = ex.criar_pedido(atena, "claude.tarefa", params, "chat", titulo)
ex.mudar(p, estado="executando")
ex.executar(p)
nome = f"{p['id']}.executar"
marca, resultado = f"{base}/registros/{nome}.andamento", f"{base}/resultados/{nome}.json"
if os.path.exists(f"{tmp}/chamadas.jsonl"):
    os.remove(f"{tmp}/chamadas.jsonl")
filho = subprocess.Popen([sys.executable, "-c", f"""
import importlib.machinery, sys
sys.dont_write_bytecode = True
rn = importlib.machinery.SourceFileLoader("runner", {os.path.join(RAIZ, "host", "sbin", "atena-claude-runner")!r}).load_module()
rn.BASE, rn.PROJETOS, rn.CONF, rn.CLAUDE, rn.SKILLS = {base!r}, {projetos!r}, {rn.CONF!r}, {FALSO!r}, {rn.SKILLS!r}
rn.principal()
"""])
comecou = esperar(lambda: rn.git(f"{projetos}/orfao", "log", "--oneline"), 20)
confere("runner pega o trabalho e o Claude Code faz um commit", comecou)
if comecou:
    falso = chamadas()[-1]["pid"]
    rn.principal()   # um segundo runner (à mão) com o primeiro no ar
    confere("com outro runner no ar, não mexe no trabalho que está rodando", os.path.exists(marca)
            and not os.path.exists(resultado))
    filho.kill()
    filho.wait()
    os.killpg(falso, signal.SIGKILL)   # o Claude Code está numa sessão própria
    confere("morreu no meio: fica a marca de andamento, sem resultado", os.path.exists(marca) and not os.path.exists(resultado))
    uma_volta(ex)
    confere("o executor segue esperando (o runner tinha pegado)", p["estado"] == "executando")
    rn.principal()   # o runner sobe de novo (o atena-claude.path vê a marca)
    with open(resultado) as f:
        r = json.load(f)
    confere("ao subir, fecha o trabalho como interrompido, com a conversa e os commits", r["ok"] is False
            and r.get("interrompido") and "interrompido" in r["texto"] and r.get("sessao") == SESSAO
            and r.get("commits", [""])[0].endswith("primeiro commit"), r)
    confere("a marca de andamento sai", not os.path.exists(marca))
    avisos.clear()
    uma_volta(ex)
    confere("o executor fica sabendo: falhou, com a conversa guardada", p["estado"] == "falhou" and p.get("sessao") == SESSAO
            and "interrompido" in p.get("resumo", ""), p)
    confere("o celular fica sabendo, com os commits", any(p["id"] in a["titulo"] and "(1 commits)" in a["texto"] for a in avisos))
    titulo, _ = ex.preparar_claude_tarefa(atena, {"pedido": "continue de onde parou", "continuar": p["id"]})
    confere("o projeto fica livre e dá para continuar de onde parou", "orfao" in titulo, titulo)
else:
    filho.kill()
filho.wait()
for id_ in ("abcd0001", "abcd0002"):   # um com o cancelar pedido; o outro já tinha o resultado
    with open(f"{base}/registros/{id_}.executar.andamento", "w") as f:
        json.dump({"id": id_, "fase": "executar", "conta": "pessoal", "projeto": "orfao"}, f)
open(f"{base}/fila/abcd0001.cancelar", "w").close()
with open(f"{base}/resultados/abcd0002.executar.json", "w") as f:
    json.dump({"id": "abcd0002", "fase": "executar", "ok": True, "texto": "terminou antes de o runner morrer"}, f)
rn.principal()
with open(f"{base}/resultados/abcd0001.executar.json") as f:
    r = json.load(f)
confere("interrompido com o cancelar pedido: vira cancelado, e o sinal sai", r.get("cancelado")
        and not os.path.exists(f"{base}/fila/abcd0001.cancelar"), r)
with open(f"{base}/resultados/abcd0002.executar.json") as f:
    r = json.load(f)
confere("morreu depois de gravar o resultado: o resultado fica como estava", r["ok"] and r["texto"].startswith("terminou"))
confere("nenhuma marca de andamento sobra", not [n for n in os.listdir(f"{base}/registros") if n.endswith(".andamento")])

fim()
