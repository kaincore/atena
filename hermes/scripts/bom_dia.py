"""Bom-dia da Atena, sem IA: o cron do Hermes roda às 8h (--no-agent) e manda esta saída no Telegram.

Lê o servidor pelo executor, como a ronda, e diz em poucas linhas como ele amanheceu: os containers,
as temperaturas, o gasto de IA do mês e o Claude Code da noite. Não chama nenhum modelo, então chega
mesmo com a IA fora do ar (e diz isso). Cada parte que falha vira uma linha dizendo o quê.
"""
import datetime as dt
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acao import acao  # noqa: E402  (o cliente do executor, ao lado)

LITELLM = "http://litellm:4000/health/readiness"   # a IA da Atena; responde sem chamar nenhum modelo
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro")


def consulta(nome):
    status, r = acao(nome, origem="bom-dia")
    if status != 200 or not r.get("ok"):
        raise RuntimeError(r.get("erro") or f"HTTP {status}")
    return r["resultado"]


def dolar(valor):
    return f"US$ {valor:.2f}".replace(".", ",")


def servidor():
    servicos = consulta("status.servicos")
    ruins = [s for s in servicos if s.get("estado") != "running" or "unhealthy" in (s.get("status") or "")]
    if not ruins:
        return f"Servidor: tudo em ordem, {len(servicos)} containers no ar."
    nomes = ", ".join(f"{s.get('container')} ({'doente' if s.get('estado') == 'running' else s.get('estado')})"
                      for s in ruins[:5])
    return f"Servidor: {len(ruins)} de {len(servicos)} containers pedem atenção: {nomes}."


def temperaturas():
    s = consulta("sistema.sensores")
    partes = [f"{rotulo} {round(t)} °C" for chave, rotulo in (("cpu", "CPU"), ("gpu", "GPU"), ("nvme", "NVMe"))
              if (t := (s.get(chave) or {}).get("temperatura_c")) is not None]
    if not partes:
        return None
    linha = "Temperaturas: " + ", ".join(partes) + "."
    if s.get("avaliacao") not in (None, "normal"):
        linha += f" Atenção: {s['avaliacao']}."
    return linha


def gasto():
    g = consulta("gasto.api")
    mes = MESES[int(g["mes"][5:7]) - 1]
    linha = f"IA em {mes}: {dolar(g.get('total_usd') or 0)}"
    haiku = next((m for m in g.get("por_modelo", []) if m.get("modelo") == "haiku"), None)
    if haiku and haiku.get("teto_usd"):
        linha += f", com o Haiku em {round(100 * haiku['gasto_usd'] / haiku['teto_usd'])}% do teto de {dolar(haiku['teto_usd'])}"
    return linha + "."


def claude_code(agora):
    try:
        trabalhos = consulta("claude.trabalhos").get("trabalhos") or []
    except RuntimeError:
        return None   # servidor sem o lab, ou token sem o Claude Code
    rodando = [t for t in trabalhos if t.get("estado") in ("planejando", "executando")]
    desde = (agora - dt.timedelta(hours=16)).strftime("%Y-%m-%d %H:%M")
    noite = [t for t in trabalhos if t not in rodando and (t.get("criado") or "") >= desde]
    partes = []
    if rodando:
        partes.append(f"{len(rodando)} rodando ({', '.join(t.get('projeto') or '?' for t in rodando)})")
    if noite:
        partes.append("da noite: " + ", ".join(f"{t.get('projeto') or '?'} ({t.get('estado')})" for t in noite))
    return "Claude Code: " + "; ".join(partes) + "." if partes else None


def litellm_pronto():
    try:
        with urllib.request.urlopen(LITELLM, timeout=10) as r:
            return r.status == 200
    except OSError:
        return False


def montar(agora):
    linhas = [f"Bom dia! {DIAS[agora.weekday()].capitalize()}, {agora.day} de {MESES[agora.month - 1]}."]
    if not litellm_pronto():
        linhas.append("A IA da Atena (LiteLLM) não está respondendo agora: ela não conversa até ele voltar.")
    try:
        linhas.append(servidor())
    except (OSError, RuntimeError, ValueError) as e:
        linhas.append(f"Não consegui falar com o executor ({type(e).__name__}); a ronda avisa se houver algo.")
        return "\n".join(linhas)
    for nome, parte in (("as temperaturas", temperaturas), ("o gasto de IA", gasto),
                        ("o Claude Code", lambda: claude_code(agora))):
        try:
            linha = parte()
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as e:
            linha = f"Não consegui ler {nome} ({type(e).__name__})."
        if linha:
            linhas.append(linha)
    return "\n".join(linhas)


if __name__ == "__main__":
    print(montar(dt.datetime.now()))
