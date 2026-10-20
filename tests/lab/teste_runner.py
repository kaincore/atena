"""O atena-claude-runner com um Claude Code de mentira: trabalho normal, plano, recusas, cancelar,
contas do atena.conf, limite de uso (com e sem troca automática), continuar em outra conta, as
travas de git, o fechamento depois do resumo final e os trabalhos em paralelo."""
import json
import os
import subprocess
import threading
import time

from comum import SESSAO, confere, fim, runner

rn, tmp = runner()
base, projetos = rn.BASE, rn.PROJETOS

# Claude Code de mentira: anota como foi chamado e responde em stream-json. O pedido escolhe o caso:
# COMMIT faz um commit; DEMORA espera 60 s; PRESO manda o resumo e fica aberto (com um filho);
# PARALELO anota início e fim. Uma conta listada em <tmp>/limitadas bate o limite de uso.
FALSO = f"{tmp}/claude-falso"
with open(FALSO, "w") as f:
    f.write(f"""#!/usr/bin/env python3
import json, os, subprocess, sys, time
T, SESSAO = {tmp!r}, {SESSAO!r}
conta = os.path.basename(os.environ["CLAUDE_CONFIG_DIR"])
pedido = sys.argv[-1]
with open(T + "/chamadas.jsonl", "a") as f:
    f.write(json.dumps({{"conta": conta, "argv": sys.argv[1:], "cwd": os.getcwd(), "env": dict(os.environ)}}) + "\\n")
proj = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "projects", "-proj")
os.makedirs(proj, exist_ok=True)
sessao_aqui = os.path.exists(os.path.join(proj, SESSAO + ".jsonl"))
print(json.dumps({{"type": "system", "subtype": "init", "session_id": SESSAO}}), flush=True)
if "DEMORA" in pedido:
    time.sleep(60)
if "PARALELO" in pedido:
    open(T + "/eventos.log", "a").write(f"inicio {{time.time()}}\\n")
    time.sleep(3)
    open(T + "/eventos.log", "a").write(f"fim {{time.time()}}\\n")
if "COMMIT" in pedido:
    subprocess.run(["git", "init", "-q"], check=True)
    open("app.py", "w").write("print('oi')\\n")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-q", "-m", "primeiro commit"], check=True)
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
confere("HOME do trabalhador e PATH sem sbin", c["env"]["HOME"] == base and "sbin" not in c["env"]["PATH"])
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

fim()
