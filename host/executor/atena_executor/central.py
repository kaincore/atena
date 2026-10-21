"""Central do painel: aprovacoes.lista mostra os pedidos que esperam o dono, de todos os clientes
(só os das zonas de quem pergunta), com o texto que foi ao celular; aprovacoes.decidir aprova,
recusa ou responde a pergunta, como o toque no celular faria, mas nunca um pedido do próprio
cliente; atividade.lista lê o registro do executor (cada pedido, cada decisão e os eventos)."""

import json
import re
import subprocess
import time
import urllib.error

from .base import Erro
from .celular import ntfy
from .claude import ESPERA_PERGUNTA
from .pedidos import ESTADO, TRAVA, decidir, no_alcance
from .segredos import curto, ocultar


LIMITE_ATIVIDADE = 1000   # linhas do registro numa consulta


def pendente(p):
    """O que o dono precisa para decidir: quem pediu, o quê e o texto que foi ao celular."""
    item = {"id": p["id"], "cliente": p["cliente"], "acao": p["acao"], "titulo": p.get("titulo"),
            "origem": p.get("origem"), "criado": p["criado"],
            "params": {k: curto(v) for k, v in (p.get("params") or {}).items()
                       if k not in ("chave", "nonce")}}
    if p["acao"] == "claude.pergunta":
        params = p["params"]
        return {**item, "tipo": "pergunta", "pergunta": params.get("pergunta"),
                "opcoes": params.get("opcoes") or [], "por_que": params.get("por_que"),
                "projeto": params.get("projeto"), "expira": p["criado"] + ESPERA_PERGUNTA}
    return {**item, "tipo": "aprovacao", "texto": p.get("aviso") or "", "expira": p.get("expira")}


def acao_aprovacoes_lista(cliente, params):
    agora = time.time()
    with TRAVA:
        todos = [p for p in ESTADO["pedidos"].values() if no_alcance(cliente, p)]
        esperando = [pendente(p) for p in todos
                     if (p["estado"] == "aguardando" and p.get("expira", 0) > agora)
                     or (p["estado"] == "perguntando" and p["criado"] + ESPERA_PERGUNTA > agora)]
        passaram = sorted((p for p in todos if p["estado"] not in ("aguardando", "perguntando")
                           and (p.get("aviso") or p["acao"] in ("claude.permissao", "claude.pergunta"))),
                          key=lambda p: p.get("atualizado", p["criado"]), reverse=True)[:15]
        recentes = [{"id": p["id"], "cliente": p["cliente"], "acao": p["acao"], "titulo": p.get("titulo"),
                     "estado": p["estado"], "quando": p.get("atualizado", p["criado"]),
                     "por": p.get("decidido_por") or p.get("quem"), "erro": p.get("erro")}
                    for p in passaram]
    return {"pendentes": sorted(esperando, key=lambda x: x["criado"]), "recentes": recentes, "agora": agora}


def acao_aprovacoes_decidir(cliente, params):
    alvo, decisao, resposta = params.get("pedido"), params.get("decisao"), params.get("resposta")
    if decisao not in ("aprovar", "recusar", "responder"):
        raise Erro(400, "decisao deve ser aprovar, recusar ou responder")
    if decisao == "responder" and (not isinstance(resposta, str) or not 1 <= len(resposta.strip()) <= 2000):
        raise Erro(400, "resposta deve ter de 1 a 2000 caracteres")
    with TRAVA:
        p = ESTADO["pedidos"].get(alvo) if isinstance(alvo, str) else None
        if not p or not no_alcance(cliente, p):
            raise Erro(404, "pedido não encontrado (veja aprovacoes.lista)")
        if p["cliente"] == cliente["cliente"] and p["acao"] not in ("claude.permissao", "claude.pergunta"):
            raise Erro(403, "um cliente não decide sobre os próprios pedidos")
        pergunta = p["acao"] == "claude.pergunta"
        if pergunta != (decisao == "responder"):
            raise Erro(400, "pergunta do Claude Code se responde (decisao responder); o resto, aprovar ou recusar")
        if p["estado"] != ("perguntando" if pergunta else "aguardando"):
            raise Erro(409, f"esse pedido já foi decidido (estado: {p['estado']})")
        resultado = decidir(p, decisao, cliente["cliente"], resposta.strip() if pergunta else None)
    return {"pedido": alvo, "resultado": resultado}


def ler_registro(quantas):
    """As últimas linhas do registro do executor, em JSON do journal (uma entrada por linha)."""
    r = subprocess.run(["journalctl", "-u", "atena-executor", "-o", "json", "--output-fields=MESSAGE",
                        "--no-pager", "-n", str(quantas)], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise Erro(500, "não consegui ler o registro do executor")
    return r.stdout


def acao_atividade_lista(cliente, params):
    """O registro do executor no journal, do mais novo para o mais velho."""
    linhas, quem, so_erros = params.get("linhas", 200), params.get("cliente"), params.get("so_erros", False)
    if not isinstance(linhas, int) or not 1 <= linhas <= LIMITE_ATIVIDADE:
        raise Erro(400, f"linhas deve ser um número de 1 a {LIMITE_ATIVIDADE}")
    if quem is not None and (not isinstance(quem, str) or not re.fullmatch(r"[a-z0-9_-]{1,32}", quem)):
        raise Erro(400, "cliente inválido")
    if not isinstance(so_erros, bool):
        raise Erro(400, "so_erros deve ser true ou false")
    filtrando = quem is not None or so_erros
    itens = []
    for bruta in reversed(ler_registro(LIMITE_ATIVIDADE * 5 if filtrando else linhas).splitlines()):
        try:
            entrada = json.loads(bruta)
            mensagem = entrada.get("MESSAGE")
            quando = int(entrada["__REALTIME_TIMESTAMP"]) / 1e6
        except (ValueError, KeyError, TypeError):
            continue
        if not isinstance(mensagem, str):   # mensagem binária no journal
            continue
        try:
            campos = json.loads(mensagem)
        except ValueError:
            campos = None
        if not isinstance(campos, dict):   # linha que não é do log(): erro do Python, aviso do systemd
            campos = {"evento": curto(mensagem, 300)}
        item = {"quando": quando}
        for chave in ("cliente", "origem", "acao", "evento", "pedido", "decisao", "por", "ok", "segundos",
                      "aprovacao", "trabalho", "ferramenta", "quem"):
            if campos.get(chave) is not None:
                item[chave] = campos[chave] if isinstance(campos[chave], (bool, int, float)) else curto(campos[chave])
        if campos.get("erro") is not None:
            item["erro"] = curto(campos["erro"], 300)
        if isinstance(campos.get("params"), dict):
            item["params"] = {k: curto(v) for k, v in campos["params"].items()}
        if quem is not None and item.get("cliente") != quem:
            continue
        if so_erros and item.get("ok") is not False and "erro" not in item:
            continue
        itens.append(item)
        if len(itens) >= linhas:
            break
    return {"itens": itens}


def acao_aviso_celular(cliente, params):
    """Aviso no celular do dono, pelo ntfy. O painel não tem rede: os agendamentos dele avisam por aqui."""
    titulo, texto = params.get("titulo"), params.get("texto", "")
    if not isinstance(titulo, str) or not 1 <= len(titulo.strip()) <= 120:
        raise Erro(400, "titulo deve ter de 1 a 120 caracteres")
    if not isinstance(texto, str) or len(texto) > 3000:
        raise Erro(400, "texto deve ter até 3000 caracteres")
    try:
        ntfy("aprovacoes", ocultar(titulo.strip()), ocultar(texto) or titulo.strip(), tags=["calendar"])
    except (OSError, urllib.error.URLError) as e:
        raise Erro(502, f"o ntfy não recebeu o aviso: {e}")
    return {"avisado": True}
