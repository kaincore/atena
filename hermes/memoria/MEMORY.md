Servidor: a lista de containers e zonas muda; pergunte com status.servicos em vez de guardar de memória. Gasto de API: gasto.api (os logs do litellm só listam requisições). CPU e RAM por container: status.containers.
§
Executor (habilidade servidor-atena), sempre pelo /opt/data/scripts/acao.py, que mostra o código HTTP: consultas, servico.reiniciar e o PC rodam direto, sem celular. Lê qualquer arquivo e log, menos segredos e bancos de dados. Foto, PDF e planilha só saem (arquivo.entregar) de /opt/atena/docs, dos projetos do lab e do seu espaço; para ler PDF, Word e Excel, traga a cópia e use o Python das ferramentas (habilidade notas).
§
O painel do servidor (se instalado) abre pelo Tailscale, na porta 3100. Aprovações, agenda e histórico de lá são do dono: você não decide pedidos.
§
Lembretes e tarefas agendadas: ferramenta cronjob_manage (action create, schedule com data ISO, deliver: ntfy, como manda o SOUL). O comando hermes não existe no seu terminal. Jobs fixos: a ronda (a cada 3 min; as falhas dela vão para o ntfy) e o bom-dia (8h, sem IA, direto no Telegram).