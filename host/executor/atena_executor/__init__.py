"""Atena: executor de ações do servidor.

O único caminho para os clientes (o Hermes e o painel) mexerem no servidor. Ouve um socket unix e só
conhece uma lista fechada de ações. Nunca usa shell: cada ação é um comando fixo, com parâmetros
validados contra o que existe de verdade. Cada cliente tem um token próprio, e cada token só pode pedir
as ações e as zonas dele.

O programa é o /usr/local/sbin/atena-executor; o código fica neste pacote, um módulo por assunto, de
baixo para cima (um módulo só importa dos que vêm antes dele):
  base        atena.conf, registro, comandos (rodar) e o Erro que vira a resposta HTTP
  segredos    o que nunca se lê e o que sai oculto (***)
  inventario  o que existe no servidor: containers, zonas e o IP de casa
  celular     avisos e botões no celular (ntfy)
  tokens      os tokens dos clientes
  pedidos     ações que esperam a aprovação do dono, e quem vê qual pedido
  sistema     estado, recursos, sensores, serviços, processos, rede e gasto
  arquivos    ler, procurar e entregar arquivos
  pc          o PC da rede de casa
  local       texto privado num modelo que roda em casa
  stacks      as stacks de apps que a Atena edita
  lab         os apps do lab
  claude      o Claude Code no lab
  atena       a Atena no painel: as conversas, a agenda e o chat (a API do Hermes)
  central     a central do painel: aprovações e atividade
  acoes       a lista fechada de ações
  servidor    o socket, o protocolo e a linha de comando
"""
