"""O histórico do Claude Code para o painel: claude.historico (a semana do executor e o arquivo) e
claude.registro (a conversa inteira de um trabalho, resumida e sem segredos)."""
import json
import os
import time

from comum import confere, erro, executor, fim

ex, tmp, avisos = executor()
os.makedirs(f"{tmp}/registros")
painel = {"cliente": "painel", "zonas": ["core", "apps", "ai", "agents", "lab"], "acoes": ["aprovacoes.decidir"]}
atena = {"cliente": "hermes", "zonas": ["apps", "ai", "agents", "lab", "core"], "acoes": []}
agora = time.time()


def trabalho(id_, criado, cliente="hermes", **extra):
    return {"id": id_, "acao": "claude.tarefa", "cliente": cliente, "zonas": ["lab"], "estado": "concluido",
            "fase": "executar", "criado": criado, "atualizado": criado + 60, "sessao": "s-" + id_,
            "params": {"pedido": f"pedido {id_}", "projeto": "nave", "conta": "pessoal", "somente_plano": False},
            **extra}


for i in range(3):   # a semana do executor
    p = trabalho(f"0000000{i}", agora - i * 3600, resumo="feito; token=abc999", commits=[{"x": 1}] * i)
    ex.ESTADO["pedidos"][p["id"]] = p
ex.ESTADO["pedidos"]["00000009"] = {**trabalho("00000009", agora - 100), "acao": "servico.reiniciar"}
with open(f"{tmp}/claude-arquivo.jsonl", "w") as f:   # o arquivo: mais velhos, um repetido e uma linha cortada
    for i in range(3, 6):
        f.write(json.dumps(trabalho(f"0000000{i}", agora - 9 * 86400 - i)) + "\n")
    f.write(json.dumps(trabalho("00000000", agora - 9 * 86400)) + "\n")
    f.write('{"id": "cortado", "acao": "claude.tar')
open(f"{tmp}/registros/00000000.executar.jsonl", "w").close()

r = ex.acao_claude_historico(painel, {})
ids = [t["id"] for t in r["trabalhos"]]
confere("historico: a semana e o arquivo, do mais novo ao mais velho, sem repetir nem a linha cortada",
        ids == ["00000000", "00000001", "00000002", "00000003", "00000004", "00000005"] and not r["mais"], ids)
t0 = r["trabalhos"][0]
confere("cada trabalho: pedido, projeto, conta, commits, resumo sem segredo",
        t0["pedido"] == "pedido 00000000" and t0["projeto"] == "nave" and t0["conta"] == "pessoal"
        and r["trabalhos"][2]["commits"] == 2 and "abc999" not in r["trabalhos"][1]["resumo"], r["trabalhos"][:2])
confere("só o da semana dá para continuar; o registro existe só onde tem arquivo",
        [t["continuavel"] for t in r["trabalhos"]] == [True, True, True, False, False, False]
        and [t["registro"] for t in r["trabalhos"]] == [True] + [False] * 5)
r = ex.acao_claude_historico(painel, {"quantos": 2})
confere("de quantos em quantos, com mais", [t["id"] for t in r["trabalhos"]] == ["00000000", "00000001"] and r["mais"])
r = ex.acao_claude_historico(painel, {"quantos": 2, "antes": r["trabalhos"][-1]["criado"]})
confere("a página seguinte começa depois do último", [t["id"] for t in r["trabalhos"]] == ["00000002", "00000003"])
outro = {"cliente": "outro", "zonas": ["apps"], "acoes": []}
confere("quem não fala pelo dono só vê os próprios", ex.acao_claude_historico(outro, {})["trabalhos"] == [])
confere("quantos fora do limite: 400", erro(ex, ex.acao_claude_historico, painel, {"quantos": 80})[0] == 400)
confere("antes que não é número: 400", erro(ex, ex.acao_claude_historico, painel, {"antes": "ontem"})[0] == 400)
os.remove(f"{tmp}/claude-arquivo.jsonl")
confere("sem o arquivo, só a semana", len(ex.acao_claude_historico(painel, {})["trabalhos"]) == 3)

# --- o registro de um trabalho -------------------------------------------------------------------------
EVENTOS = [
    {"type": "system", "subtype": "init", "model": "claude-opus-5-5", "session_id": "s"},
    {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": "hmm"},
                                                  {"type": "text", "text": "Vou criar o jogo."},
                                                  {"type": "tool_use", "id": "u1", "name": "Bash",
                                                   "input": {"command": "npm init -y", "description": "inicia"}}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "u1",
                                              "content": [{"type": "text", "text": "ok\nAPI_KEY=sk-segredo"}]}]}},
    {"type": "assistant", "parent_tool_use_id": "t9", "message": {"content": [
        {"type": "tool_use", "id": "u2", "name": "Read", "input": {"file_path": "/srv/lab/projetos/nave/a.js"}}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "u2", "is_error": True,
                                              "content": "não existe"}]}},
    {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}},
    {"type": "rate_limit_event", "rate_limit_info": {"status": "rejected"}},
    {"type": "atena", "nota": "fechado 60 s depois do resumo final"},
    {"type": "result", "is_error": False, "result": "Pronto: jogo criado.", "total_cost_usd": 0.42,
     "num_turns": 7, "duration_ms": 61500},
]
with open(f"{tmp}/registros/00000000.executar.jsonl", "w") as f:
    f.write("aviso solto do stderr\n" + "\n".join(json.dumps(e) for e in EVENTOS) + "\n")
with open(f"{tmp}/registros/00000000.plano.jsonl", "w") as f:
    f.write(json.dumps({"type": "result", "is_error": False, "result": "o plano", "duration_ms": 1000}) + "\n")
r = ex.acao_claude_registro(painel, {"trabalho": "00000000"})
tipos = [i["tipo"] for i in r["itens"]]
confere("registro: as fases em ordem (plano, executar), com o que importa e sem o stderr",
        tipos == ["fase", "fim", "fase", "inicio", "texto", "ferramenta", "ferramenta", "nota", "nota", "fim"], tipos)
bash, leitura = r["itens"][5], r["itens"][6]
confere("a ferramenta com o comando e o resultado, sem o segredo",
        bash["nome"] == "Bash" and bash["detalhe"] == "npm init -y" and bash["resultado"].startswith("ok")
        and "sk-segredo" not in bash["resultado"] and not bash["erro"], bash)
confere("o subagente vem marcado, e o erro da ferramenta também", leitura["sub"] and leitura["erro"], leitura)
fim_ = r["itens"][-1]
confere("o fim: texto, custo, turnos e segundos",
        fim_ == {"tipo": "fim", "ok": True, "texto": "Pronto: jogo criado.", "custo": 0.42, "turnos": 7, "segundos": 62}, fim_)
confere("só o limite de uso recusado vira nota", sum(1 for i in r["itens"] if i.get("texto") == "a conta bateu o limite de uso") == 1)
r = ex.acao_claude_registro(painel, {"trabalho": "00000000", "de": 4, "quantos": 2})
confere("de quantos em quantos itens, com o total", [i["tipo"] for i in r["itens"]] == ["texto", "ferramenta"] and r["total"] == 10)
confere("trabalho sem registro: 404", erro(ex, ex.acao_claude_registro, painel, {"trabalho": "00000001"})[0] == 404)
confere("trabalho inválido: 400", erro(ex, ex.acao_claude_registro, painel, {"trabalho": "../../x"})[0] == 400)
confere("só quem fala pelo dono lê o registro", erro(ex, ex.acao_claude_registro, atena, {"trabalho": "00000000"})[0] == 403)
fim()
