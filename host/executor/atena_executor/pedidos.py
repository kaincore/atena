"""Pedidos: as ações que esperam a aprovação do dono.

Aprovação no celular: as ações que mudam algo (reiniciar) podem exigir que o dono toque em Aprovar no
celular (ntfy) antes de rodar. Quem exige é o token de cada cliente (campo "aprovar"); sem o campo,
todas exigem. O código de cada pedido só existe na notificação (tópico que só o dono lê), então o
cliente não consegue se aprovar sozinho."""

import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.request

from .base import Cancelado, Erro, ler, log
from .celular import NTFY, NTFY_TOKEN, avisar, avisar_quando_der, botao, legivel, ntfy


PEDIDOS = "/var/lib/atena-executor/pedidos.json"
VALIDADE = 10 * 60          # um pedido espera a aprovação por 10 min
MAX_AGUARDANDO = 5          # por cliente: um cliente enganado não enche o celular de pedidos
TERMINADOS = {"concluido", "falhou", "recusado", "expirado", "cancelado"}
TRAVA = threading.RLock()
MUDOU = threading.Condition(TRAVA)   # acorda quem espera em GET /pedido?esperar
ESTADO = {"pedidos": {}, "ultima_resposta": None}


def carregar_estado():
    """Os pedidos guardados em disco. Um arquivo ilegível (cortado numa queda de energia, mexido à mão)
    não some em silêncio: o executor começa vazio, mas guarda o arquivo ao lado e avisa o dono."""
    try:
        with open(PEDIDOS) as f:
            dados = json.load(f)
        pedidos = dados.get("pedidos", {}) if isinstance(dados, dict) else None
        if not isinstance(pedidos, dict) or not all(isinstance(p, dict) for p in pedidos.values()):
            raise ValueError('não está no formato {"pedidos": {id: pedido}}')
    except FileNotFoundError:   # a primeira vez
        return
    except ValueError as e:   # JSON quebrado (texto que não é UTF-8 também cai aqui) ou de outro formato
        guardar_ilegivel(e)
        return
    ESTADO.update(dados)


def guardar_ilegivel(erro):
    """Move o pedidos.json ilegível para o lado, com a data no nome (mover, e não copiar: um reinício logo
    depois não repete a cópia nem o aviso), registra e avisa o dono quando o ntfy deixar."""
    copia = f"{PEDIDOS}.ilegivel-{time.strftime('%Y%m%d-%H%M%S')}"
    try:
        os.replace(PEDIDOS, copia)
        onde = f"O arquivo ficou em {copia}: dá para conferir ou recuperar à mão (com o executor parado)."
    except OSError as e:
        copia, onde = None, f"Nem consegui guardar o arquivo ao lado ({e}): o próximo pedido grava por cima."
    log(evento="pedidos.json ilegível: o executor começou sem o histórico", erro=str(erro), copia=copia)
    avisar_quando_der("Executor: histórico de pedidos ilegível",
                      f"O {PEDIDOS} não abriu ({erro}), e o executor começou sem os pedidos da última semana "
                      f"(trabalhos do Claude Code em andamento também). {onde}", tags=["warning"])


def salvar_estado():
    with TRAVA:
        limite = time.time() - 7 * 86400   # guarda uma semana de histórico
        ESTADO["pedidos"] = {i: p for i, p in ESTADO["pedidos"].items() if p["criado"] > limite}
        temporario = PEDIDOS + ".novo"
        with open(os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
            json.dump(ESTADO, f, ensure_ascii=False)
        os.replace(temporario, PEDIDOS)


def mudar(p, **campos):
    with TRAVA:
        p.update(campos, atualizado=time.time())
        salvar_estado()
        MUDOU.notify_all()


def precisa_aprovacao(cliente, nome):
    """Se o pedido vai ao celular do dono: o que o token manda aprovar e, sempre, o que é destrutivo (uma
    ação nova destrutiva pede o celular mesmo que ninguém a ponha no token). Sem o campo aprovar no token,
    tudo o que vira pedido. Com aprovar vazio ("nenhuma"), nada: é o painel, onde quem confirma, na
    tela, é o próprio dono."""
    from .acoes import ACOES, DESTRUTIVO  # aqui: a lista de ações usa este módulo
    acao = ACOES.get(nome)
    if acao is None or acao.preparar is None:   # só um pedido espera o celular
        return False
    aprovar = cliente.get("aprovar")
    if aprovar is None:
        return True
    return aprovar != [] and (nome in aprovar or acao.risco == DESTRUTIVO)


def criar_pedido(cliente, nome, params, origem, titulo):
    with TRAVA:
        aguardando = [p for p in ESTADO["pedidos"].values()
                      if p["cliente"] == cliente["cliente"] and p["estado"] == "aguardando"
                      and p["expira"] > time.time()]
        if len(aguardando) >= MAX_AGUARDANDO:
            raise Erro(429, "já há pedidos demais esperando aprovação")
        p = {"id": secrets.token_hex(4), "cliente": cliente["cliente"], "zonas": cliente["zonas"],
             "acao": nome, "params": params, "origem": origem, "titulo": titulo, "estado": "novo",
             "criado": time.time()}
        ESTADO["pedidos"][p["id"]] = p
    return p


def pedir_aprovacao(p, titulo, texto):
    segredo = secrets.token_urlsafe(18)
    mudar(p, estado="aguardando", segredo=segredo, expira=time.time() + VALIDADE, aviso=texto[:3000])
    try:
        ntfy("aprovacoes", titulo,
             f"{texto}\n\nPedido {p['id']} de {p['cliente']} · vale por {VALIDADE // 60} min",
             prioridade=4, tags=["warning"],
             acoes=[botao("Aprovar", "aprovar", p, segredo), botao("Recusar", "recusar", p, segredo)])
    except (OSError, urllib.error.URLError) as e:
        mudar(p, estado="falhou", segredo=None, erro="não consegui mandar o pedido para o celular")
        log(evento="ntfy fora do ar", erro=str(e))
        raise Erro(503, "não consegui mandar o pedido para o celular (ntfy fora do ar)")


def publico(p):
    """O pedido como o cliente vê: sem o código dos botões."""
    return {k: v for k, v in p.items() if k not in ("segredo", "zonas", "nonce")}


def tratar_resposta(texto):
    m = re.fullmatch(r"(aprovar|recusar|cancelar|opcao[0-2]) ([0-9a-f]{8}) ([A-Za-z0-9_-]{24})", texto.strip())
    if not m:
        return
    decisao, id_, segredo = m.groups()
    with TRAVA:
        p = ESTADO["pedidos"].get(id_)
        if not p or not p.get("segredo") or not secrets.compare_digest(p["segredo"], segredo):
            if not p or p["estado"] in ("aguardando", "planejando", "executando", "perguntando"):
                log(evento="resposta inválida", pedido=id_)   # toque repetido num decidido é normal
            return
    decidir(p, decisao, "celular")


def decidir(p, decisao, por, resposta=None):
    """A decisão do dono: pelo botão do celular (tratar_resposta) ou pelo painel (aprovacoes.decidir).
    Devolve o que aconteceu: aprovado, recusado, expirado, respondida, cancelando ou ignorado."""
    from .claude import cancelar_claude, negar_permissao, responder_pergunta  # aqui: o claude usa este módulo
    with TRAVA:
        log(evento="decisão do dono", pedido=p["id"], acao=p["acao"], decisao=decisao, por=por)
        if decisao.startswith("opcao") or decisao == "responder":   # pergunta do Claude Code
            if decisao == "responder":
                texto = resposta
            else:
                opcoes = p["params"].get("opcoes") or []
                i = int(decisao[-1])
                texto = opcoes[i] if i < len(opcoes) else None
            if p["acao"] != "claude.pergunta" or p["estado"] != "perguntando" or not texto:
                return "ignorado"
            responder_pergunta(p, texto, "dono (botão no celular)" if por == "celular" else f"dono ({por})")
            return "respondida"
        if decisao == "cancelar":
            if p["estado"] in ("planejando", "executando"):
                cancelar_claude(p)
                return "cancelando"
            return "ignorado"
        if p["estado"] != "aguardando":
            return "ignorado"
        if time.time() > p["expira"]:
            mudar(p, estado="expirado", segredo=None)
            negar_permissao(p, "o dono não respondeu a tempo")
            avisar(f"Pedido {p['id']} expirou", "Nada foi feito. Peça de novo à Atena se ainda quiser.",
                   tags=["hourglass"])
            return "expirado"
        if decisao == "recusar":
            mudar(p, estado="recusado", segredo=None, decidido_por=por)
            if p["acao"] == "claude.permissao":   # o Claude Code fica sabendo; sem aviso extra
                negar_permissao(p, "o dono recusou")
                return "recusado"
            avisar(f"Recusado: {p['titulo']}", "Nada foi feito.", tags=["no_entry"])
            return "recusado"
        mudar(p, estado="executando", segredo=None, decidido_por=por)
    threading.Thread(target=executar_aprovado, args=(p,), daemon=True).start()
    return "aprovado"


def executar(p):
    """Roda a ação de um pedido (aprovado, ou de um cliente que não precisa de aprovação)."""
    from .acoes import ACOES, INTERNAS  # aqui: a lista de ações usa este módulo
    try:
        funcao = INTERNAS[p["acao"]] if p["acao"] in INTERNAS else ACOES[p["acao"]][0]
        resultado = funcao(p)
        if resultado is not None:   # None: a ação segue sozinha (Claude Code)
            mudar(p, estado="concluido", resultado=resultado)
        return resultado
    except Erro as e:
        mudar(p, estado="cancelado" if isinstance(e, Cancelado) else "falhou", erro=str(e))
        raise
    except Exception as e:
        mudar(p, estado="falhou", erro=f"erro interno: {e}")
        log(evento="erro ao executar", pedido=p["id"], erro=repr(e))
        raise Erro(500, "erro interno; veja journalctl -u atena-executor")


def executar_aprovado(p):
    try:
        resultado = executar(p)
        if resultado is not None:
            avisar(f"Feito: {p['titulo']}", legivel(resultado)[:1000], tags=["white_check_mark"])
    except Cancelado as e:
        avisar(f"Cancelado: {p['titulo']}", str(e), tags=["no_entry"])
    except Erro as e:
        avisar(f"Falhou: {p['titulo']}", str(e), tags=["x"])


def ouvir_respostas():
    """Fica ligado no tópico de respostas: é por ali que chegam os toques nos botões."""
    while True:
        desde = ESTADO.get("ultima_resposta") or str(int(time.time()))
        try:
            pedido = urllib.request.Request(f"{NTFY}/respostas/json?since={desde}",
                                            headers={"Authorization": "Bearer " + ler(NTFY_TOKEN)})
            with urllib.request.urlopen(pedido, timeout=120) as r:   # o ntfy dá sinal a cada 45 s
                for linha in r:
                    evento = json.loads(linha)
                    if evento.get("event") != "message":
                        continue
                    with TRAVA:
                        ESTADO["ultima_resposta"] = evento["id"]
                        tratar_resposta(evento.get("message", ""))
                        salvar_estado()
        except Exception as e:
            log(evento="respostas: reconectando", erro=str(e))
            time.sleep(10)


def no_alcance(cliente, p):
    """O cliente só enxerga pedidos de quem não passa das zonas dele."""
    return set(p.get("zonas") or ()) <= set(cliente["zonas"])


def pelo_dono(cliente):
    """O painel: quem decide pelo dono também vê e cancela os trabalhos dos outros clientes."""
    return "aprovacoes.decidir" in cliente.get("acoes", ())


def alcanca(cliente, p):
    """O pedido é do cliente, ou o cliente fala pelo dono e o pedido está no alcance dele."""
    return p["cliente"] == cliente["cliente"] or (pelo_dono(cliente) and no_alcance(cliente, p))


def pedidos_interrompidos():
    """stack.aplicar e app.publicar rodam numa thread do executor: se ele reiniciou no meio, o pedido
    não volta sozinho. (O Claude Code roda no runner e continua: o resultado chega depois.)"""
    with TRAVA:
        for p in ESTADO["pedidos"].values():
            if p["acao"] in ("stack.aplicar", "app.publicar") and p["estado"] == "executando":
                p.update(estado="falhou", erro="o executor reiniciou no meio; confira com status.servicos e "
                                                "aplique de novo se precisar", atualizado=time.time())
        salvar_estado()
