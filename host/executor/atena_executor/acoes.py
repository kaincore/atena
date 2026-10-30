"""A lista fechada de ações: nome → (função, ajuda, preparar). Com preparar, a ação é um pedido: o
preparar valida e devolve o texto da aprovação, e a função roda depois (aprovada ou sem aprovação)."""

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


# nome: (função, descrição, preparar). Sem preparar, a ação roda na hora: função(cliente, params).
# Com preparar, vira um pedido: preparar(cliente, params) valida e descreve, e função(pedido) roda
# depois da aprovação no celular (se o token do cliente exigir) ou na hora.
ACOES = {
    # central do painel: o dono vê e decide o que espera por ele, e lê o registro do executor
    "aprovacoes.lista":  (acao_aprovacoes_lista, "pedidos esperando o dono (aprovação ou pergunta do Claude Code), "
                          "de todos os clientes das suas zonas, e os que passaram há pouco", None),
    "aprovacoes.decidir": (acao_aprovacoes_decidir, "decide um pedido de outro cliente como o dono no celular "
                           "(pedido, decisao: aprovar|recusar|responder, resposta? para pergunta)", None),
    "atividade.lista":   (acao_atividade_lista, "registro do executor, do mais novo ao mais velho "
                          "(linhas? 1-1000, cliente?, so_erros?)", None),
    "aviso.celular":     (acao_aviso_celular, "manda um aviso ao celular do dono (titulo, texto?)", None),
    "status.servicos":   (acao_status_servicos, "estado dos containers das zonas do cliente", None),
    "status.recursos":   (acao_status_recursos, "CPU, RAM, discos, GPU e temperaturas agora", None),
    "status.containers": (acao_status_containers, "CPU e RAM de cada container agora", None),
    "status.sistema":    (acao_status_sistema, "serviços e timers atena-*, e unidades com falha no sistema todo", None),
    "gasto.api":         (acao_gasto_api, "gasto de API do mês por modelo e por chave, com os tetos", None),
    "servico.logs":      (acao_servico_logs, "últimas linhas do log de uma stack (stack, linhas<=500)", None),
    "servico.journal":   (acao_servico_journal,
                          "registro do systemd de qualquer unidade ou do sistema todo (unidade?, linhas<=200, prioridade?, desde?)",
                          None),
    "arquivo.ler":       (acao_arquivo_ler, "lê qualquer arquivo ou pasta do servidor, menos segredos (caminho)", None),
    "arquivo.procurar":  (acao_arquivo_procurar, "procura arquivos pelo nome, tipo e data, menos segredos "
                          "(pasta, nome?, tipo? foto|documento|planilha|video|audio, dias?)", None),
    "arquivo.entregar":  (acao_arquivo_entregar, "copia um arquivo do servidor para /opt/data/entregas, para olhar "
                          "ou mandar ao dono (caminho); texto sai com segredos ocultos", None),
    "local.processar":   (acao_local_processar, "processa um texto privado num modelo que roda em casa, sem nuvem "
                          "(instrucao, arquivo ou texto, modelo? local|pc, parte?)", None),
    "arquivo.buscar":    (acao_arquivo_buscar, "procura um texto nos arquivos de uma pasta, menos segredos (pasta, texto)", None),
    "sistema.processos": (acao_sistema_processos, "processos que mais usam CPU ou RAM (ordem?, quantos?)", None),
    "sistema.rede":      (acao_sistema_rede, "endereços e portas abertas do servidor", None),
    "sistema.sensores":  (acao_sistema_sensores, "temperaturas da CPU, NVMe, GPU e placa, e as ventoinhas", None),
    "stack.editar":      (acao_stack_editar, "edita um arquivo de uma stack da zona apps, com foto antes (stack, "
                          "arquivo relativo à pasta, conteudo ou trocar=[{de, para}]); não aplica sozinho", None),
    "stack.aplicar":     (acao_stack_aplicar, "confere as regras e sobe a stack com docker compose up -d --build, "
                          "em segundo plano (stack)", preparar_stack_aplicar),
    "stack.fotos":       (acao_stack_fotos, "edições guardadas de uma stack, da mais nova para a mais velha (stack)", None),
    "stack.desfazer":    (acao_stack_desfazer, "volta um arquivo da stack como estava antes da última edição, ou de "
                          "uma foto (stack, foto?)", None),
    "servico.reiniciar": (acao_servico_reiniciar, "reinicia os containers de uma stack (stack)",
                          preparar_servico_reiniciar),
    "pc.estado":         (acao_pc_estado, "PC da rede de casa ligado? LM Studio respondendo?", None),
    "pc.ligar":          (acao_pc_ligar, "liga o PC pela rede (Wake-on-LAN)", None),
    "pc.desligar":       (acao_pc_desligar, "desliga o PC em 60 s (pc.cancelar desiste)", None),
    "pc.reiniciar":      (acao_pc_reiniciar, "reinicia o PC em 60 s (pc.cancelar desiste)", None),
    "pc.cancelar":       (acao_pc_cancelar, "cancela um desligamento ou reinício do PC ainda na contagem", None),
    # Claude Code e apps do lab (módulo lab, ./install.sh --lab): o Claude Code roda como atena-claude,
    # sem sudo e sem Docker, com sandbox; no lab, desfazer é git.
    "claude.tarefa":     (acao_claude_tarefa,
                          "Claude Code trabalha sozinho numa pasta do lab (pedido, projeto, conta? = uma de "
                          "claude.trabalhos, modelo? fable|opus|sonnet|haiku, esforco? low|medium|high|xhigh|max, "
                          "minutos? 5-600, skill? = uma de claude.trabalhos, somente_plano?, continuar?, "
                          "publicar? = publica quando terminar bem)",
                          preparar_claude_tarefa),
    "claude.trabalhos":  (acao_claude_trabalhos, "trabalhos do Claude Code (10 últimos), as contas e as que têm login", None),
    "claude.perguntas":  (acao_claude_perguntas, "perguntas do Claude Code esperando resposta do dono", None),
    "claude.responder":  (acao_claude_responder, "responde uma pergunta do Claude Code (pergunta, resposta, quem: dono|atena)", None),
    "claude.cancelar":   (acao_claude_cancelar, "interrompe um trabalho do Claude Code (pedido)", None),
    "app.publicar":      (acao_app_publicar, "publica um projeto do lab na rede de casa: constrói pelo Dockerfile "
                          "e roda na zona lab (projeto, porta? 8000-8999)", preparar_app_publicar),
    "app.parar":         (acao_app_parar, "tira do ar um app publicado do lab; dados e imagem ficam (projeto)", None),
    "app.reiniciar":     (acao_app_reiniciar, "reinicia um app do lab; se estava parado, sobe de novo com a imagem "
                          "que já existe (projeto)", None),
    "app.cancelar":      (acao_app_cancelar, "para tudo o que está em andamento num projeto do lab: trabalho do "
                          "Claude Code, construção e pedidos esperando o celular (projeto)", None),
    "app.apagar":        (acao_app_apagar, "apaga partes de um projeto do lab (projeto, partes: docker = container "
                          "e imagem; dados = volume, sem volta; codigo = pasta vai para a lixeira por 30 dias)",
                          preparar_app_apagar),
    "app.restaurar":     (acao_app_restaurar, "traz da lixeira o código de um projeto apagado (projeto)", None),
    "app.comando":       (acao_app_comando, "roda um comando dentro de um app do lab no ar (projeto, comando = "
                          "texto para sh -c ou lista, segundos? 1-120)", None),
    "app.lista":         (acao_app_lista, "projetos do lab: app no ar, endereço, código, dados guardados, o que "
                          "está em andamento e a lixeira", None),
}

# Ações que só o próprio executor cria (ninguém pede por POST /acao).
INTERNAS = {
    "claude.permissao": acao_claude_permissao,
}
