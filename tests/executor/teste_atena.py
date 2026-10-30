"""A Atena no painel (atena.*): as conversas, o chat com a resposta aos pedaços e a agenda dela, contra um
Hermes de mentira que fala a API de verdade (HTTP e SSE). Também o GET /pedido?versao, o arquivo dos
trabalhos antigos do Claude Code e o token-acertar."""
import contextlib
import http.server
import io
import json
import os
import sys
import threading
import time
import urllib.parse

from comum import carregar, confere, erro, fim, ligar, pedir, token

ex, tmp = carregar()
ex.PEDIDOS = f"{tmp}/pedidos.json"
ex.HERMES_ENV = f"{tmp}/hermes.env"
with open(ex.HERMES_ENV, "w") as f:
    f.write("# comentário\nTELEGRAM_BOT_TOKEN=nada\nAPI_SERVER_KEY=chave-teste\n")
c = {"cliente": "painel", "zonas": ["core", "apps", "ai", "agents", "lab"], "acoes": [], "aprovar": []}


# --- o Hermes de mentira ------------------------------------------------------------------------------
SESSOES = {
    "20261029_tg": {"id": "20261029_tg", "source": "telegram", "title": "Conversa", "preview": "Atena, me fala",
                    "started_at": 1000.0, "last_active": 2000.0, "message_count": 6, "tool_call_count": 2,
                    "estimated_cost_usd": 0.01, "model": "haiku", "is_internal_child": False},
    "api_1": {"id": "api_1", "source": "api_server", "title": None, "preview": "oi", "started_at": 900.0,
              "message_count": 2, "is_internal_child": False},
    "cron_461a_1": {"id": "cron_461a_1", "source": "cron", "title": "ronda · Oct 30", "started_at": 800.0,
                    "message_count": 2, "is_internal_child": False},
    "filho": {"id": "filho", "source": "api_server", "is_internal_child": True, "started_at": 700.0},
}
SAIDA_CLAUDE = json.dumps({"output": json.dumps({"ok": True, "acao": "claude.tarefa", "pedido": "e4d647e7",
                                                 "estado": "executando"})})
MENSAGENS = [
    {"id": 1, "role": "user", "content": "[Cron delivery: bom-dia]\nBom dia! Servidor em ordem.", "timestamp": 10.0},
    {"id": 2, "role": "user", "content": "faz um jogo de nave com o claude code; a senha: hunter2", "timestamp": 11.0},
    {"id": 3, "role": "assistant", "content": "", "timestamp": 12.0, "tool_calls": [
        {"id": "t1", "function": {"name": "terminal", "arguments": json.dumps(
            {"command": "python3 /opt/data/scripts/acao.py claude.tarefa '{\"projeto\": \"nave\"}'"})}},
        {"id": "t2", "function": {"name": "skill_view", "arguments": "{\"name\": \"lab\"}"}}]},
    {"id": 4, "role": "tool", "tool_call_id": "t1", "tool_name": "terminal", "content": SAIDA_CLAUDE, "timestamp": 13.0},
    {"id": 5, "role": "tool", "tool_call_id": "t2", "tool_name": "skill_view", "content": "{\"success\": true}", "timestamp": 13.5},
    {"id": 6, "role": "session_meta", "content": None, "timestamp": 13.9},
    {"id": 7, "role": "assistant", "content": "Mandei ao Claude Code: trabalho e4d647e7.", "timestamp": 14.0},
    {"id": 8, "role": "assistant", "content": "", "timestamp": 15.0, "tool_calls": [
        {"id": "t3", "function": {"name": "terminal", "arguments": json.dumps(
            {"command": "T=$(cat /opt/data/executor.token); S=/run/atena-executor/executor.sock; "
                        "for a in status.servicos sistema.rede; do curl --unix-socket $S http://x/acao/$a; done"})}}]},
]
JOBS = {
    "461a4cd4d149": {"id": "461a4cd4d149", "name": "ronda", "prompt": "Ronda do servidor", "schedule": {"kind": "interval", "minutes": 3},
                     "schedule_display": "every 3m", "enabled": True, "state": "scheduled",
                     "next_run_at": "2026-10-30T10:19:58-03:00", "last_run_at": "2026-10-30T10:16:58-03:00",
                     "last_status": "ok", "deliver": "telegram", "monitor_script": "ronda.py", "repeat": {"times": None, "completed": 3107}},
    "abc123def456": {"id": "abc123def456", "name": "lembrete remédio", "prompt": "Lembre o dono do remédio",
                     "schedule": {"kind": "once"}, "schedule_display": "once at 2026-11-01 15:00", "enabled": True,
                     "state": "paused", "next_run_at": None, "deliver": "telegram", "last_error": "token=abc123 caiu"},
}
VISTO = {"chamadas": [], "aprovacao": None, "parar": None}
CHAT = {"liberar": threading.Event(), "modo": "aprovar"}


class Hermes(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def json(self, status, corpo):
        dados = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def corpo(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")

    def autorizado(self):
        if self.headers.get("Authorization") != "Bearer chave-teste":
            self.json(401, {"error": {"message": "Invalid API key"}})
            return False
        return True

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        VISTO["chamadas"].append(("GET", self.path))
        if not self.autorizado():
            return
        partes = url.path.strip("/").split("/")
        if url.path == "/api/sessions":
            fonte = urllib.parse.parse_qs(url.query).get("source", [None])[0]
            dados = [s for s in SESSOES.values() if fonte in (None, s["source"])]
            self.json(200, {"data": dados, "has_more": False})
        elif partes[:2] == ["api", "sessions"] and len(partes) == 3:
            s = SESSOES.get(partes[2])
            self.json(200, {"session": s}) if s else self.json(404, {"error": {"message": f"Session not found: {partes[2]}"}})
        elif partes[:2] == ["api", "sessions"] and partes[3:] == ["messages"]:
            self.json(200, {"data": list(reversed(MENSAGENS))})
        elif url.path == "/api/jobs":
            self.json(200, {"jobs": list(JOBS.values())})
        elif partes[:2] == ["api", "jobs"] and len(partes) == 3:
            j = JOBS.get(partes[2])
            self.json(200, {"job": j}) if j else self.json(404, {"error": "Job not found"})
        else:
            self.json(404, {"error": "rota"})

    def do_DELETE(self):
        VISTO["chamadas"].append(("DELETE", self.path))
        if self.autorizado():
            self.json(200, {"ok": JOBS.pop(self.path.rsplit("/", 1)[1], None) is not None})

    def do_POST(self):
        VISTO["chamadas"].append(("POST", self.path))
        if not self.autorizado():
            return
        corpo, partes = self.corpo(), self.path.strip("/").split("/")
        if self.path == "/api/sessions":
            SESSOES["api_novo"] = {"id": "api_novo", "source": "api_server", "started_at": 3000.0}
            self.json(201, {"session": SESSOES["api_novo"]})
        elif partes[-1] == "stream":
            self.conversar(corpo)
        elif partes[:2] == ["v1", "runs"] and partes[3] == "approval":
            VISTO["aprovacao"] = corpo.get("choice")
            CHAT["liberar"].set()
            self.json(200, {"ok": True})
        elif partes[:2] == ["v1", "runs"] and partes[3] == "stop":
            VISTO["parar"] = partes[2]
            CHAT["liberar"].set()
            self.json(200, {"ok": True})
        elif self.path == "/api/jobs":
            if corpo.get("schedule") == "nunca":
                return self.json(400, {"error": "Invalid schedule 'nunca'"})
            job = {"id": "fff000aaa111", "name": corpo["name"], "prompt": corpo["prompt"], "deliver": corpo["deliver"],
                   "schedule": {"kind": "once"}, "schedule_display": corpo["schedule"], "enabled": True,
                   "state": "scheduled", "repeat": {"times": corpo.get("repeat"), "completed": 0}}
            JOBS[job["id"]] = job
            self.json(200, {"job": job})
        elif partes[:2] == ["api", "jobs"]:
            j = JOBS[partes[2]]
            j["state"] = {"pause": "paused", "resume": "scheduled"}.get(partes[3], j["state"])
            self.json(200, {"job": j})
        else:
            self.json(404, {"error": "rota"})

    def conversar(self, corpo):
        """O SSE de /api/sessions/{id}/chat/stream: pedaços, uma ferramenta, a aprovação e o fim."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        def evento(nome, dados):
            self.wfile.write(f"event: {nome}\ndata: {json.dumps(dados)}\n\n".encode())
            self.wfile.flush()

        evento("run.started", {"run_id": "run_1", "user_message": {"content": corpo["message"]}})
        evento("assistant.delta", {"delta": "Vou "})
        self.wfile.write(b": keepalive\n\n")
        evento("assistant.delta", {"delta": "conferir. token=segredo123"})
        evento("tool.started", {"tool_name": "terminal", "args": {"command": "python3 acao.py status.recursos"}})
        if CHAT["modo"] == "aprovar":
            evento("approval.request", {"command": "rm -rf /tmp/x", "description": "apagar pasta",
                                        "choices": ["once", "session", "deny"], "run_id": "run_1"})
        CHAT["liberar"].wait(10)
        if CHAT["modo"] == "parar":
            evento("run.cancelled", {"messages": []})
            evento("done", {})
            return
        evento("tool.completed", {"tool_name": "terminal"})
        evento("assistant.completed", {"content": "Tudo certo: CPU em 12%."})
        evento("run.completed", {"messages": [
            {"role": "assistant", "content": "", "tool_calls": [
                {"id": "x1", "function": {"name": "terminal", "arguments": "{\"command\": \"acao.py status.recursos\"}"}}]},
            {"role": "tool", "tool_call_id": "x1", "tool_name": "terminal", "content": "{\"output\": \"cpu 12%\"}"},
            {"role": "assistant", "content": "Tudo certo: CPU em 12%."}]})
        evento("done", {})


servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Hermes)
threading.Thread(target=servidor.serve_forever, daemon=True).start()
ex.HERMES_API = f"http://127.0.0.1:{servidor.server_address[1]}"

# --- a chave e os erros da API --------------------------------------------------------------------------
confere("a chave vem do .env do Hermes", ex.chave() == "chave-teste")
with open(ex.HERMES_ENV, "w") as f:
    f.write("API_SERVER_KEY=errada\n")
status, msg = erro(ex.acao_atena_conversas, c, {})
confere("chave errada: o Hermes recusa, e o erro diz o motivo", status == 502 and "Invalid API key" in msg, (status, msg))
os.remove(ex.HERMES_ENV)
status, msg = erro(ex.acao_atena_conversas, c, {})
confere("sem a chave: 503 que manda rodar o instalador", status == 503 and "--hermes" in msg, (status, msg))
with open(ex.HERMES_ENV, "w") as f:
    f.write("API_SERVER_KEY=\"chave-teste\"\n")
api = ex.HERMES_API
ex.HERMES_API = "http://127.0.0.1:9"
status, msg = erro(ex.acao_atena_conversas, c, {})
confere("o Hermes fora do ar: 503", status == 503 and "hermes" in msg, (status, msg))
ex.HERMES_API = api

# --- as conversas -----------------------------------------------------------------------------------------
r = ex.acao_atena_conversas(c, {})
origens = {x["id"]: x["origem"] for x in r["conversas"]}
confere("conversas: telegram, painel e agenda, sem a filha interna",
        origens == {"20261029_tg": "telegram", "api_1": "painel", "cron_461a_1": "agenda"}, origens)
confere("só as do painel dá para responder",
        [x["id"] for x in r["conversas"] if x["pode_responder"]] == ["api_1"])
ex.acao_atena_conversas(c, {"origem": "painel", "quantas": 5})
confere("o filtro de origem vira o source do Hermes", "source=api_server" in VISTO["chamadas"][-1][1]
        and "limit=5" in VISTO["chamadas"][-1][1], VISTO["chamadas"][-1])
confere("origem desconhecida: 400", erro(ex.acao_atena_conversas, c, {"origem": "email"})[0] == 400)
confere("quantas fora do limite: 400", erro(ex.acao_atena_conversas, c, {"quantas": 1000})[0] == 400)

r = ex.acao_atena_conversa(c, {"conversa": "20261029_tg"})
m = r["mensagens"]
confere("a entrega da agenda aparece como da agenda, com o nome",
        m[0] == {"papel": "agenda", "nome": "bom-dia", "texto": "Bom dia! Servidor em ordem.", "quando": 10.0}, m[0])
confere("a sua mensagem, sem a senha", m[1]["papel"] == "voce" and "hunter2" not in m[1]["texto"], m[1])
passos = m[2]["passos"]
confere("o passo do terminal diz a ação do executor", passos[0]["detalhe"] == "executor: claude.tarefa", passos[0])
confere("o resultado sem o envelope do terminal", passos[0]["resultado"].startswith("{\"ok\": true"), passos[0])
confere("o trabalho do Claude Code que ela mandou vira um cartão", passos[0].get("trabalhos") == ["e4d647e7"], passos[0])
confere("outra ferramenta mostra os argumentos", passos[1]["ferramenta"] == "skill_view" and "lab" in passos[1]["detalhe"], passos[1])
confere("o resto: a resposta final, sem session_meta", [x["papel"] for x in m] == ["agenda", "voce", "atena", "atena", "atena"], m)
confere("das mais antigas para as mais novas", m[-2]["texto"].startswith("Mandei"))
confere("um comando que percorre uma lista de ações também diz quais",
        m[-1]["passos"][0]["detalhe"] == "executor: status.servicos, sistema.rede", m[-1]["passos"])
confere("o argumento sozinho aparece sem o JSON em volta", passos[1]["detalhe"] == "lab", passos[1])
confere("conversa inválida: 400", erro(ex.acao_atena_conversa, c, {"conversa": "../x"})[0] == 400)
status, msg = erro(ex.acao_atena_conversa, c, {"conversa": "nao_existe"})
confere("conversa que não existe: 404 com o motivo do Hermes", status == 404 and "Session not found" in msg, (status, msg))

# --- o chat, pelo socket do executor --------------------------------------------------------------------
ACOES = ["atena.falar", "atena.parar", "atena.aprovar"]
painel = token(ex, "painel", ACOES, c["zonas"], aprovar=[])
ligar(ex)


def falar(params):
    return pedir(ex, "POST", "/acao/atena.falar", painel, {"params": params, "origem": "painel"})


def esperar(id_, versao, segundos=5):
    return pedir(ex, "GET", f"/pedido/{id_}?esperar={segundos}&versao={versao}", painel)[1]["pedido"]


status, r = falar({"texto": "como está o servidor?"})
confere("atena.falar: 202 com o pedido (a resposta vem aos pedaços)", status == 202 and r["estado"] == "executando", (status, r))
id_, p = r["pedido"], {"versao": 0, "aprovacao": None}
inicio = time.monotonic()
while not p.get("aprovacao") and time.monotonic() - inicio < 5:
    p = esperar(id_, p["versao"])
confere("a conversa nova é do painel", p["conversa"] == "api_novo", p.get("conversa"))
confere("o texto chega aos pedaços, sem segredo", p["texto"].startswith("Vou conferir.") and "segredo123" not in p["texto"], p["texto"])
confere("o passo aparece rodando, com a ação do executor",
        p["passos"] == [{"ferramenta": "terminal", "detalhe": "executor: status.recursos", "estado": "rodando"}], p["passos"])
confere("o pedido de aprovação chega com as escolhas do Hermes",
        p["aprovacao"] == {"comando": "rm -rf /tmp/x", "descricao": "apagar pasta", "escolhas": ["once", "session", "deny"]}, p["aprovacao"])
antes = time.monotonic()
mesmo = esperar(id_, p["versao"], 1)
confere("versao: sem mudança, espera o tempo pedido", time.monotonic() - antes >= 0.9 and mesmo["versao"] == p["versao"])
status, r2 = falar({"texto": "e agora?", "conversa": "api_novo"})
confere("uma resposta por vez em cada conversa: 409", status == 409 and "respondendo" in r2["erro"], (status, r2))
status, r2 = pedir(ex, "POST", "/acao/atena.aprovar", painel, {"params": {"pedido": id_, "escolha": "always"}})
confere("escolha que o Hermes não ofereceu: 400", status == 400, (status, r2))
status, r2 = pedir(ex, "POST", "/acao/atena.aprovar", painel, {"params": {"pedido": id_, "escolha": "once"}})
confere("aprovar: a escolha vai ao run do Hermes", status == 200 and VISTO["aprovacao"] == "once", (status, r2))
while p["estado"] == "executando" and time.monotonic() - inicio < 10:
    p = esperar(id_, p["versao"])
confere("a resposta termina concluída, com o texto final", p["estado"] == "concluido"
        and p["resultado"] == {"conversa": "api_novo", "texto": "Tudo certo: CPU em 12%."}, p)
confere("os passos completos, com o resultado da ferramenta",
        p["passos"] == [{"ferramenta": "terminal", "detalhe": "executor: status.recursos", "resultado": "cpu 12%"}], p["passos"])
confere("sem aprovação pendurada no fim", p["aprovacao"] is None)
confere("a conversa fica livre", not ex.CONVERSANDO)
status, r2 = pedir(ex, "POST", "/acao/atena.aprovar", painel, {"params": {"pedido": id_, "escolha": "once"}})
confere("aprovar um pedido que terminou: 409", status == 409, (status, r2))

status, r = falar({"texto": "oi", "conversa": "20261029_tg"})
confere("responder numa conversa do Telegram: 409 (fica só para ler)", status == 409 and "só" in r["erro"], (status, r))
status, r = falar({"texto": "   "})
confere("texto vazio: 400", status == 400, (status, r))
status, r = falar({"texto": "x" * 9000})
confere("texto longo demais: 400", status == 400, (status, r))

CHAT["liberar"].clear()
CHAT["modo"] = "parar"
status, r = falar({"texto": "faz algo demorado", "conversa": "api_novo"})
id_, p = r["pedido"], {"versao": 0}
while not p.get("passos") and time.monotonic() - inicio < 15:
    p = esperar(id_, p["versao"])
status, r2 = pedir(ex, "POST", "/acao/atena.parar", painel, {"params": {"pedido": id_}})
confere("parar: o stop vai ao run do Hermes", status == 200 and VISTO["parar"] == "run_1", (status, r2))
while p["estado"] == "executando" and time.monotonic() - inicio < 20:
    p = esperar(id_, p["versao"])
confere("parado: o pedido fica cancelado", p["estado"] == "cancelado" and "parou" in p["erro"], p)
outro = token(ex, "outro", ACOES, c["zonas"], aprovar=[])
status, r2 = pedir(ex, "POST", "/acao/atena.parar", outro, {"params": {"pedido": id_}})
confere("o pedido de outro cliente não se para: 404", status == 404, (status, r2))

# --- a agenda dela ------------------------------------------------------------------------------------------
r = {a["nome"]: a for a in ex.acao_atena_agenda(c, {})["agendamentos"]}
ronda, remedio = r["ronda"], r["lembrete remédio"]
confere("agenda: a ronda com quando, próxima em segundos e o script",
        ronda["quando"] == "every 3m" and ronda["intervalo"] == 3 and abs(ronda["proxima"] - 1793366398.0) < 1
        and ronda["script"] == "ronda.py"
        and ronda["feitas"] == 3107 and ronda["protegido"], ronda)
confere("um lembrete pausado aparece pausado, sem segredo no erro",
        not remedio["ativo"] and remedio["tipo"] == "once" and "abc123" not in remedio["erro"] and not remedio["protegido"], remedio)
novo = ex.acao_atena_agendar(c, {"nome": "pagar a luz", "quando": "2026-11-05T09:00", "texto": "Lembre o dono", "vezes": 1})
confere("agendar: o Hermes recebe nome, quando, texto, entrega e vezes",
        novo["agendamento"]["nome"] == "pagar a luz" and JOBS["fff000aaa111"]["deliver"] == "telegram"
        and JOBS["fff000aaa111"]["repeat"]["times"] == 1, novo)
status, msg = erro(ex.acao_atena_agendar, c, {"nome": "x", "quando": "nunca", "texto": "y"})
confere("quando que o Hermes não entende: 400 com o motivo dele", status == 400 and "Invalid schedule" in msg, (status, msg))
for params, motivo in [({"nome": "", "quando": "every 2h", "texto": "y"}, "nome vazio"),
                       ({"nome": "x" * 70, "quando": "every 2h", "texto": "y"}, "nome longo"),
                       ({"nome": "x", "quando": "every 2h\nrm", "texto": "y"}, "quando com quebra de linha"),
                       ({"nome": "x", "quando": "every 2h", "texto": ""}, "sem texto"),
                       ({"nome": "x", "quando": "every 2h", "texto": "y", "entrega": "email"}, "entrega desconhecida"),
                       ({"nome": "x", "quando": "every 2h", "texto": "y", "vezes": 0}, "vezes zero")]:
    confere(f"agendar recusa {motivo}", erro(ex.acao_atena_agendar, c, params)[0] == 400)
r = ex.acao_atena_agendamento(c, {"id": "abc123def456", "fazer": "retomar"})
confere("retomar: POST resume", r["agendamento"]["ativo"] and ("POST", "/api/jobs/abc123def456/resume") in VISTO["chamadas"], r)
ex.acao_atena_agendamento(c, {"id": "461a4cd4d149", "fazer": "pausar"})
confere("pausar a ronda pode", JOBS["461a4cd4d149"]["state"] == "paused")
status, msg = erro(ex.acao_atena_agendamento, c, {"id": "461a4cd4d149", "fazer": "apagar"})
confere("apagar a ronda não (é do instalador)", status == 409 and "461a4cd4d149" in JOBS, (status, msg))
r = ex.acao_atena_agendamento(c, {"id": "abc123def456", "fazer": "apagar"})
confere("apagar um lembrete: DELETE", r == {"apagado": "abc123def456"} and "abc123def456" not in JOBS, r)
confere("id inválido: 400", erro(ex.acao_atena_agendamento, c, {"id": "../x", "fazer": "pausar"})[0] == 400)
confere("fazer desconhecido: 400", erro(ex.acao_atena_agendamento, c, {"id": "abc123def456", "fazer": "editar"})[0] == 400)

# --- o arquivo dos trabalhos antigos, o executor que reinicia, o token-acertar -------------------------
velho = time.time() - 8 * 86400
ex.ESTADO["pedidos"]["aaaa0001"] = {"id": "aaaa0001", "acao": "claude.tarefa", "cliente": "hermes", "zonas": ["lab"],
                                    "params": {"pedido": "jogo", "projeto": "nave"}, "estado": "concluido",
                                    "criado": velho, "segredo": "nao-pode", "resumo": "feito"}
ex.ESTADO["pedidos"]["aaaa0002"] = {"id": "aaaa0002", "acao": "servico.reiniciar", "cliente": "hermes",
                                    "params": {}, "estado": "concluido", "criado": velho}
ex.salvar_estado()
with open(f"{tmp}/claude-arquivo.jsonl") as f:
    arquivados = [json.loads(linha) for linha in f]
confere("os trabalhos do Claude Code de mais de uma semana vão para o arquivo, sem o segredo",
        [a["id"] for a in arquivados] == ["aaaa0001"] and "segredo" not in arquivados[0] and arquivados[0]["resumo"] == "feito", arquivados)
confere("e saem do histórico da semana, com os outros velhos",
        "aaaa0001" not in ex.ESTADO["pedidos"] and "aaaa0002" not in ex.ESTADO["pedidos"])
ex.ESTADO["pedidos"]["bbbb0001"] = {"id": "bbbb0001", "acao": "atena.falar", "cliente": "painel", "params": {},
                                    "estado": "executando", "criado": time.time()}
ex.pedidos_interrompidos()
confere("executor reiniciado no meio do chat: o pedido falha e diz para mandar de novo",
        ex.ESTADO["pedidos"]["bbbb0001"]["estado"] == "falhou" and "de novo" in ex.ESTADO["pedidos"]["bbbb0001"]["erro"])

with open(ex.TOKENS, "w") as f:
    json.dump({}, f)
t_painel = token(ex, "painel", ["status.servicos"], c["zonas"], aprovar=[])
t_atena = token(ex, "hermes", ["status.servicos", "atena.falar"], ["apps"])
token(ex, "outro", ["status.servicos"], ["apps"])
ex.lab_instalado = lambda: False
saida = io.StringIO()
argv, sys.argv = sys.argv, ["atena-executor", "token-acertar"]
with contextlib.redirect_stdout(saida):
    ex.principal()
sys.argv = argv
tokens = {t["cliente"]: t for t in ex.carregar_tokens().values()}
confere("token-acertar: o painel ganha as ações do perfil dele, com o mesmo token",
        set(tokens["painel"]["acoes"]) == set(ex.do_perfil("painel"))
        and ex.carregar_tokens()[ex.hash_token(t_painel)]["cliente"] == "painel", tokens["painel"]["acoes"])
confere("a Atena ganha as do perfil atena (sem o lab, sem as do lab), e as que já tinha ficam",
        set(tokens["hermes"]["acoes"]) == set(ex.do_perfil("atena")) | {"atena.falar"}
        and ex.carregar_tokens()[ex.hash_token(t_atena)]["zonas"] == ["apps"], tokens["hermes"])
confere("as aprovações ficam como estavam", tokens["painel"]["aprovar"] == [] and "aprovar" not in tokens["hermes"])
confere("um cliente sem perfil fica como estava", tokens["outro"]["acoes"] == ["status.servicos"])
confere("e diz o que acrescentou", "painel: + " in saida.getvalue() and "hermes: + " in saida.getvalue(), saida.getvalue())
saida = io.StringIO()
sys.argv = ["atena-executor", "token-acertar"]
with contextlib.redirect_stdout(saida):
    ex.principal()
sys.argv = argv
confere("de novo: nada a acrescentar", "já têm" in saida.getvalue(), saida.getvalue())
fim()
