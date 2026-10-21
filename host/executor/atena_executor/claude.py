"""Claude Code no lab (módulo lab): claude.tarefa põe um trabalho na fila (/var/lib/atena-claude/fila);
o atena-claude-runner roda o Claude Code como atena-claude em /srv/lab/projetos/<projeto>, com o
sandbox do lab. Quando o Claude Code pede permissão, a ponte (dono.py) deixa
fila/<trabalho>-<n>.permissao; o executor manda para o celular com Aprovar/Recusar e devolve a
decisão em fila/<trabalho>-<n>.resposta. Perguntas do Claude Code chegam como
fila/<trabalho>-q<n>.pergunta: o celular é avisado na hora (com botões, se houver opções) e a
resposta volta por claude.responder (do dono, ou da Atena se ele não responder em 10 min).
Com ATENA_CLAUDE_SKILLS=sim, claude.tarefa aceita uma skill do catálogo do lab (skills.json), que o
runner chama no começo do pedido."""

import glob
import json
import os
import re
import secrets
import threading
import time

from .base import Erro, ler_conf, log
from .celular import avisar, botao
from .lab import PROJETOS_LAB, lixeira, preparar_app_publicar
from .pedidos import (ESTADO, TERMINADOS, TRAVA, alcanca, criar_pedido, executar_aprovado, mudar,
                      pedir_aprovacao, pelo_dono, precisa_aprovacao)
from .segredos import curto, ocultar
from .tokens import carregar_tokens


CLAUDE = "/var/lib/atena-claude"              # fila, resultados e contas do Claude Code do lab
SKILLS_CLAUDE = "/usr/local/lib/atena-claude/skills.json"   # catálogo das skills (o runner lê o mesmo)
MAX_FILA_CLAUDE = 5         # trabalhos do Claude Code esperando ou rodando (3 rodam juntos)
MODELOS_CLAUDE = {"fable", "opus", "sonnet", "haiku"}
ESFORCOS_CLAUDE = ("low", "medium", "high", "xhigh", "max")
ESPERA_PERGUNTA = 30 * 60   # a ponte espera a resposta de uma pergunta do Claude Code por até 30 min


def lab_instalado():
    return os.path.isdir(f"{CLAUDE}/fila")


def contas_claude():
    """As contas do Claude Code no atena.conf (ATENA_CLAUDE_CONTAS), na ordem em que aparecem."""
    nomes = re.split(r"[\s,]+", ler_conf().get("ATENA_CLAUDE_CONTAS") or "principal")
    return [n for n in dict.fromkeys(nomes) if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,19}", n)]


def contas_prontas():
    """As contas do atena.conf com login (contas.json, escrito pelo atena-claude-conta)."""
    try:
        with open(f"{CLAUDE}/contas.json") as f:
            prontas = {c for c, pronta in json.load(f).items() if pronta}
    except (OSError, ValueError, AttributeError):
        return set()
    return prontas & set(contas_claude())


def skills_claude():
    """As skills que a Atena pode mandar o Claude Code rodar no começo do pedido, na ordem do catálogo;
    nenhuma sem ATENA_CLAUDE_SKILLS=sim (o instalador põe os plugins nas contas)."""
    if ler_conf().get("ATENA_CLAUDE_SKILLS") != "sim":
        return []
    try:
        with open(SKILLS_CLAUDE) as f:
            catalogo = json.load(f)
    except (OSError, ValueError):
        return []
    return [n for n, c in catalogo.items() if isinstance(c, str)] if isinstance(catalogo, dict) else []


def descrever_skills(nomes):
    """frontend-design, to-spec ou impeccable <init|polish>: as variações de uma skill juntas."""
    grupos = {}
    for nome in nomes:
        base, _, variacao = nome.partition(" ")
        grupos.setdefault(base, []).append(variacao)
    partes = [base if variacoes == [""] else f"{base} <{'|'.join(v for v in variacoes if v)}>"
              for base, variacoes in grupos.items()]
    return ", ".join(partes[:-1]) + " ou " + partes[-1] if len(partes) > 1 else partes[0]


def enfileirar(p, fase, **extra):
    dados = {"id": p["id"], "fase": fase, **extra}
    final = f"{CLAUDE}/fila/{p['id']}.{fase}.json"
    temporario = f"{CLAUDE}/fila/.{p['id']}.{fase}.novo"   # o runner só pega *.json
    with open(os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640), "w") as f:
        json.dump(dados, f, ensure_ascii=False)
    os.replace(temporario, final)
    mudar(p, fase=fase, estado={"plano": "planejando", "executar": "executando"}[fase])


def cancelar_claude(p):
    with open(os.open(f"{CLAUDE}/fila/{p['id']}.cancelar", os.O_WRONLY | os.O_CREAT, 0o640), "w"):
        pass   # o runner vê este arquivo e interrompe o Claude Code
    try:   # se ainda não tinha começado, basta tirar da fila
        os.unlink(f"{CLAUDE}/fila/{p['id']}.{p['fase']}.json")
    except FileNotFoundError:
        mudar(p, cancelando=True)   # já está rodando: o runner interrompe e manda o resultado
        return
    os.unlink(f"{CLAUDE}/fila/{p['id']}.cancelar")
    mudar(p, estado="cancelado", segredo=None)
    avisar(f"Cancelado: trabalho {p['id']}", "Ele ainda estava na fila; nada rodou.", tags=["no_entry"])


def resultado_claude(id_, fase):
    try:
        with open(f"{CLAUDE}/resultados/{id_}.{fase}.json") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def responder_permissao(chave, nonce, permitir, motivo=""):
    """Devolve a decisão à ponte do Claude Code (fila/<chave>.resposta, só o nonce dela vale)."""
    final = f"{CLAUDE}/fila/{chave}.resposta"
    temporario = f"{CLAUDE}/fila/.{chave}.resposta.novo"
    with open(os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640), "w") as f:
        json.dump({"nonce": nonce, "permitir": permitir, "motivo": motivo}, f, ensure_ascii=False)
    os.replace(temporario, final)


def negar_permissao(p, motivo):
    if p["acao"] == "claude.permissao":
        responder_permissao(p["params"]["chave"], p.get("nonce"), False, motivo)


def levar_permissoes():
    """Pedidos de permissão do Claude Code (fila/<trabalho>-<n>.permissao) viram pedidos no celular."""
    for caminho in sorted(glob.glob(f"{CLAUDE}/fila/*.permissao")):
        chave = os.path.basename(caminho)[:-len(".permissao")]
        try:
            with open(caminho) as f:
                dados = json.load(f)
        except (OSError, ValueError):
            dados = None
        try:
            os.unlink(caminho)
        except FileNotFoundError:
            continue
        m = re.fullmatch(r"([0-9a-f]{8})-(\d{1,4})", chave)
        if not m or not isinstance(dados, dict) or not isinstance(dados.get("nonce"), str):
            log(evento="permissão com defeito ignorada", arquivo=chave)
            continue
        with TRAVA:
            trabalho = ESTADO["pedidos"].get(m.group(1))
        if (not trabalho or trabalho["acao"] != "claude.tarefa"
                or trabalho["estado"] not in ("planejando", "executando")):
            responder_permissao(chave, dados["nonce"], False, "trabalho desconhecido ou já terminado")
            continue
        ferramenta = str(dados.get("ferramenta") or "?")[:60]
        detalhe = ocultar(str(dados.get("detalhe") or ""))[:600]
        motivo = ocultar(str(dados.get("motivo") or ""))[:300]
        cliente = {"cliente": trabalho["cliente"], "zonas": trabalho["zonas"]}
        try:
            p = criar_pedido(cliente, "claude.permissao",
                             {"trabalho": trabalho["id"], "chave": chave, "ferramenta": ferramenta,
                              "detalhe": detalhe}, "claude", f"Claude Code quer usar {ferramenta}")
            mudar(p, nonce=dados["nonce"])
            texto = (f"Trabalho {trabalho['id']} (projeto {trabalho['params'].get('projeto')}): "
                     f"{trabalho['params']['pedido'][:200]}\n\n{ferramenta}: {detalhe}")
            if motivo:
                texto += f"\n\nPor quê: {motivo}"
            pedir_aprovacao(p, f"Claude Code pede: {ferramenta}", texto)
            log(evento="permissão pedida", pedido=p["id"], trabalho=trabalho["id"], ferramenta=ferramenta)
        except Erro as e:   # pedidos demais esperando, ou ntfy fora do ar
            responder_permissao(chave, dados["nonce"], False, str(e))


def acao_claude_permissao(p):
    """Interna: o dono tocou em Aprovar num pedido de permissão do Claude Code."""
    responder_permissao(p["params"]["chave"], p.get("nonce"), True)
    mudar(p, estado="concluido", nonce=None)
    return None   # sem o aviso "Feito": o Claude Code segue sozinho


def responder_pergunta(p, resposta, quem):
    """Devolve a resposta de uma pergunta do Claude Code à ponte (fila/<chave>.resposta, com o nonce)."""
    chave = p["params"]["chave"]
    final = f"{CLAUDE}/fila/{chave}.resposta"
    temporario = f"{CLAUDE}/fila/.{chave}.resposta.novo"
    with open(os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640), "w") as f:
        json.dump({"nonce": p.get("nonce"), "resposta": resposta, "quem": quem}, f, ensure_ascii=False)
    os.replace(temporario, final)
    mudar(p, estado="concluido", resposta=resposta, quem=quem, segredo=None, nonce=None)
    log(evento="pergunta respondida", pedido=p["id"], trabalho=p["params"]["trabalho"], quem=quem)


def levar_perguntas():
    """Perguntas do Claude Code (fila/<trabalho>-q<n>.pergunta): avisam o celular na hora e ficam
    esperando o dono responder pela Atena (claude.responder) ou num botão de opção."""
    for caminho in sorted(glob.glob(f"{CLAUDE}/fila/*.pergunta")):
        chave = os.path.basename(caminho)[:-len(".pergunta")]
        try:
            with open(caminho) as f:
                dados = json.load(f)
        except (OSError, ValueError):
            dados = None
        try:
            os.unlink(caminho)
        except FileNotFoundError:
            continue
        m = re.fullmatch(r"([0-9a-f]{8})-q(\d{1,4})", chave)
        pergunta = dados.get("pergunta") if isinstance(dados, dict) else None
        if not m or not isinstance(pergunta, str) or not isinstance(dados.get("nonce"), str):
            log(evento="pergunta com defeito ignorada", arquivo=chave)
            continue
        with TRAVA:
            trabalho = ESTADO["pedidos"].get(m.group(1))
        falso = {"params": {"chave": chave, "trabalho": m.group(1)}, "nonce": dados["nonce"], "id": "-"}
        if (not trabalho or trabalho["acao"] != "claude.tarefa"
                or trabalho["estado"] not in ("planejando", "executando")):
            responder_pergunta_solta(falso, "o trabalho já terminou; siga sem resposta")
            continue
        opcoes = [str(o).strip()[:60] for o in (dados.get("opcoes") or []) if str(o).strip()][:3]
        params = {"trabalho": trabalho["id"], "chave": chave, "projeto": trabalho["params"].get("projeto"),
                  "pergunta": ocultar(pergunta.strip())[:1500], "opcoes": opcoes,
                  "por_que": ocultar(str(dados.get("por_que") or "").strip())[:500]}
        p = criar_pedido({"cliente": trabalho["cliente"], "zonas": trabalho["zonas"]}, "claude.pergunta",
                         params, "claude", f"Claude Code pergunta ({params['projeto']})")
        segredo = secrets.token_urlsafe(18)
        mudar(p, estado="perguntando", nonce=dados["nonce"], segredo=segredo)
        texto = params["pergunta"] + (f"\n\nPor quê: {params['por_que']}" if params["por_que"] else "")
        texto += "\n\nResponda à Atena no Telegram" + (" ou toque numa opção." if opcoes else ".")
        texto += " Sem resposta em 10 min, a Atena decide."
        avisar(f"Claude Code pergunta (projeto {params['projeto']})", texto, tags=["question"],
               acoes=[botao(o[:30], f"opcao{i}", p, segredo) for i, o in enumerate(opcoes)])
        log(evento="pergunta recebida", pedido=p["id"], trabalho=trabalho["id"])


def responder_pergunta_solta(p, resposta):
    """Resposta para uma pergunta que nem virou pedido (trabalho inexistente ou terminado)."""
    chave = p["params"]["chave"]
    with open(os.open(f"{CLAUDE}/fila/.{chave}.resposta.novo", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640), "w") as f:
        json.dump({"nonce": p["nonce"], "resposta": resposta, "quem": "executor"}, f, ensure_ascii=False)
    os.replace(f"{CLAUDE}/fila/.{chave}.resposta.novo", f"{CLAUDE}/fila/{chave}.resposta")


def acompanhar():
    """De 3 em 3 s: vence pedidos sem resposta e leva o Claude Code adiante (permissões, perguntas e
    resultados)."""
    while True:
        time.sleep(3)
        for levar in (levar_permissoes, levar_perguntas):
            try:
                levar()
            except Exception as e:
                log(evento=f"acompanhar: erro em {levar.__name__}", erro=repr(e))
        with TRAVA:
            pedidos = list(ESTADO["pedidos"].values())
        for p in pedidos:
            try:
                if p["estado"] == "aguardando" and time.time() > p["expira"]:
                    mudar(p, estado="expirado", segredo=None)
                    negar_permissao(p, "o dono não respondeu a tempo")
                elif p["estado"] == "perguntando" and time.time() > p["criado"] + ESPERA_PERGUNTA + 600:
                    mudar(p, estado="expirado", segredo=None, nonce=None)   # a ponte já desistiu
                elif p["estado"] in ("planejando", "executando") and p.get("fase"):
                    r = resultado_claude(p["id"], p["fase"])
                    if r:
                        concluir_claude(p, r)
            except Exception as e:
                log(evento="acompanhar: erro", pedido=p.get("id"), erro=repr(e))


def concluir_claude(p, r):
    texto = (r.get("texto") or "").strip() or "(sem resumo)"
    with TRAVA:   # permissões e perguntas ainda esperando o dono perdem o sentido
        pendentes = [q for q in ESTADO["pedidos"].values()
                     if q["acao"] in ("claude.permissao", "claude.pergunta")
                     and q["estado"] in ("aguardando", "perguntando") and q["params"]["trabalho"] == p["id"]]
    for q in pendentes:
        mudar(q, estado="expirado", segredo=None, nonce=None)
        negar_permissao(q, "o trabalho terminou")
    if r.get("trocas"):   # bateu o limite de uso e passou para outra conta (ATENA_CLAUDE_TROCA=sim)
        mudar(p, conta_final=r.get("conta"), trocas=r["trocas"])
    if r.get("cancelado"):
        # guarda a conversa: dá para continuar (até com outro modelo ou esforço) de onde parou
        mudar(p, estado="cancelado", segredo=None, resumo=texto, sessao=r.get("sessao") or p.get("sessao"))
        avisar(f"Cancelado: trabalho {p['id']}", texto[:3000], tags=["no_entry"])
        return
    mudar(p, estado="concluido" if r["ok"] else "falhou", segredo=None, resumo=texto,
          sessao=r.get("sessao") or p.get("sessao"), uso=r.get("uso"), segundos=r.get("segundos"),
          commits=r.get("commits", []))
    if p["fase"] == "plano":
        avisar(f"Plano pronto (trabalho {p['id']})", texto[:3500], tags=["memo"])
        return
    if p["params"].get("projeto"):
        texto += f"\n\nPasta: /srv/lab/projetos/{p['params']['projeto']}"
        if r.get("commits"):
            texto += f" ({len(r['commits'])} commits)"
    for t in r.get("trocas", []):
        texto += f"\n\nTrocou de conta: {t['de']} → {t['para']} ({t['motivo']})"
    avisar(f"Claude Code {'terminou' if r['ok'] else 'parou com erro'} (trabalho {p['id']})", texto,
           tags=["white_check_mark" if r["ok"] else "x"])
    if r["ok"] and p["params"].get("publicar"):
        publicar_depois(p)


def publicar_depois(trabalho):
    """claude.tarefa com publicar: o trabalho terminou bem, então publica a versão nova.

    Segue a regra de aprovação do token do cliente, lida de novo agora: um token revogado ou sem
    app.publicar não publica.
    """
    projeto = trabalho["params"]["projeto"]
    cliente = next((c for c in carregar_tokens().values() if c["cliente"] == trabalho["cliente"]), None)
    try:
        if not cliente or "app.publicar" not in cliente["acoes"]:
            raise Erro(403, f"o cliente {trabalho['cliente']} não pode mais publicar")
        params = {"projeto": projeto}
        titulo, texto = preparar_app_publicar(cliente, params)
        p = criar_pedido(cliente, "app.publicar", params, f"trabalho {trabalho['id']}", titulo)
        mudar(trabalho, publicacao=p["id"])
        if precisa_aprovacao(cliente, "app.publicar"):
            pedir_aprovacao(p, f"{cliente['cliente']} pede: {titulo}",
                            f"Versão nova do trabalho {trabalho['id']}.\n\n{texto}")
            return
        mudar(p, estado="executando")
        threading.Thread(target=executar_aprovado, args=(p,), daemon=True).start()
    except Erro as e:
        mudar(trabalho, publicacao_erro=str(e))
        avisar(f"Não publiquei {projeto}", str(e), tags=["x"])


def preparar_claude_tarefa(cliente, params):
    if not lab_instalado():
        raise Erro(503, "o lab não está instalado neste servidor (sudo ./install.sh --lab)")
    pedido, continuar = params.get("pedido"), params.get("continuar")
    if not isinstance(pedido, str) or not 3 <= len(pedido.strip()) <= 4000:
        raise Erro(400, "pedido deve ter de 3 a 4000 caracteres")
    params["pedido"] = pedido.strip()
    params["somente_plano"] = bool(params.get("somente_plano"))
    params["publicar"] = bool(params.get("publicar"))   # publica sozinho quando terminar bem
    if params["publicar"] and params["somente_plano"]:
        raise Erro(400, "publicar não combina com somente_plano (um plano não muda o app)")
    if params["publicar"] and "app.publicar" not in cliente.get("acoes", []):
        raise Erro(403, f"o cliente {cliente['cliente']} não pode pedir app.publicar")
    minutos = params.setdefault("minutos", 60)   # trabalhos longos (a noite toda): até 600
    if not isinstance(minutos, int) or not 5 <= minutos <= 600:
        raise Erro(400, "minutos deve ser um número de 5 a 600")
    if continuar is not None:   # continua a conversa de um trabalho anterior
        with TRAVA:
            anterior = ESTADO["pedidos"].get(continuar) if isinstance(continuar, str) else None
        if (not anterior or anterior["acao"] != "claude.tarefa" or not alcanca(cliente, anterior)
                or not anterior.get("sessao")):
            raise Erro(404, "não achei um trabalho anterior com esse id para continuar")
        if anterior["estado"] not in TERMINADOS:
            raise Erro(409, "o trabalho anterior ainda não terminou")
        # a conversa fica na conta em que o trabalho terminou (pode ter trocado pelo limite de uso);
        # com outra conta, a pedido do dono, o runner leva a conversa para ela
        params["sessao_conta"] = anterior.get("conta_final") or anterior["params"]["conta"]
        params["conta"] = params.get("conta") or params["sessao_conta"]
        params["sessao"] = anterior["sessao"]
        params["projeto"] = anterior["params"].get("projeto")
        params.setdefault("modelo", anterior["params"].get("modelo"))
        params.setdefault("esforco", anterior["params"].get("esforco"))
    projeto = params.get("projeto")
    if not isinstance(projeto, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", projeto):
        raise Erro(400, "projeto deve ser um nome curto, com letras minúsculas, números e hífen "
                        "(ex.: lista-compras); vira a pasta /srv/lab/projetos/<projeto>")
    if continuar is not None and not os.path.isdir(f"{PROJETOS_LAB}/{projeto}"):
        raise Erro(409, f"a pasta do projeto {projeto} não existe mais"
                        + ("; ele está na lixeira: app.restaurar traz de volta" if lixeira(projeto) else ""))
    if params.get("modelo") is not None and params["modelo"] not in MODELOS_CLAUDE:
        raise Erro(400, "modelo deve ser fable, opus, sonnet ou haiku (ou ficar de fora)")
    if params.get("esforco") is not None and params["esforco"] not in ESFORCOS_CLAUDE:
        raise Erro(400, "esforco deve ser low, medium, high, xhigh ou max (ou ficar de fora)")
    if params.get("skill") is not None:   # não vem do continuar: cada trabalho escolhe a sua
        skills = skills_claude()
        if not skills:
            raise Erro(400, "as skills do Claude Code não estão ligadas neste servidor (ATENA_CLAUDE_SKILLS)")
        if params["skill"] not in skills:
            raise Erro(400, f"skill deve ser {descrever_skills(skills)} (ou ficar de fora)")
    contas = contas_claude()
    if not params.get("conta") and len(contas) == 1:
        params["conta"] = contas[0]
    if params.get("conta") not in contas:
        raise Erro(400, "conta deve ser " + " ou ".join(contas) + " (as contas de ATENA_CLAUDE_CONTAS)")
    if params["conta"] not in contas_prontas():
        raise Erro(409, f"a conta {params['conta']} ainda não tem login no servidor "
                        f"(sudo atena-claude-conta entrar {params['conta']})")
    with TRAVA:
        na_fila = [p for p in ESTADO["pedidos"].values()
                   if p["acao"] == "claude.tarefa" and p["estado"] in ("planejando", "executando")]
        mesmo_projeto = [p for p in na_fila if p["params"].get("projeto") == projeto]
    if len(na_fila) >= MAX_FILA_CLAUDE:
        raise Erro(429, f"já há {len(na_fila)} trabalhos do Claude Code na fila; espere um terminar")
    if mesmo_projeto:
        raise Erro(409, f"o projeto {projeto} já tem um trabalho em andamento ({mesmo_projeto[0]['id']})")
    tipo = "plano" if params["somente_plano"] else "trabalho"
    if params.get("skill"):
        tipo += f" com a skill {params['skill']}"
    if params["publicar"]:
        tipo += " e publicar"
    return f"Claude Code ({params['conta']}) em {projeto}: {tipo}", f"Pedido: {params['pedido']}"


def acao_claude_tarefa(p):
    params = p["params"]
    pedido = params["pedido"]
    if params.get("publicar"):
        pedido += ("\n\n(Quando você terminar, a Atena publica o app de novo pelo Dockerfile desta pasta: "
                   "deixe-o pronto para publicar, seguindo as regras do lab.)")
    enfileirar(p, "plano" if params["somente_plano"] else "executar", conta=params["conta"],
               pedido=pedido, minutos=params["minutos"], projeto=params["projeto"],
               **({"modelo": params["modelo"]} if params.get("modelo") else {}),
               **({"esforco": params["esforco"]} if params.get("esforco") else {}),
               **({"skill": params["skill"]} if params.get("skill") else {}),
               **({"sessao": params["sessao"], "sessao_conta": params["sessao_conta"]} if params.get("sessao") else {}))
    segredo = secrets.token_urlsafe(18)
    mudar(p, segredo=segredo)
    avisar(f"Claude Code ({params['conta']}) começou: trabalho {p['id']}",
           f"Projeto: /srv/lab/projetos/{params['projeto']}\n"
           + (f"Skill: {params['skill']}\n" if params.get("skill") else "")
           + f"\n{params['pedido'][:3000]}\n\n"
           + ("Só vai planejar; nada muda." if params["somente_plano"] else "Toque em Cancelar para interromper."),
           tags=["robot"], acoes=[botao("Cancelar", "cancelar", p, segredo)])
    return None   # o acompanhar() leva o resultado ao celular e ao pedido


def acao_claude_trabalhos(cliente, params):
    with TRAVA:
        meus = sorted((p for p in ESTADO["pedidos"].values()
                       if p["acao"] == "claude.tarefa" and alcanca(cliente, p)),
                      key=lambda p: p["criado"], reverse=True)[:10]
        esperando = {q["params"]["trabalho"] for q in ESTADO["pedidos"].values()
                     if q["acao"] == "claude.permissao" and q["estado"] == "aguardando"}
    skills = skills_claude()
    return {"contas": contas_claude(), "contas_com_login": sorted(contas_prontas()),
            **({"skills": skills} if skills else {}), "trabalhos": [
        {"id": p["id"], "estado": p["estado"], "projeto": p["params"].get("projeto"),
         "conta": p.get("conta_final") or p["params"].get("conta"), "modelo": p["params"].get("modelo"),
         "esforco": p["params"].get("esforco"), "skill": p["params"].get("skill"),
         "pedido": p["params"]["pedido"][:150],
         **({"cliente": p["cliente"], "resumo": curto(p["resumo"], 2000) if p.get("resumo") else None,
             "commits": len(p.get("commits") or []),
             "continuavel": bool(p.get("sessao")) and p["estado"] in TERMINADOS} if pelo_dono(cliente) else {}),
         "criado": time.strftime("%Y-%m-%d %H:%M", time.localtime(p["criado"])),
         "esperando_permissao_no_celular": p["id"] in esperando}
        for p in meus]}


def acao_claude_cancelar(cliente, params):
    alvo = params.get("pedido")
    with TRAVA:
        p = ESTADO["pedidos"].get(alvo) if isinstance(alvo, str) else None
        if not p or p["acao"] != "claude.tarefa" or not alcanca(cliente, p):
            raise Erro(404, "não achei um trabalho do Claude Code com esse id")
        if p["estado"] not in ("planejando", "executando"):
            raise Erro(409, f"o trabalho não está rodando (estado: {p['estado']})")
        cancelar_claude(p)
    return {"cancelando": alvo, "dica": "o resultado chega quando ele parar (segundos)"}


def acao_claude_perguntas(cliente, params):
    agora = time.time()
    with TRAVA:
        abertas = sorted((p for p in ESTADO["pedidos"].values() if p["acao"] == "claude.pergunta"
                          and p["estado"] == "perguntando" and p["cliente"] == cliente["cliente"]),
                         key=lambda p: p["criado"])
    return [{"id": p["id"], "trabalho": p["params"]["trabalho"], "projeto": p["params"]["projeto"],
             "pergunta": p["params"]["pergunta"], "opcoes": p["params"]["opcoes"], "por_que": p["params"]["por_que"],
             "esperando_min": int((agora - p["criado"]) // 60)} for p in abertas]


def acao_claude_responder(cliente, params):
    alvo, resposta, quem = params.get("pergunta"), params.get("resposta"), params.get("quem", "dono")
    if not isinstance(resposta, str) or not 1 <= len(resposta.strip()) <= 2000:
        raise Erro(400, "resposta deve ter de 1 a 2000 caracteres")
    if quem not in ("dono", "atena"):
        raise Erro(400, "quem deve ser dono (o dono respondeu) ou atena (você decidiu porque ele não respondeu)")
    with TRAVA:
        p = ESTADO["pedidos"].get(alvo) if isinstance(alvo, str) else None
        if not p or p["acao"] != "claude.pergunta" or p["cliente"] != cliente["cliente"]:
            raise Erro(404, "não achei essa pergunta do Claude Code (veja claude.perguntas)")
        if p["estado"] != "perguntando":
            raise Erro(409, f"essa pergunta já foi encerrada (estado: {p['estado']})")
        responder_pergunta(p, resposta.strip(), quem)
    return {"respondida": alvo, "quem": quem, "dica": "o Claude Code segue com a resposta"}
