"""A lista fechada de ações, e o catálogo delas: cada uma diz o que faz, o risco e quem a usa. O executor
mostra isso no GET /acoes; o painel lê de lá, e o instalador monta os tokens daqui (atena-executor acoes).
Uma ação nova é a entrada aqui e o código dela, com teste; o resto se acerta sozinho ou o teste avisa."""
from typing import Callable, NamedTuple

from .arquivos import acao_arquivo_buscar, acao_arquivo_entregar, acao_arquivo_ler, acao_arquivo_procurar
from .central import acao_aprovacoes_decidir, acao_aprovacoes_lista, acao_atividade_lista, acao_aviso_celular
from .claude import (acao_claude_cancelar, acao_claude_perguntas, acao_claude_permissao,
                     acao_claude_responder, acao_claude_tarefa, acao_claude_trabalhos, preparar_claude_tarefa)
from .lab import (acao_app_apagar, acao_app_cancelar, acao_app_comando, acao_app_lista, acao_app_parar,
                  acao_app_publicar, acao_app_reiniciar, acao_app_restaurar, preparar_app_apagar,
                  preparar_app_publicar)
from .local import acao_local_processar
from .pc import acao_pc_cancelar, acao_pc_desligar, acao_pc_estado, acao_pc_ligar, acao_pc_reiniciar
from .sistema import (acao_gasto_api, acao_servico_journal, acao_servico_logs, acao_servico_reiniciar,
                      acao_sistema_processos, acao_sistema_rede, acao_sistema_sensores,
                      acao_status_containers, acao_status_recursos, acao_status_servicos, acao_status_sistema,
                      preparar_servico_reiniciar)
from .stacks import (acao_stack_aplicar, acao_stack_desfazer, acao_stack_editar, acao_stack_fotos,
                     preparar_stack_aplicar)


# o risco: consulta só lê; muda mexe em algo que tem volta; destrutivo não tem volta e sempre pede o
# celular (a não ser ao painel, onde quem confirma, na tela, é o próprio dono)
CONSULTA, MUDA, DESTRUTIVO = "consulta", "muda", "destrutivo"
RISCOS = (CONSULTA, MUDA, DESTRUTIVO)
# quem usa: o painel e a Atena; o instalador monta o token de cada um com as ações do perfil dele
P, A, PA = frozenset({"painel"}), frozenset({"atena"}), frozenset({"painel", "atena"})
LAB = "lab"   # só com o lab (./install.sh --lab): a Atena as ganha no 88-lab.sh


class Acao(NamedTuple):
    """Sem preparar, a ação roda na hora: funcao(cliente, params). Com preparar, vira um pedido:
    preparar(cliente, params) valida e descreve, e funcao(pedido) roda depois da aprovação no celular (se o
    token pedir ou se ela for destrutiva) ou na hora."""
    funcao: Callable
    ajuda: str
    preparar: Callable | None = None
    risco: str = CONSULTA
    perfis: frozenset = frozenset()
    modulo: str = ""


def do_perfil(perfil):
    """As ações de um perfil, na ordem da lista: painel, atena ou atena-lab (as do lab, para a Atena)."""
    if perfil == "atena-lab":
        return [n for n, a in ACOES.items() if "atena" in a.perfis and a.modulo == LAB]
    if perfil == "atena":
        return [n for n, a in ACOES.items() if "atena" in a.perfis and a.modulo != LAB]
    return [n for n, a in ACOES.items() if perfil in a.perfis]


ACOES = {
    # central do painel: o dono vê e decide o que espera por ele, e lê o registro do executor
    "aprovacoes.lista":  Acao(acao_aprovacoes_lista, "pedidos esperando o dono (aprovação ou pergunta do Claude Code), "
                              "de todos os clientes das suas zonas, e os que passaram há pouco", None, CONSULTA, P),
    "aprovacoes.decidir": Acao(acao_aprovacoes_decidir, "decide um pedido de outro cliente como o dono no celular "
                               "(pedido, decisao: aprovar|recusar|responder, resposta? para pergunta)", None, MUDA, P),
    "atividade.lista":   Acao(acao_atividade_lista, "registro do executor, do mais novo ao mais velho "
                              "(linhas? 1-1000, cliente?, so_erros?)", None, CONSULTA, P),
    "aviso.celular":     Acao(acao_aviso_celular, "manda um aviso ao celular do dono (titulo, texto?)", None, MUDA, P),
    "status.servicos":   Acao(acao_status_servicos, "estado dos containers das zonas do cliente", None, CONSULTA, PA),
    "status.recursos":   Acao(acao_status_recursos, "CPU, RAM, discos, GPU e temperaturas agora", None, CONSULTA, PA),
    "status.containers": Acao(acao_status_containers, "CPU e RAM de cada container agora", None, CONSULTA, PA),
    "status.sistema":    Acao(acao_status_sistema, "serviços e timers atena-*, e unidades com falha no sistema todo", None, CONSULTA, PA),
    "gasto.api":         Acao(acao_gasto_api, "gasto de API do mês por modelo e por chave, com os tetos", None, CONSULTA, PA),
    "servico.logs":      Acao(acao_servico_logs, "últimas linhas do log de uma stack (stack, linhas<=500)", None, CONSULTA, PA),
    "servico.journal":   Acao(acao_servico_journal,
                              "registro do systemd de qualquer unidade ou do sistema todo (unidade?, linhas<=200, prioridade?, desde?)", None, CONSULTA, PA),
    "arquivo.ler":       Acao(acao_arquivo_ler, "lê qualquer arquivo ou pasta do servidor, menos segredos (caminho)", None, CONSULTA, PA),
    "arquivo.procurar":  Acao(acao_arquivo_procurar, "procura arquivos pelo nome, tipo e data, menos segredos "
                              "(pasta, nome?, tipo? foto|documento|planilha|video|audio, dias?)", None, CONSULTA, PA),
    "arquivo.entregar":  Acao(acao_arquivo_entregar, "copia um arquivo do servidor para /opt/data/entregas, para olhar "
                              "ou mandar ao dono (caminho); texto sai com segredos ocultos", None, CONSULTA, A),
    "local.processar":   Acao(acao_local_processar, "processa um texto privado num modelo que roda em casa, sem nuvem "
                              "(instrucao, arquivo ou texto, modelo? local|pc, parte?)", None, CONSULTA, A),
    "arquivo.buscar":    Acao(acao_arquivo_buscar, "procura um texto nos arquivos de uma pasta, menos segredos (pasta, texto)", None, CONSULTA, PA),
    "sistema.processos": Acao(acao_sistema_processos, "processos que mais usam CPU ou RAM (ordem?, quantos?)", None, CONSULTA, PA),
    "sistema.rede":      Acao(acao_sistema_rede, "endereços e portas abertas do servidor", None, CONSULTA, PA),
    "sistema.sensores":  Acao(acao_sistema_sensores, "temperaturas da CPU, NVMe, GPU e placa, e as ventoinhas", None, CONSULTA, PA),
    "stack.editar":      Acao(acao_stack_editar, "edita um arquivo de uma stack da zona apps, com foto antes (stack, "
                              "arquivo relativo à pasta, conteudo ou trocar=[{de, para}]); não aplica sozinho", None, MUDA, PA),
    "stack.aplicar":     Acao(acao_stack_aplicar, "confere as regras e sobe a stack com docker compose up -d --build, "
                              "em segundo plano (stack)", preparar_stack_aplicar, MUDA, PA),
    "stack.fotos":       Acao(acao_stack_fotos, "edições guardadas de uma stack, da mais nova para a mais velha (stack)", None, CONSULTA, PA),
    "stack.desfazer":    Acao(acao_stack_desfazer, "volta um arquivo da stack como estava antes da última edição, ou de "
                              "uma foto (stack, foto?)", None, MUDA, PA),
    "servico.reiniciar": Acao(acao_servico_reiniciar, "reinicia os containers de uma stack (stack)", preparar_servico_reiniciar, MUDA, PA),
    "pc.estado":         Acao(acao_pc_estado, "PC da rede de casa ligado? LM Studio respondendo?", None, CONSULTA, PA),
    "pc.ligar":          Acao(acao_pc_ligar, "liga o PC pela rede (Wake-on-LAN)", None, MUDA, PA),
    "pc.desligar":       Acao(acao_pc_desligar, "desliga o PC em 60 s (pc.cancelar desiste)", None, MUDA, PA),
    "pc.reiniciar":      Acao(acao_pc_reiniciar, "reinicia o PC em 60 s (pc.cancelar desiste)", None, MUDA, PA),
    "pc.cancelar":       Acao(acao_pc_cancelar, "cancela um desligamento ou reinício do PC ainda na contagem", None, MUDA, PA),
    # Claude Code e apps do lab (módulo lab, ./install.sh --lab): o Claude Code roda como atena-claude,
    # sem sudo e sem Docker, com sandbox; no lab, desfazer é git.
    "claude.tarefa":     Acao(acao_claude_tarefa,
                              "Claude Code trabalha sozinho numa pasta do lab (pedido, projeto, conta? = uma de "
                              "claude.trabalhos, modelo? fable|opus|sonnet|haiku, esforco? low|medium|high|xhigh|max, "
                              "minutos? 5-600, skill? = uma de claude.trabalhos, somente_plano?, continuar?, "
                              "publicar? = publica quando terminar bem)", preparar_claude_tarefa, MUDA, PA, LAB),
    "claude.trabalhos":  Acao(acao_claude_trabalhos, "trabalhos do Claude Code (10 últimos), as contas e as que têm login", None, CONSULTA, PA, LAB),
    "claude.perguntas":  Acao(acao_claude_perguntas, "perguntas do Claude Code esperando resposta do dono", None, CONSULTA, A, LAB),
    "claude.responder":  Acao(acao_claude_responder, "responde uma pergunta do Claude Code (pergunta, resposta, quem: dono|atena)", None, MUDA, A, LAB),
    "claude.cancelar":   Acao(acao_claude_cancelar, "interrompe um trabalho do Claude Code (pedido)", None, MUDA, PA, LAB),
    "app.publicar":      Acao(acao_app_publicar, "publica um projeto do lab na rede de casa: constrói pelo Dockerfile "
                              "e roda na zona lab (projeto, porta? 8000-8999)", preparar_app_publicar, MUDA, PA, LAB),
    "app.parar":         Acao(acao_app_parar, "tira do ar um app publicado do lab; dados e imagem ficam (projeto)", None, MUDA, PA, LAB),
    "app.reiniciar":     Acao(acao_app_reiniciar, "reinicia um app do lab; se estava parado, sobe de novo com a imagem "
                              "que já existe (projeto)", None, MUDA, PA, LAB),
    "app.cancelar":      Acao(acao_app_cancelar, "para tudo o que está em andamento num projeto do lab: trabalho do "
                              "Claude Code, construção e pedidos esperando o celular (projeto)", None, MUDA, PA, LAB),
    "app.apagar":        Acao(acao_app_apagar, "apaga partes de um projeto do lab (projeto, partes: docker = container "
                              "e imagem; dados = volume, sem volta; codigo = pasta vai para a lixeira por 30 dias)", preparar_app_apagar, DESTRUTIVO, PA, LAB),
    "app.restaurar":     Acao(acao_app_restaurar, "traz da lixeira o código de um projeto apagado (projeto)", None, MUDA, PA, LAB),
    "app.comando":       Acao(acao_app_comando, "roda um comando dentro de um app do lab no ar (projeto, comando = "
                              "texto para sh -c ou lista, segundos? 1-120)", None, MUDA, PA, LAB),
    "app.lista":         Acao(acao_app_lista, "projetos do lab: app no ar, endereço, código, dados guardados, o que "
                              "está em andamento e a lixeira", None, CONSULTA, PA, LAB),
}

# Ações que só o próprio executor cria (ninguém pede por POST /acao).
INTERNAS = {
    "claude.permissao": acao_claude_permissao,
}
