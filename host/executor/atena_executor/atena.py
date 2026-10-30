"""A Atena (o Hermes) no painel: as conversas dela, a agenda e o chat, pela API interna do Hermes.

A API ouve só na rede svc-atena (HERMES_API), onde não há outro container: chega nela quem está no
servidor e tem a chave (API_SERVER_KEY, no .env do Hermes, que só o executor lê). Estas ações são do
perfil painel; a Atena não as tem.
O chat (atena.falar) roda numa thread: o pedido junta o texto que chega aos pedaços, os passos (as
ferramentas que ela usa) e o pedido de aprovação de um comando perigoso, e o painel acompanha com
GET /pedido/<id>?esperar=s&versao=n, que volta a cada mudança. As conversas do Telegram e da agenda
ficam só para ler: duas pontas escrevendo na mesma conversa embaralhariam as duas."""

import datetime
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

from .base import Erro, log
from .pedidos import ESTADO, TRAVA, andamento, mudar
from .segredos import curto, ocultar


HERMES_API = "http://10.10.252.2:8642"   # a rede svc-atena, do compose do Hermes
HERMES_ENV = "/srv/agents/hermes/.env"
ESPERA_API = 15           # uma consulta à API
ESPERA_CHAT = 300         # nenhum sinal do Hermes por 5 min (ele manda um a cada poucos segundos): caiu
MAX_TEXTO = 8000          # uma mensagem sua
MAX_PROMPT = 4000         # o texto de um agendamento
MAX_RESULTADO = 600       # o que aparece do resultado de cada ferramenta
# de onde veio a conversa: o nome que o Hermes dá → o que o painel mostra
ORIGENS = {"telegram": "telegram", "api_server": "painel", "cron": "agenda", "oneshot": "terminal",
           "cli": "terminal", "whatsapp": "whatsapp"}
PROTEGIDOS = {"ronda", "bom-dia"}   # os agendamentos do instalador: pausar pode, apagar não
ESCOLHAS = ("once", "session", "always", "deny")   # aprovar um comando: só agora, na conversa, sempre, não
ID_CONVERSA = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
ID_AGENDAMENTO = re.compile(r"[0-9a-f]{6,32}")
ACAO_NO_COMANDO = re.compile(r"(?:/acao/|acao\.py\s+)([a-z]+(?:\.[a-z]+)+)")
ACAO_NA_RESPOSTA = re.compile(r'\\*"acao\\*":\s*\\*"([a-z]+(?:\.[a-z]+)+)\\*"(?:,\s*\\*"pedido\\*":\s*\\*"([0-9a-f]{8}))?')
CONVERSANDO = set()       # conversas com uma resposta em andamento: uma por vez em cada


def chave():
    """A chave da API, do .env do Hermes (o instalador a cria; o Hermes só liga a API com ela)."""
    try:
        with open(HERMES_ENV) as f:
            for linha in f:
                if linha.startswith("API_SERVER_KEY="):
                    valor = linha.split("=", 1)[1].strip().strip("\"'")
                    if valor:
                        return valor
    except OSError:
        pass
    raise Erro(503, "a API da Atena não está ligada (falta API_SERVER_KEY no .env do Hermes); "
                    "rode de novo o instalador com --hermes")


def motivo(e):
    """A mensagem de erro que o Hermes mandou, nos dois formatos dele."""
    try:
        corpo = json.loads(e.read() or b"{}")
        erro = corpo.get("error", corpo)
        return str(erro.get("message") if isinstance(erro, dict) else erro)[:300]
    except (OSError, ValueError, AttributeError):
        return f"HTTP {e.code}"


def pedido_api(metodo, rota, corpo=None):
    return urllib.request.Request(HERMES_API + rota, method=metodo,
                                  data=json.dumps(corpo).encode() if corpo is not None else None,
                                  headers={"Authorization": "Bearer " + chave(), "Content-Type": "application/json"})


def api(metodo, rota, corpo=None):
    """A resposta (JSON) de uma chamada à API do Hermes; o erro dela vira um Erro com o motivo."""
    try:
        with urllib.request.urlopen(pedido_api(metodo, rota, corpo), timeout=ESPERA_API) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise Erro(e.code if e.code in (400, 404, 409, 429) else 502, f"a Atena recusou: {motivo(e)}") from None
    except (OSError, ValueError) as e:
        raise Erro(503, f"a Atena não respondeu ({e}); o container hermes está no ar?") from None


def q(texto):
    return urllib.parse.quote(texto, safe="")


def numero(params, nome, padrao, minimo, maximo):
    valor = params.get(nome, padrao)
    if not isinstance(valor, int) or isinstance(valor, bool) or not minimo <= valor <= maximo:
        raise Erro(400, f"{nome} deve ser um número de {minimo} a {maximo}")
    return valor


def texto_de(conteudo):
    """O texto de uma mensagem: o Hermes guarda texto ou uma lista de partes (texto, imagem, áudio)."""
    if isinstance(conteudo, list):
        return "\n".join(p.get("text", "") for p in conteudo if isinstance(p, dict) and p.get("type") == "text")
    return conteudo if isinstance(conteudo, str) else ""


# --- conversas -----------------------------------------------------------------------------------------

def conversa_id(params):
    valor = params.get("conversa")
    if not isinstance(valor, str) or not ID_CONVERSA.fullmatch(valor):
        raise Erro(400, "conversa inválida")
    return valor


def resumo_conversa(s):
    return {"id": s["id"], "origem": ORIGENS.get(s.get("source"), s.get("source") or "?"),
            "titulo": curto(s.get("title") or "", 120), "previa": curto(s.get("preview") or "", 160),
            "comecou": s.get("started_at"), "ultima": s.get("last_active") or s.get("ended_at") or s.get("started_at"),
            "mensagens": s.get("message_count") or 0, "ferramentas": s.get("tool_call_count") or 0,
            "custo": s.get("estimated_cost_usd"), "modelo": s.get("model"), "encerrada": s.get("end_reason"),
            "pode_responder": s.get("source") == "api_server"}


def acao_atena_conversas(cliente, params):
    """As conversas da Atena, da mais recente para a mais antiga (Telegram, painel, agenda, terminal)."""
    quantas, pular = numero(params, "quantas", 30, 1, 100), numero(params, "pular", 0, 0, 100000)
    origem = params.get("origem")
    fonte = {v: k for k, v in ORIGENS.items() if k != "cli"}.get(origem) if origem else None
    if origem is not None and fonte is None:
        raise Erro(400, "origem deve ser telegram, painel, agenda, terminal ou whatsapp")
    resposta = api("GET", f"/api/sessions?limit={quantas}&offset={pular}" + (f"&source={fonte}" if fonte else ""))
    conversas = [resumo_conversa(s) for s in resposta.get("data", []) if not s.get("is_internal_child")]
    return {"conversas": conversas, "mais": bool(resposta.get("has_more"))}


def detalhe_ferramenta(nome, args):
    """Uma linha sobre o que a ferramenta fez: a ação do executor, se for uma; senão os argumentos."""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            pass
    texto = args.get("command", "") if isinstance(args, dict) and nome == "terminal" else ""
    acoes = ACAO_NO_COMANDO.findall(texto)
    if acoes:
        return "executor: " + ", ".join(dict.fromkeys(acoes))
    return curto(args if args not in (None, "", {}) else "", 160)


def passo(nome, args):
    return {"ferramenta": nome or "?", "detalhe": detalhe_ferramenta(nome, args)}


def resultado_ferramenta(conteudo, p):
    """Junta ao passo o resultado da ferramenta: um pedaço do texto e os trabalhos do Claude Code que ela
    mandou (o pedido de claude.tarefa, que o painel mostra como um cartão)."""
    texto = texto_de(conteudo)
    for acao, pedido in ACAO_NA_RESPOSTA.findall(texto):
        if acao == "claude.tarefa" and pedido:
            p.setdefault("trabalhos", []).append(pedido)
    try:   # o terminal do Hermes devolve {"output": "..."}: o que interessa é a saída
        saida = json.loads(texto)
        texto = saida.get("output", texto) if isinstance(saida, dict) else texto
    except ValueError:
        pass
    p["resultado"] = curto(texto if isinstance(texto, str) else json.dumps(texto, ensure_ascii=False), MAX_RESULTADO)


def mensagens(brutas):
    """As mensagens do Hermes como o painel mostra: as suas, as da Atena com os passos (cada ferramenta com
    o resultado) e as entregas da agenda. Sem segredos."""
    saida, passos = [], {}
    for m in sorted(brutas, key=lambda m: (m.get("timestamp") or 0, m.get("id") or 0)):
        papel, texto = m.get("role"), ocultar(texto_de(m.get("content")))
        if papel == "user":
            agenda = re.match(r"\[Cron delivery: ([^\]]+)\]\n?", texto)
            if agenda:
                saida.append({"papel": "agenda", "nome": agenda.group(1), "texto": texto[agenda.end():], "quando": m.get("timestamp")})
            else:
                saida.append({"papel": "voce", "texto": texto, "quando": m.get("timestamp")})
        elif papel == "assistant":
            chamadas = m.get("tool_calls") or []
            if isinstance(chamadas, str):
                try:
                    chamadas = json.loads(chamadas)
                except ValueError:
                    chamadas = []
            novos = []
            for c in chamadas if isinstance(chamadas, list) else []:
                if not isinstance(c, dict):
                    continue
                funcao = c.get("function") or {}
                p = passo(funcao.get("name"), funcao.get("arguments"))
                passos[c.get("id")] = p
                novos.append(p)
            if texto.strip() or novos:
                saida.append({"papel": "atena", "texto": texto, "passos": novos, "quando": m.get("timestamp")})
        elif papel == "tool":
            p = passos.get(m.get("tool_call_id"))
            if p is None:   # o resultado chegou sem a chamada (a conversa começa no meio)
                p = passo(m.get("tool_name"), None)
                saida.append({"papel": "atena", "texto": "", "passos": [p], "quando": m.get("timestamp")})
            resultado_ferramenta(m.get("content"), p)
    return saida


def acao_atena_conversa(cliente, params):
    """Uma conversa: as últimas mensagens (quantas, até 500), da mais antiga para a mais nova."""
    sid, quantas = conversa_id(params), numero(params, "quantas", 200, 1, 500)
    s = api("GET", f"/api/sessions/{q(sid)}")["session"]
    brutas = api("GET", f"/api/sessions/{q(sid)}/messages?limit={quantas}&order=latest").get("data", [])
    return {"conversa": resumo_conversa(s), "mensagens": mensagens(brutas), "completa": len(brutas) < quantas}


# --- o chat ----------------------------------------------------------------------------------------------

def preparar_atena_falar(cliente, params):
    texto = params.get("texto")
    if not isinstance(texto, str) or not texto.strip():
        raise Erro(400, "falta o texto")
    if len(texto) > MAX_TEXTO:
        raise Erro(400, f"texto longo demais (até {MAX_TEXTO} caracteres)")
    if params.get("conversa") is not None:
        conversa_id(params)
    return "conversar com a Atena", curto(texto, 300)


def acao_atena_falar(p):
    """Manda a mensagem numa conversa do painel (ou numa nova) e acompanha a resposta numa thread."""
    conversa = p["params"].get("conversa")
    if conversa:
        s = api("GET", f"/api/sessions/{q(conversa)}")["session"]
        if s.get("source") != "api_server":
            raise Erro(409, "esta conversa não é do painel (é do Telegram ou da agenda): aqui ela fica só "
                            "para ler; comece uma nova")
    else:
        conversa = api("POST", "/api/sessions", {})["session"]["id"]
    with TRAVA:
        if conversa in CONVERSANDO:
            raise Erro(409, "a Atena ainda está respondendo nesta conversa; espere ou pare a resposta")
        CONVERSANDO.add(conversa)
    andamento(p, conversa=conversa, texto="", passos=[])
    threading.Thread(target=conversar, args=(p, conversa), daemon=True).start()
    return None   # o pedido fica em "executando": GET /pedido/<id>?esperar=s&versao=n


def eventos_sse(resposta):
    """(evento, dados) de cada mensagem do SSE do Hermes; as linhas de keepalive (": ...") ficam de fora."""
    evento, dados = None, []
    for bruta in resposta:
        linha = bruta.decode("utf-8", "replace").rstrip("\r\n")
        if not linha:
            if dados:
                try:
                    yield evento, json.loads("\n".join(dados))
                except ValueError:
                    pass
            evento, dados = None, []
        elif linha.startswith("event:"):
            evento = linha[6:].strip()
        elif linha.startswith("data:"):
            dados.append(linha[5:].strip())


def conversar(p, conversa):
    texto, passos, estado, erro = "", [], "falhou", None
    try:
        pedido = pedido_api("POST", f"/api/sessions/{q(conversa)}/chat/stream", {"message": p["params"]["texto"]})
        with urllib.request.urlopen(pedido, timeout=ESPERA_CHAT) as r:
            for evento, d in eventos_sse(r):
                if evento == "run.started":
                    andamento(p, run=d.get("run_id"))
                elif evento == "assistant.delta":
                    texto += d.get("delta") or ""
                    andamento(p, texto=ocultar(texto))
                elif evento == "assistant.commentary" and not d.get("already_streamed"):
                    texto += (d.get("text") or "") + "\n\n"
                    andamento(p, texto=ocultar(texto))
                elif evento == "tool.started":
                    passos.append({**passo(d.get("tool_name"), d.get("args") or d.get("preview")), "estado": "rodando"})
                    andamento(p, passos=[dict(x) for x in passos], aprovacao=None)
                elif evento in ("tool.completed", "tool.failed"):
                    rodando = [x for x in passos if x["estado"] == "rodando" and x["ferramenta"] == d.get("tool_name")]
                    if rodando:
                        rodando[0]["estado"] = "ok" if evento == "tool.completed" else "falhou"
                    andamento(p, passos=[dict(x) for x in passos], aprovacao=None)
                elif evento == "approval.request":
                    andamento(p, aprovacao={"comando": curto(d.get("command") or "", 500),
                                            "descricao": ocultar(str(d.get("description") or "")),
                                            "escolhas": [c for c in d.get("choices") or [] if c in ESCOLHAS]})
                elif evento == "assistant.completed":
                    texto = d.get("content") or texto
                elif evento in ("run.completed", "run.failed", "run.cancelled"):
                    estado = {"run.completed": "concluido", "run.cancelled": "cancelado"}.get(evento, "falhou")
                    if estado == "falhou":
                        erro = d.get("error") or "a Atena parou no meio da resposta"
                    # os passos completos, com o resultado de cada ferramenta (e os trabalhos do Claude Code)
                    completos = [x for m in mensagens(d.get("messages") or []) if m["papel"] == "atena"
                                 for x in m["passos"]]
                    if completos:
                        passos = completos
                elif evento == "error":
                    erro = d.get("message") or "erro na Atena"
                elif evento == "done":
                    break
    except urllib.error.HTTPError as e:
        erro = f"a Atena recusou: {motivo(e)}"
    except (OSError, ValueError, Erro) as e:
        erro = f"a conversa com a Atena caiu: {e}"
    except Exception as e:
        erro = "erro interno; veja journalctl -u atena-executor"
        log(evento="erro no chat com a Atena", pedido=p["id"], erro=repr(e))
    finally:
        with TRAVA:
            CONVERSANDO.discard(conversa)
    campos = {"texto": ocultar(texto), "passos": passos, "aprovacao": None}
    if estado == "concluido" and erro is None:
        mudar(p, estado="concluido", resultado={"conversa": conversa, "texto": ocultar(texto)}, **campos)
    elif estado == "cancelado":
        mudar(p, estado="cancelado", erro="você parou a resposta", **campos)
    else:
        mudar(p, estado="falhou", erro=curto(erro or "a Atena parou no meio da resposta", 500), **campos)



def chat_do_cliente(cliente, params):
    """O pedido de atena.falar ainda respondendo, deste cliente."""
    id_ = params.get("pedido")
    with TRAVA:
        p = ESTADO["pedidos"].get(id_) if isinstance(id_, str) else None
        if not p or p["acao"] != "atena.falar" or p["cliente"] != cliente["cliente"]:
            raise Erro(404, "pedido não encontrado")
        if p["estado"] != "executando" or not p.get("run"):
            raise Erro(409, "a Atena não está respondendo neste pedido")
        return p


def acao_atena_parar(cliente, params):
    """Para a resposta da Atena no meio (pedido de atena.falar)."""
    p = chat_do_cliente(cliente, params)
    api("POST", f"/v1/runs/{q(p['run'])}/stop", {})
    return {"parando": p["id"]}


def acao_atena_aprovar(cliente, params):
    """Responde ao pedido de aprovação de um comando que a Atena quer rodar no meio do chat (pedido,
    escolha: once = só desta vez, session = nesta conversa, always = sempre, deny = não)."""
    p = chat_do_cliente(cliente, params)
    escolha, aprovacao = params.get("escolha"), p.get("aprovacao")
    if not aprovacao:
        raise Erro(409, "a Atena não está esperando aprovação neste pedido")
    if escolha not in aprovacao["escolhas"]:
        raise Erro(400, "escolha deve ser " + ", ".join(aprovacao["escolhas"]))
    api("POST", f"/v1/runs/{q(p['run'])}/approval", {"choice": escolha})
    andamento(p, aprovacao=None)
    log(evento="aprovação no chat", pedido=p["id"], escolha=escolha)
    return {"respondido": escolha}


# --- a agenda dela ---------------------------------------------------------------------------------------

def instante(iso):
    """Uma data do Hermes (ISO, com fuso) em segundos, como as das conversas."""
    try:
        return datetime.datetime.fromisoformat(iso).timestamp() if iso else None
    except (TypeError, ValueError):
        return None


def agendamento(j):
    repetir = j.get("repeat") or {}
    return {"id": j.get("id"), "nome": j.get("name") or "", "quando": j.get("schedule_display") or "",
            "tipo": (j.get("schedule") or {}).get("kind"), "proxima": instante(j.get("next_run_at")),
            "ultima": instante(j.get("last_run_at")), "resultado": j.get("last_status"),
            "erro": curto(j["last_error"], 300) if j.get("last_error") else None,
            "ativo": bool(j.get("enabled")) and j.get("state") != "paused", "estado": j.get("state"),
            "entrega": j.get("deliver"), "texto": curto(j.get("prompt") or "", 600),
            "script": j.get("script") or j.get("monitor_script"), "sem_ia": bool(j.get("no_agent")),
            "vezes": repetir.get("times"), "feitas": repetir.get("completed"),
            "protegido": j.get("name") in PROTEGIDOS}


def acao_atena_agenda(cliente, params):
    """Os agendamentos da Atena (lembretes, a ronda, o bom-dia), os pausados também."""
    jobs = api("GET", "/api/jobs?include_disabled=true").get("jobs", [])
    return {"agendamentos": [agendamento(j) for j in jobs]}


def acao_atena_agendar(cliente, params):
    """Um agendamento novo da Atena: nome; quando = data e hora (2026-11-03T15:00, uma vez), cron
    (0 8 * * *) ou intervalo (every 2h); texto = o que ela faz na hora; entrega = telegram ou ntfy;
    vezes = quantas vezes repete (sem: sempre)."""
    nome, quando, texto = params.get("nome"), params.get("quando"), params.get("texto")
    entrega, vezes = params.get("entrega", "telegram"), params.get("vezes")
    if not isinstance(nome, str) or not 1 <= len(nome.strip()) <= 64 or "\n" in nome:
        raise Erro(400, "nome deve ter de 1 a 64 caracteres, numa linha")
    if not isinstance(quando, str) or not 1 <= len(quando.strip()) <= 64 or "\n" in quando:
        raise Erro(400, "quando deve ser uma data e hora (2026-11-03T15:00), um cron (0 8 * * *) ou um intervalo (every 2h)")
    if not isinstance(texto, str) or not texto.strip() or len(texto) > MAX_PROMPT:
        raise Erro(400, f"texto deve dizer o que a Atena faz na hora (até {MAX_PROMPT} caracteres)")
    if entrega not in ("telegram", "ntfy"):
        raise Erro(400, "entrega deve ser telegram ou ntfy")
    corpo: dict = {"name": nome.strip(), "schedule": quando.strip(), "prompt": texto, "deliver": entrega}
    if vezes is not None:
        corpo["repeat"] = numero(params, "vezes", 1, 1, 1000)
    return {"agendamento": agendamento(api("POST", "/api/jobs", corpo).get("job") or {})}


def acao_atena_agendamento(cliente, params):
    """Muda um agendamento da Atena (id, fazer: pausar, retomar, rodar = agora, apagar)."""
    id_, fazer = params.get("id"), params.get("fazer")
    if not isinstance(id_, str) or not ID_AGENDAMENTO.fullmatch(id_):
        raise Erro(400, "id inválido (veja atena.agenda)")
    if fazer not in ("pausar", "retomar", "rodar", "apagar"):
        raise Erro(400, "fazer deve ser pausar, retomar, rodar ou apagar")
    if fazer == "apagar":
        nome = (api("GET", f"/api/jobs/{q(id_)}").get("job") or {}).get("name")
        if nome in PROTEGIDOS:
            raise Erro(409, f"o agendamento {nome} é do instalador: pause em vez de apagar")
        api("DELETE", f"/api/jobs/{q(id_)}")
        return {"apagado": id_}
    rota = {"pausar": "pause", "retomar": "resume", "rodar": "run"}[fazer]
    resposta = api("POST", f"/api/jobs/{q(id_)}/{rota}", {})
    return {"agendamento": agendamento(resposta.get("job") or {})} if resposta.get("job") else {"ok": True}
