# Mudanças

## 0.28.0 (2026-10-30)

A terceira parte da Onda 6: o servidor se atualiza pelo repositório, num comando só, e as regras da Atena ficam só para leitura. É o portão da onda: pela primeira vez, o servidor está igual ao repositório.

- **`sudo ./aplicar`:** deixa o servidor igual ao repositório. Primeiro mostra o plano (o que grava, o que guarda no backup, o que fica como está e o que reinicia) e pede confirmação. Guarda um backup antes de mexer, e o `--desfazer` volta a ele. Reinicia só o que mudou de verdade e desfaz sozinho se um passo falha. Ele substitui os scripts avulsos de cada troca. Ficam de fora o `daemon.json` (reiniciaria todos os containers), a stack que ainda não existe e a memória da Atena, que só ganha a semente quando falta.
- **O SOUL e as habilidades da Atena só para leitura:** o compose dela os monta assim dentro do container. Um texto que ela leia não consegue reescrever as regras dela, e o "aprendizado" do Hermes também não. O curador já tinha reescrito uma habilidade sozinho, em 17/10. Quem as muda é o `./aplicar`, a partir do repositório.
- Testado:
  - 28 verificações novas: `teste_aplicar.py`, num servidor de mentira, cobre aplicar, desfazer byte a byte, a falha que desfaz sozinha, o que reinicia, a trava e o sudo. `teste_compose.py` cobre as montagens só para leitura;
  - cada commit rodado sozinho;
  - o CI reproduzido com `tools/ci-local.sh`.

  No servidor de origem:
  - o primeiro `sudo ./aplicar` de verdade gravou 3 arquivos (o do SSH, só nos comentários, o compose e o SOUL da Atena), conferiu o SSH com `sshd -t` e subiu a Atena de novo, saudável;
  - de dentro do container, gravar, apagar e mover o SOUL e as habilidades foi recusado, e a memória e as notas continuam graváveis;
  - a conferência de depois, como root, não achou nenhuma diferença.

  Sem testar ainda: o `--desfazer` no servidor de verdade (testado só no de mentira).

## 0.27.0 (2026-10-30)

A segunda parte da Onda 6: o instalador serve para o servidor de verdade, e o que era escrito à mão sai do `atena.conf`.

- **O instalador lê o `/etc/atena/atena.conf`** quando a pasta do repositório não tem um `atena.conf`. Antes, num servidor já instalado, ele não rodava sem uma cópia.
- **O PC da rede de casa sai do `atena.conf`:** com `ATENA_PC_IP`, ele entra em cinco lugares, e todos vêm do arquivo. São o modelo `pc` no LiteLLM, a exceção do firewall dos containers (só a porta do LM Studio), a lista e a chave da Atena, e o plano B. O plano B é uma chave nova, `ATENA_PC_RESERVA`, vazia por padrão: com um modelo da nuvem, o texto privado sai de casa.
- **Blocos que só entram com uma chave:** num modelo, as linhas entre `{{SE ATENA_X}}` e `{{FIM}}` só ficam quando `ATENA_X` tem valor. O instalador e o `./aplicar` preenchem os modelos pelo mesmo código (`install/estado.py`).
- **Lembrete de uma vez só some 1 hora depois de rodar.** Antes, o Hermes guardava o agendamento por 7 dias. Os diários, semanais e mensais continuam.
- Testado:
  - 24 verificações novas: `teste_estado.py` (os blocos e o LiteLLM sem PC, com PC e com plano B), `teste_instalador.py` (qual `atena.conf` o `install.sh` lê), `teste_firewall.py` e `teste_configurar.py` (contra um iptables e um docker de mentira);
  - cada commit rodado sozinho;
  - o CI reproduzido com `tools/ci-local.sh`.

  No servidor de origem:
  - um script com backup e `--desfazer`, ensaiado antes numa cópia dos arquivos, pôs os scripts e as unidades do repositório e trocou os 5 complementos do executor feitos à mão por 1. As 22 regras do firewall e as permissões do executor saíram iguais às de antes, menos as pastas do Arca;
  - o compose da Atena passou a ser o do repositório com o mesmo hash, e ela não foi recriada;
  - o LiteLLM e a Atena reiniciaram saudáveis com o modelo `pc`, e as chaves trocaram o nome antigo por ele;
  - o `./aplicar --conferir` foi de 31 diferenças para 1: o `sshd_config.d`, só nos comentários.

  Sem testar ainda: uma chamada ao `pc` com o PC ligado, o plano B com ele desligado e o instalador num servidor novo.

## 0.26.0 (2026-10-30)

O começo da Onda 6, o estado desejado: dá para saber, sem mudar nada, o quanto o servidor se afastou do repositório.

- **`sudo ./aplicar --conferir`:** compara o servidor com o que o instalador poria nele, por parte (host, executor, stacks, painel, Atena e lab). Ele lista o que difere (inclusive o modo e o dono), o que falta e o que sobra, e diz quando a diferença está só nos comentários. Sobra é um drop-in feito à mão, um módulo velho do executor ou um script `atena-*` antigo. Ele também conta as cópias `.antes-*` que as trocas deixaram. O `--diff` mostra o que mudaria. Nada muda no servidor; a aplicação por partes vem na próxima parte da onda.
- **O estado desejado num lugar só:** o `install/estado.py` descreve cada arquivo que o repositório põe no servidor, com o conteúdo preenchido pelo `/etc/atena/atena.conf`. O teste confere que ele anda junto com as etapas do instalador, e um arquivo novo que fique de fora quebra o teste.
- Testado:
  - `teste_estado.py`, 44 verificações. Rodando os trechos do próprio instalador, o estado preenche os modelos, tira a GPU e monta o lab.json como ele. Num servidor de mentira, cada estrago aparece no lugar certo, e a linha de comando sai com o código certo;
  - cada commit rodado sozinho;
  - o CI reproduzido com `tools/ci-local.sh`.

  No servidor de origem, sem sudo: 28 diferenças, cada uma conferida à mão contra o `--diff`, e 15 arquivos que só o root lê. Os arquivos da Atena foram conferidos pelo container: são iguais ao repositório, menos as ferramentas Python dela, que faltam.

  Sem testar ainda: o `--conferir` com sudo no servidor de origem.

## 0.25.0 (2026-10-30)

A Atena afinada: mais barata por conversa, falhando rápido e dizendo que falhou, com a memória de acordo com o SOUL e o bom-dia de volta.

- **O cache cobre a conversa inteira:** o Hermes marca o cache da Anthropic ao longo da conversa, mas só quando sabe que o modelo é Claude, e pelo nome ("haiku") ele não sabia. Com `prompt_caching` nos modelos do LiteLLM, o histórico e os resultados das ferramentas também vêm do cache. Numa conversa de teste, a segunda volta leu 99,9% da entrada do cache e custou 12 vezes menos que a primeira.
- **Falha rápida, sem o plano B que não funcionava:** o Haiku espera 90 s (o Sonnet e o Opus, 180 s), com uma repetição, no lugar de 600 s com duas. O plano B haiku→local saiu: o modelo local não comporta o prompt da Atena. Uma falha chega em até ~3 min, e não em 5 a 9.
- **As falhas da ronda chegam pelo ntfy**, e não pelo Telegram da Atena que não está respondendo.
- **O `acao.py`:** a Atena chama o executor por ele, e não mais por `curl -s`. A primeira linha da saída é o código HTTP, e o token nunca passa pelo terminal dela.
- **O bom-dia volta, sem IA:** às 8h, o `bom_dia.py` lê o servidor e manda no Telegram, direto, os containers, as temperaturas, o gasto do mês e o Claude Code da noite. Ele chega mesmo com a IA fora.
- **Uma semente para a memória, com teste:** `hermes/memoria` entra quando a Atena ainda não tem memória. O `teste_memoria.py` confere os limites, o formato e o que não pode voltar: a personalidade antiga, o "deliver origin", o painel "não iniciado", o Arca e o curl. Ele também roda na memória viva.
- Testado:
  - `teste_scripts.py`: o `acao.py` e o bom-dia contra um executor e um LiteLLM de mentira, com o executor e a IA fora;
  - `teste_memoria.py`;
  - cada commit rodado sozinho;
  - o CI reproduzido com `tools/ci-local.sh`.

  No servidor de origem:
  - o LiteLLM e a Atena reiniciados com a configuração nova e saudáveis;
  - a conversa de teste do cache;
  - o bom-dia gerado com os dados reais e o job criado;
  - a ronda com `failure_deliver: ntfy`;
  - a memória reescrita, com o teste passando nela.

  Sem testar ainda: a meta de custo, menos de US$ 0,006 por conversa ao longo de uma semana.

  Ficou para a Onda 6: o SOUL e as habilidades só para leitura. Mudar o dono dos arquivos não protege, porque a pasta é da Atena e ela apaga e recria. Isso foi testado e desfeito. Só um volume montado como somente leitura protege, e ele muda a ordem do instalador.

## 0.24.0 (2026-10-30)

As travas: o que a Atena e as stacks podem tocar fica do tamanho certo, e o que trava sem ninguém ver passa a fechar sozinho (painel 0.15.0). Antes de ela ganhar casa, e-mail ou voz, nenhum texto lido por ela deveria conseguir trocar a imagem de outro serviço, copiar um banco ou aprovar o próprio pedido.

- **Imagem só com o nome da própria stack:** uma stack da zona apps podia construir uma imagem com o nome da do LiteLLM, do Hermes ou do painel, e a cópia subiria na próxima recriação deles (até pelo `atena-reconciliar`, no boot). Agora, com `build`, a imagem se chama `atena-apps/<stack>` ou `atena-apps/<stack>-<algo>`; sem `build`, uma imagem que só existe construída no servidor (`atena/`, `atena-lab/`, `atena-apps/` de outra stack) não passa; `build.tags`, `cache_from` e `cache_to` também não.
- **Banco de dados não sai:** o `arquivo.entregar` copiava qualquer arquivo fora da lista do que nunca se lê, inclusive o `user.db` do ntfy (os tokens em claro) e o cache dele (os botões de aprovação, o que deixava a Atena aprovar o próprio pedido), o Postgres do LiteLLM e os SQLite do painel e da Open WebUI. Agora o conteúdo de SQLite, Postgres e Redis não sai nem lido nem copiado, e a busca não entra neles.
- **Binário só das pastas de entrega:** texto continua saindo de qualquer lugar, com os segredos ocultos; foto, PDF e planilha, que saem inteiros, só de `/opt/atena/docs`, dos projetos do lab, do espaço da Atena e das pastas em `ATENA_PASTAS_ENTREGA` (novo no `atena.conf`).
- **O Arca sai:** a stack, as ações `arca.*` e as linhas da Atena. Num servidor que já o tem, nada é apagado; um token antigo que ainda liste `arca.*` não quebra nada.
- **O Claude Code não trava mais o projeto:** um trabalho tem prazo (os minutos dele mais 15 min; na fila, 10 h 15), e o runner, ao voltar de uma queda de energia, fecha como interrompido o que ficou pela metade (com a conversa, para continuar, e os commits). O `atena-claude.path` também vigia esses trabalhos, para o runner subir sozinho. Um cancelar sem resposta do runner fecha em 5 min.
- **Uma publicação por projeto:** dois `app.publicar` aprovados juntos rodavam dois `docker compose up --build` na mesma pasta; o segundo agora recebe 409.
- **Healthcheck nos apps do lab:** o compose gerado confere se o app atende na porta (python3, node ou wget), a menos que o Dockerfile tenha `HEALTHCHECK` próprio. Os apps no ar ganham na próxima publicação.
- **Um `pedidos.json` ilegível** (cortado numa queda) não some mais em silêncio: vai para o lado, com a data no nome, e o dono é avisado pelo ntfy, que o executor tenta de novo por até 1 h.
- **Painel 0.15.0:**
  - a trava da senha errada vale por entrada: errar no Wi-Fi não tranca o dono fora de casa. A entrada vem do socket, nunca de um cabeçalho, e o banco migra sozinho.
  - Editar um agendamento pausado não o religa.
  - A execução que o reinício do painel interrompeu vira "interrompida" (antes, ficava "executando" para sempre).
  - A ação entra no histórico antes de ir ao executor: um prazo esgotado (agora 504, "confira antes de pedir de novo") ou um erro não a apagam mais.
- Testado: cada um dos 13 commits rodado sozinho (os testes do painel e o tsc, ou os de Python e o ruff, na árvore daquele commit). Os testes novos:
  - 7 composes ruins e 2 bons com o `docker compose config` de verdade;
  - bancos de mentira de cada tipo e as pastas de entrega;
  - o prazo na fila, no runner e no cancelar;
  - um runner de verdade morto com SIGKILL no meio de um trabalho e o seguinte fechando-o;
  - duas publicações do mesmo projeto;
  - o healthcheck rodado com `sh -c` contra uma porta aberta e uma fechada, com python3, só node, só wget (GNU e busybox) e sem nenhum;
  - o `pedidos.json` cortado e de outro formato;
  - 7 testes novos do painel (56 no total), um deles subindo o `principal.ts` de verdade.
  
  O CI foi reproduzido com `tools/ci-local.sh`. No servidor de origem, o painel 0.15.0 está no ar e saudável, com o banco migrado (a coluna `entrada`). Sem testar ainda: o executor, o runner e o `.path` novos no servidor (dependem do script com sudo) e as provas lá dentro (a imagem trocada e a cópia de banco recusadas pela Atena de verdade).

## 0.23.0 (2026-10-29)

O servidor que volta inteiro de um desligamento sujo. Depois de um corte de energia, o Docker já religou o LiteLLM sem a rede da zona (sem internet nem porta), e a Atena ficou muda por horas enquanto tudo parecia em pé.

- **O reconciliador** (`atena-reconciliar`, timer): compara as redes e as portas de cada container com o compose da stack. 3 min depois do boot, recria uma vez o que voltou errado e avisa; depois, de 5 em 5 min, só avisa, uma vez por problema. Nunca liga o que o dono parou nem cria o que sumiu. `--so-ver` mostra sem mexer.
- **Healthcheck em todo serviço da plataforma:** LiteLLM, Atena (o estado que o gateway grava, com o Telegram conectado), Ollama, Whisper, voz, Beszel e o agente. Dos 17 containers, só 7 diziam se estavam doentes.
- **A virada do mês espera:** se o servidor estava desligado no dia 1º, a virada roda no boot, espera o Redis e o LiteLLM e tenta de novo de 5 em 5 min; antes, falhava calada e os tetos por modelo ficavam presos no mês anterior.
- **O Docker só sobe com o `/srv` montado** (`RequiresMountsFor`): sem o disco de dados, os serviços ficam parados em vez de criar bancos vazios no disco do sistema.
- **A ronda espera o LiteLLM:** com ele fora (ou ainda subindo no boot), ela repete a última saída, e a mudança espera a próxima volta, em vez de acordar a Atena só para falhar e perder o aviso.
- Testado: `tests/host/teste_reconciliar.py` (18 casos, com um docker de mentira) e `tests/hermes/teste_ronda.py` (3 casos novos, com um LiteLLM de mentira); ruff e shellcheck limpos; `systemd-analyze verify` das unidades novas; o CI reproduzido com `tools/ci-local.sh`. No servidor de origem: cada healthcheck rodado dentro do container e os 7 serviços recriados e saudáveis; a ronda nova no ar; `atena-reconciliar --so-ver` sem diferença. Sem testar ainda: o reconciliador, a virada e o `RequiresMountsFor` instalados e passando por um boot de verdade (dependem do script de instalação com sudo).

## 0.22.1 (2026-10-29)

Correções de segurança nas imagens, sem mudar comportamento (painel 0.14.1).

- **Node 22.23.4** no painel e no Arca: corrige 4 falhas altas (Brotli com execução remota, dois desvios na conferência do nome do host no TLS e um NUL no dns) e 3 médias. As imagens ganham tags novas (painel 0.14.1, Arca 1.1.1), e as antigas ficam no Docker para voltar. O CI e o `tools/ci-local.sh` testam o painel no mesmo Node.
- **Open WebUI 0.12.5:** a 0.12.2 corrige o GHSA-3vvh, e a 0.12.0, a 0.12.4 e a 0.12.5 trazem correções de segurança ainda não divulgadas. A partida da 0.12 migra o banco e não há volta: antes de atualizar, guarde a pasta de dados inteira.
- Testado: os 49 testes do painel no `node:22.23.4-alpine3.24`; a imagem do Arca construída e respondendo 200 num container sem rede; o CI reproduzido com `tools/ci-local.sh`. No servidor de origem: o painel 0.14.1 saudável pela etapa da rede de casa, o Arca 1.1.1 respondendo 200, os dois no Node 22.23.4; o Open WebUI 0.12.5 com as 8 migrações sem erro e `/health` 200, depois de guardar a pasta de dados. Sem testar: entrar no Open WebUI e conversar; uma instalação nova numa VM.

## 0.22.0 (2026-10-23)

O Início que não tranquiliza à toa e põe o que pede você no alto (painel 0.14.0). Saiu de uma crítica da tela, em que o dono escolheu as quatro frentes, a letra grega como adorno e os números contando da última leitura.

- **A frase honesta:** "Tudo em ordem" só aparece quando as leituras do servidor, dos serviços, do systemd e das aprovações vieram. Com o executor fora, a frase diz "Não consegui ler o servidor agora.", e o erro aparece uma vez, com "Tentar de novo"; com uma leitura faltando, a frase diz qual. No alarme, ela tem no máximo duas frases: o veredito ("O ollama está fora do ar e mais 4 coisas pedem atenção") e o que espera você. Sem a central de aprovações (executor antigo), nada muda.
- **O que pede você no alto:** saiu da margem e virou a rubrica da folha, logo abaixo da frase, na tinta do mais grave, em colunas no PC. Os pedidos dizem quem pediu (Atena, Claude Code), quando vencem (em horas e minutos) e o motivo; o "Ver" abre o próprio pedido nas Aprovações. As leituras passadas do limite entram com o limite escrito, e o "Ver" acende o anel delas.
- **A régua com nomes:** cada sinal é uma tecla que leva ao seu lugar: os pedidos, as zonas, o instrumento em miniatura e só as leituras fora do azul, com a letra e o nome curto ("Γ Temp. 88,4 °C"). Sem largura, ela quebra de linha em vez de esconder; e aparece também depois de um salto de rolagem.
- **Números de verdade:** os números contam da última leitura vista no aparelho, nunca do zero; na primeira vez, já nascem certos.
- **Mais quieto e com fim:** o gasto de IA virou uma linha com um medidor só (o de cada modelo fica recolhido), e a folha fecha com o colofão, a hora da leitura. No PC, a agenda e as pendências vão para a margem esquerda; no celular, as pendências sobem logo depois da agenda.
- **Consertos:** a tela que se lê sozinha não tira mais o foco nem pula a página, e devolve o foco pela chave de quem a linha é (nunca à tecla de outro pedido); as teclas discretas, os detalhes, as zonas e as caixas de marcar têm 44 px no celular; a caixa de marcar mostra o foco; a legenda do instrumento funciona pelo teclado; um 401 atrasado de antes da senha não devolve mais a tela de entrada nem estraga a primeira leitura.
- Testado: os 49 testes do painel e o CI reproduzido com `tools/ci-local.sh`; no ensaio, o Início no celular, numa tela média e no PC, claro e escuro, calmo, com problema, sem executor e sem a central de aprovações; roteiros da régua (saltos de rolagem, a releitura descartada no meio), da atualização com o foco numa tecla, na legenda e nos detalhes, do "Ver" até o pedido, da contagem com e sem leitura guardada, do 401 atrasado e de "reduzir movimento"; o foco no "Aprovar" de um pedido quando o de cima sai da lista; as outras telas no celular depois da regra dos 44 px; cada commit intermediário rodado sozinho no ensaio, sem erro no console. Um revisor separado leu o diff e achou quatro defeitos (o mais sério, o foco que caía no "Aprovar" de outro pedido), todos corrigidos e conferidos com os roteiros dele. Sem testar: num celular de verdade, e no servidor de origem (o painel 0.14.0 sobe lá depois desta versão).

## 0.21.0 (2026-10-23)

O Início sem o pilar, mais vivo e sem perder as leituras ao rolar (painel 0.13.0). O dono achou que o pilar sob o instrumento não fazia sentido e pediu a página mais dinâmica, sem perder informação ao rolar e com a informação bem distribuída.

- **Sem o pilar:** no meio da lâmina ficam duas pranchas. A Prancha I é o instrumento com a legenda das letras: no celular, o disco em cima e a legenda embaixo em duas colunas; do PC médio em diante, a legenda dos dois lados. A Prancha II é a escada das zonas com a legenda ao lado.
- **Rolando, nada se perde:** quando o instrumento sai de vista, uma régua desce e fica presa no alto da tela, com um anel pequeno por letra, as leituras, as zonas no ar e os pedidos. Tocar nela volta ao instrumento.
- **Movimento ligado ao dado:** os números contam junto com a tinta (do zero quando o instrumento se grava, do valor de antes quando a leitura muda); tocar numa linha da legenda acende o anel dela; os degraus das zonas se assentam quando aparecem na tela; e a régua de cada nota se estende enquanto a nota entra na tela, ligada à rolagem.
- Testado: os 49 testes do painel e o CI reproduzido com `tools/ci-local.sh`; os cliques de ponta a ponta no celular e no PC; as cenas e o roteiro do traço; um roteiro novo de rolagem no celular, claro e escuro (os números contando, as zonas se assentando, a régua descendo, o toque nela voltando ao instrumento e a legenda acendendo o anel); o Início no celular, numa tela média e no PC, normal e com problema; os commits intermediários rodados sozinhos no ensaio, sem erro no console. No servidor de origem, o painel 0.13.0 subiu saudável pelas duas entradas. Sem testar: o movimento e a rolagem num celular de verdade. Sem revisor separado nesta rodada.

## 0.20.0 (2026-10-23)

O Início como uma lâmina só (painel 0.12.0). O dono não quis os blocos soltos da 0.19.0: a página tinha de ser planejada por inteiro, com o desenho fazendo parte dela, e não como decoração.

- **Sem cartões:** o Início vira uma lâmina composta como uma prancha impressa, sem placas nem sombras. No alto, a data e a frase do dia, fechadas por um filete duplo.
- **O monumento:** no meio, o instrumento do servidor de pé numa haste sobre a escada das zonas (o servidor apoiado nas zonas), com a legenda das letras dos dois lados do disco e linhas de chamada até ele. A haste se desenha depois do instrumento, de cima para baixo.
- **As notas nas margens:** o módulo sem a placa, só o título e o conteúdo no mármore. De um lado, o que pede você e as pendências; do outro, os próximos agendamentos, o gasto e o systemd, separados do monumento por filetes duplos. Numa tela média, o monumento atravessa e as notas vão em duas colunas; no celular, tudo numa coluna, na ordem de leitura.
- Testado: os 49 testes do painel e o CI reproduzido com `tools/ci-local.sh`; os cliques de ponta a ponta no celular e no PC; as cenas e o roteiro do traço no ensaio; o Início fotografado no celular, numa tela média (1100 px) e no PC (1440 px), claro e escuro, normal e com problema (um container caído, uma unidade com falha, a temperatura perto do limite e um disco passado dele). No servidor de origem, o painel 0.12.0 subiu saudável pelas duas entradas. Sem testar: o movimento num celular de verdade. Sem revisor separado nesta rodada.

## 0.19.0 (2026-10-23)

O Início como prancha (painel 0.11.0). O dono pediu o Início redesenhado na mesma forma do traço do sistema, escolheu a prancha entre três caminhos e manteve o gasto, as pendências, os próximos agendamentos e o systemd.

- **A frase do dia:** no alto, a data e uma frase escrita a partir dos dados: primeiro o que está errado (o container que caiu, a unidade que falhou, a leitura que passou do limite), depois o que espera você (aprovações e pendências) e o próximo agendamento. Sem nada errado, "Tudo em ordem".
- **O que pede você:** ao lado da frase (embaixo dela no celular), só quando há algo: os pedidos esperando, o que caiu e o que falhou, com a rachadura. A faixa de aprovações deixa de aparecer no Início, onde repetia o mesmo.
- **As pranchas:** impressas direto na página, sem moldura, com o título embaixo. A Prancha I é o instrumento do servidor, no lugar dos quatro medalhões: a graduação, um anel por leitura (CPU, RAM, temperatura, GPU e cada disco) com a tinta em hachura pintada até o valor no tom do limite, as letras gregas no eixo do zero e a legenda. Na primeira vez ele se grava; depois, quando uma leitura muda, a tinta anda até o valor novo, como um ponteiro. A Prancha II é a crepidoma das zonas.
- Testado: os 49 testes do painel e o CI reproduzido com `tools/ci-local.sh`; os cliques de ponta a ponta no celular e no PC; o Início fotografado no celular e no PC, claro e escuro, normal e com problema (um container caído, uma unidade com falha, a temperatura perto do limite e um disco passado dele); o instrumento quadro a quadro, na primeira vez e numa atualização com a CPU e a RAM subindo; os commits intermediários rodados sozinhos no ensaio, sem erro no console. No servidor de origem, o painel 0.11.0 subiu saudável pelas duas entradas. Sem testar: o movimento num celular de verdade. Sem revisor separado nesta rodada.

## 0.18.0 (2026-10-23)

O traço do sistema (painel 0.10.0). O dono pediu ornamentos dentro do painel com animação feita à mão, "que sejam parte do sistema", e não um enfeite fixo num canto. O ornamento passa a nascer do conteúdo: aparece onde algo acontece, se desenha naquela hora, como pena ou buril, e depois fica quieto. Cada desenho corre uma vez por sessão para cada estado, e as atualizações da tela o mostram pronto.

- **Quem carrega hachura:** a tela que ainda não chegou e o que espera uma resposta curta (abrir um arquivo, procurar, rodar um comando) mostram uma hachura traçada e apagada, uma linha depois da outra.
- **O vazio e o fim:** a lista vazia ganha uma vinheta em xilogravura gravada a buril, em passadas finas na direção da hachura: quatro aves do livro de Pierre Belon de 1555 (domínio público), todas com o nome grego na legenda. A coruja fica nas Aprovações, o galo na Agenda, a andorinha no Lab e a pega na Atividade e no Histórico. A lista longa da Atividade, do Histórico e dos Arquivos termina com um fecho de livro que se desenha quando você chega ao fim.
- **O dado vira desenho:** o container fora do ar e a unidade com falha ganham uma rachadura saindo da borda da linha, como o reboco do afresco. Na Rede, uma esfera armilar mostra um anel por alcance e um ponto por porta aberta, e gira devagar.
- **O gesto deixa um traço:** quando a ação dá certo, um louro coroa o botão ao aprovar ou publicar, um círculo de pena fecha em volta do nome ao reiniciar, e raios saem do medalhão do PC quando ele liga.
- **Por baixo:** o `ornamentos.js` novo; a `gravura()` com o modo buril, o `mostrar()`, a imagem baixada só quando vai para a tela e um ouvinte só de tamanho e de tema para todas (as vinhetas se refazem a cada atualização). A decisão de desenhar sai quando o desenho entra na página, inclusive nas telas da barra montadas antes por trás, e a cópia que a tela refaz no meio continua de onde estava.
- Testado: os 49 testes do painel e o CI reproduzido com `tools/ci-local.sh`; os cliques de ponta a ponta no celular e no PC; um roteiro de cenas novo no ensaio (`tracos.cjs`, com as respostas da API trocadas) que provoca cada traço e fotografa no meio e no fim, no celular claro e no PC escuro; a gravação a buril quadro a quadro; cada um dos sete commits do traço rodado sozinho no ensaio, sem erro no console. No servidor de origem, o painel 0.10.0 subiu saudável e serve o módulo e as vinhetas pelas duas entradas. Sem testar: o movimento num celular de verdade (só no navegador sem tela). Sem revisor separado nesta rodada.

## 0.17.2 (2026-10-22)

A entrada do painel sem moldura, e o reboco só atrás dela (painel 0.9.2). Pedido do dono, que quer fechar a entrada antes de cuidar do fundo do painel.

- **Sem moldura:** a cornija da Sistina em cima e embaixo, com os filetes dos lados no PC, formava um quadrado em volta da entrada e saiu. A entrada fica solta na tela, com as mãos, a centelha e o reboco.
- **O reboco só na entrada:** atrás da entrada, a 5%, derivando devagar; dentro do painel a camada nem é criada, e o chão volta a ser liso.
- O DESIGN.md e os documentos deixam de falar da cornija; a Regra do Meandro que Mede volta a valer sem exceção.
- Testado: os 49 testes do painel e o CI reproduzido com `tools/ci-local.sh`; os cliques de ponta a ponta no celular e no PC; a entrada fotografada no celular e no PC, claro e escuro, sem moldura; no navegador do ensaio, a camada do reboco existe na entrada e não existe dentro do painel; o commit intermediário (só sem a moldura) rodado sozinho no ensaio, sem erro. No servidor de origem, o painel 0.9.2 subiu saudável pelas duas entradas. Sem revisor separado nesta rodada.

## 0.17.1 (2026-10-22)

O fundo e a moldura da entrada do painel (painel 0.9.1). Pedido do dono, que escolheu os três elementos, quase invisíveis e com movimento lento.

- **O reboco:** atrás de toda a interface, o céu da Criação de Adão, da mesma foto das mãos, com as rachaduras de verdade da pintura (`gravuras/reboco.webp`, só máscara, 66 KB). Fica a 3,5% no painel, onde só aparece no chão entre as placas e fica parado, e a 5% na entrada, onde deriva devagar.
- **A centelha:** quando as mãos terminam de se imprimir, uma luz se acende no vão entre os dedos e respira: de dia só um halo azul, à noite um halo e um ponto de luz. Some quando a senha é aceita.
- **A cornija:** a cornija pintada do teto da Sistina (óvulos e dardos, dentículos e o astrágalo de contas), em traço fino, emoldura a entrada em cima e embaixo e se abre do meio para as bordas; no PC, dois filetes de cada lado ligam as cornijas. Ela substitui as faixas de meandro da entrada, e o DESIGN.md passa a dizer que a entrada é a exceção à regra de que o ornamento é sempre o meandro.
- Testado: os 49 testes do painel e o CI reproduzido com `tools/ci-local.sh`; os cliques de ponta a ponta no celular e no PC, sem erro no console; a entrada fotografada no celular e no PC, claro e escuro, e de perto (a cornija e a centelha); o Início no celular e no PC com o reboco; cada um dos três commits do fundo rodado sozinho no ensaio, sem erro. No servidor de origem, o painel 0.9.1 subiu saudável e serve o reboco pelas duas entradas. Sem testar: o movimento num celular de verdade (a deriva do reboco e a respiração da centelha só foram vistas no navegador sem tela). Sem revisor separado nesta rodada.

## 0.17.0 (2026-10-22)

O painel também na rede de casa, e a entrada com as mãos da Criação de Adão (painel 0.9.0).

- **Na rede de casa:** com `ATENA_PAINEL_CASA=sim` no `atena.conf` (padrão: `nao`), o painel também abre em `http://<ATENA_LAN_IP>:3100`, sem o Tailscale. O systemd escuta só no IP de casa (`atena-painel-casa.socket`) e entrega cada visita a um segundo socket do painel (`atena-painel-casa.service`, com o `systemd-socket-proxyd`, como `atena-painel`, sem rede própria e vendo de `/srv/core` só a pasta dos sockets); o ufw abre a porta só para a faixa da rede de casa. Lá é HTTP: o cookie sai sem `Secure`, a senha passa aberta no Wi-Fi e o painel não instala como app. O bloqueio da senha errada vale para as duas entradas. Escolha do dono, que preferiu o HTTP simples a instalar um certificado em cada aparelho; os riscos estão em `docs/pt/seguranca.md`.
- **A entrada:** as mãos de Deus e de Adão da Criação de Adão de Michelangelo, no lugar da Atena Partenos, escolhidas pelo dono depois de ver as duas. A imagem vem de uma foto do afresco (Jörg Bittner Unna, 2011, domínio público): as mãos foram recortadas do reboco com o GrabCut e tonalizadas como uma impressão, em azul egípcio de dia e claras sobre o escuro à noite. A impressão por pontos vem das bordas para o vão entre os dedos; no celular a imagem atravessa a tela, e no PC fica em cima da entrada. Uma gravura de 1772 foi tentada antes, mas nela os dedos ficavam pouco nítidos.
- **A imagem em WebP:** o painel passa a servir `.webp`, e a imagem tem 62 KB, com a tinta no cinza e o recorte no alfa. A `gravura()` ganha as opções `canais`, `inverterNoEscuro`, `densidade` e `centro`, e o canvas passa a reduzir e ampliar a imagem com a suavização de alta qualidade.
- Testado: os 49 testes do painel (um novo: pela rede de casa o cookie sai sem `Secure`, e a senha errada conta nas duas entradas) e o CI reproduzido com `tools/ci-local.sh`; os cliques de ponta a ponta no celular e no PC; a entrada fotografada no celular e no PC, claro e escuro, sem erro na página, com os dedos conferidos na densidade do aparelho; o `systemd-socket-proxyd` repassando para um socket unix (no ensaio) e as duas unidades no `systemd-analyze verify`. No servidor de origem, o painel 0.9.0 subiu saudável com as duas entradas, e `http://<IP de casa>:3100` responde (a saúde, a página e a imagem) com as unidades e a regra do ufw postas por um script que faz o mesmo que esta parte do instalador; a primeira tentativa barrou o repassador em `/srv/core` (750), o que levou ao `TemporaryFileSystem` da unidade. Sem testar: a etapa 85 do instalador inteira com `ATENA_PAINEL_CASA` (`sim` e `nao`) e a entrada pela rede de casa num celular de verdade. Sem revisor separado nesta rodada.

## 0.16.2 (2026-10-22)

A entrada do painel com uma gravura clássica (painel 0.8.2).

- **A gravura:** a pedido do dono, com referências dele (gravuras clássicas numa cor só, azul sobre claro ou osso sobre preto, e um pontilhado), a entrada passa a ser a Atena Partenos, a estátua do Partenon, numa xilogravura de 1851 em domínio público (da *Iconographic Encyclopaedia*, pelo Wikimedia Commons). Ela está guardada só como máscara (`gravuras/atena-partenos.png`, com a origem e o preparo em `gravuras/ORIGEM.txt`), e a cor vem do CSS: azul egípcio de dia e cor de osso à noite.
- **A impressão:** a gravura se imprime na tela por um pontilhado ordenado (a matriz de Bayer 8×8, em pontos de 2 px) que se adensa de cima para baixo e da tinta mais escura para a mais clara, num canvas na densidade do aparelho; ao entrar, o mesmo pontilhado a desfaz. Na senha errada, ΑΘΗΝΑ fica em cinábrio por um instante; na certa, fica azul.
- **No PC:** a gravura à esquerda e a entrada à direita.
- Sai o templo desenhado da 0.16.1; o ícone da chave do meandro fica.
- Testado: os 48 testes do painel e os cliques de ponta a ponta no celular e no PC; a entrada fotografada em oito momentos (a impressão, pronta, senha errada, senha certa e o painel chegando) no celular e no PC, claro e escuro, sem erro na página. No servidor de origem, o painel 0.8.2 subiu saudável e serve a gravura. Sem revisor separado nesta rodada.

## 0.16.1 (2026-10-22)

A entrada nova do painel (painel 0.8.1): a construção do templo, no lugar da coruja.

- **A entrada:** a coruja pareceu desenho animado ao dono. No lugar dela, a fachada de um templo se constrói em três atos, como numa prancha de arquiteto. Primeiro a geometria, em linha fina: o chão, o eixo, um quadrado e o arco do compasso, que estende o quadrado até o retângulo de ouro (o corpo da fachada). Depois a obra a tinta: os três degraus, as seis colunas subindo do centro para fora, os capitéis, a arquitrave, o friso com os tríglifos e o frontão, cujas duas linhas se encontram no topo. Por fim, a geometria recua para um fantasma e ΑΘΗΝΑ chega letra a letra. Nada reage à digitação; na senha errada, a inscrição fica em cinábrio por um instante, e na certa o tímpano se pinta de azul egípcio, como eram os templos.
- **O ícone do app:** a chave do meandro, em mármore sobre o azul egípcio.
- O DESIGN.md, o design.json, o brief e a arquitetura descrevem a entrada nova, com o azul pigmento (o tímpano) como token.
- Testado: os 48 testes do painel e os cliques de ponta a ponta no celular; a entrada fotografada em oito momentos (os três atos, pronta, senha errada, senha certa e o painel chegando) no celular, claro e escuro, e no PC, sem erro na página. No servidor de origem, o painel 0.8.1 subiu saudável e serve o templo da entrada. Sem revisor separado nesta rodada.

## 0.16.0 (2026-10-22)

O painel com visual grego (painel 0.8.0): a policromia contida, a coruja de Atena na entrada e as zonas como os degraus do templo, em 3D.

- **O mundo:** os templos gregos eram pintados, e aqui a pintura é pouca e precisa: mármore e tinta de dia, uma noite azul-escura quase preta, o azul egípcio como único acento e os pigmentos antigos (malaquita, ocre e cinábrio) só como pontos de estado. O meandro é o ornamento e também a medida. Escolhido pelo dono, que no meio do trabalho pediu menos cor e nada de cara de desenho animado.
- **A letra:** Commissioner (Kostas Bartsokas, OFL), servida pelo painel, no lugar da Archivo e da Martian Mono. Os eixos FLAR e VOLM dão as serifas de pedra nos títulos e números; a caixa-alta fica só nas inscrições gregas (ΑΘΗΝΑ, ΑΘΕ).
- **A entrada:** a coruja das moedas de Atenas, em traço de gravura, se desenha ao abrir, fecha os olhos enquanto você digita a senha, inclina a cabeça na senha errada, e o meandro da borda só fecha com a certa.
- **As zonas:** a crepidoma, uma escada de mármore em CSS 3D, com um degrau por zona e um ponto por container. Os degraus sobem ao entrar, a escada respira devagar, e a zona com problema escorrega para o lado; a legenda ao lado é a parte que se lê e se toca.
- **Os números:** medalhões com o meandro da borda pintado até o valor (servidor, sensores e PC), barras em faixa de meandro e um relógio de sol na agenda, cuja sombra dá a volta quando um agendamento roda.
- **O movimento:** a troca de tela é uma View Transition (a velha se apaga, a nova chega do desfoque); o marcador da tela ativa desliza numa mola suave feita só com CSS (`linear()`), e o ícone dela se redesenha. Nada de quique, tremor ou cascata; com redução de movimento, nada se move.
- **Ícones:** redesenhados no mesmo traço (o Início é a frente do templo, os serviços uma ânfora, o sistema a engrenagem de Anticítera), e o ícone do app é a coruja.
- **Consertos:** a faixa de uma aprovação nova não aparecia no Início, em Serviços e no PC até trocar de tela (a contagem estava num else); o número e a unidade não se separam mais na quebra de linha; e o número da contagem de aprovações ficou legível sobre o ocre (5,0:1).
- Continua sem dependências: nada do npm, nenhum build, CSP só com o próprio painel. O `DESIGN.md` do painel descreve o mundo novo.
- Testado: os 48 testes do painel; no ensaio com o executor falso e os dados do servidor de origem, os cliques de ponta a ponta no celular e no PC sem erro no console, as fotos de todas as telas nos dois temas, a entrada em oito momentos, uma troca de tela quadro a quadro e as cenas provocadas (zona com problema, aprovação chegando, PC ligando, agendamento rodando); cada commit do painel abre sem erro em todas as telas. Um revisor separado, com as instruções da skill de design, pediu duas rodadas de correção; as da segunda foram conferidas nas fotos, sem um terceiro veredito. No servidor de origem, o painel 0.8.0 subiu saudável e serve a casca nova com gzip e 304. Ficou sem testar no celular de verdade (o ensaio emula o Chrome do Android).

## 0.15.1 (2026-10-22)

O `pc.estado` responde em meio segundo com o PC desligado.

- **Executor:** com o PC desligado, ninguém responde ao ARP, e a tentativa na porta do LM Studio esperava os 2 s inteiros: o painel, a Atena e o `local.processar` com o modelo "pc" esperavam isso a cada consulta. Na rede de casa, o PC ligado responde em menos de 1 ms (o ARP e a porta), então a espera agora é de meio segundo. O resto da conta, com a tabela de vizinhos, não muda.
- Testado: o `teste_pc.py` confere a espera e falha no código antigo; o CI inteiro pelo `ci-local.sh`. No servidor de origem, com o PC desligado, o `pc.estado` pelo socket do executor caiu de 1 a 2 s para 506 a 517 ms, e a conferência do executor passou. Ficou sem testar com o PC ligado.

## 0.15.0 (2026-10-22)

O painel mais rápido e mais fácil de ler (painel 0.7.0), a ronda que não repete o que já disse e as habilidades da Atena com o que só o servidor de origem sabia.

- **Telas na hora:** voltar a uma tela já vista mostra o que estava lá (de 100 a 2.150 ms para 4 a 16 ms), com o dado novo entrando por cima; a primeira visita mostra um esqueleto do módulo, e o ponto da tela ativa pisca enquanto ela busca. Ao abrir, o painel já prepara as telas da barra (PC, Agenda e Serviços), e a pergunta "quem sou eu" vai junto com a primeira tela. Duas telas que pedem a mesma consulta ao mesmo tempo esperam uma resposta só.
- **Serviços sem esperar o `docker stats`:** a tela sai com o estado dos containers (de 2.150 para 120 ms) e o uso de CPU e RAM entra quando chegar, mostrando o último visto enquanto isso.
- **A casca do cache se renova sozinha:** a versão do service worker é um resumo dos arquivos, e o servidor põe no `sw.js` a versão e a lista inteira da casca. O app abre do cache (318 para 215 ms) e, quando a versão muda, troca tudo e recarrega a página, sem perder o que você está digitando. Não é mais preciso trocar o número do cache a cada mudança.
- **gzip e ETag:** a interface sai comprimida, um arquivo que não mudou volta como 304, e as respostas da API acima de 1 KB também saem comprimidas.
- **Visual (o mesmo aparelho, com quatro consertos):**
  - **Linhas de lista:** todas as telas usam a mesma linha: o LED do estado, o nome, o estado escrito embaixo e as teclas à direita (ou embaixo do nome, quando são muitas). Em Serviços, os containers ficam presos à stack por uma guia tracejada.
  - **Tecla clara:** as ações de cada linha (Logs, Reiniciar, Editar…) são teclas claras, como as cinzas da calculadora ET66; a grafite fica para a ação do módulo e a amarela para a principal.
  - **Cortes e números:** num módulo estreito, o código do que ele mede desce para baixo do título, inteiro. Os números saem em pt-BR (15,0 GB, US$ 0,98, 54,7 MB, "1 chamada").
  - **Formulários:** o rótulo em cima de cada campo, numa grade; os dias da semana da Agenda viram teclas de trava, com LED. A Atividade mostra uma linha por evento, com 100 por padrão. Arquivos ganha pictogramas e o caminho clicável.
  - O `DESIGN.md` do painel registra a tecla clara, a linha de lista, o campo, a tecla de trava e o ponto que pisca.
- **A ronda fala só do que mudou:** a unidade com falha que um timer roda de novo (o `fwupd-refresh`, cujo CDN responde 504 de hora em hora) só sai da lista depois de 15 min sem falhar, e o fim de um trabalho do Claude Code aparece numa ronda só. O estado fica em `/opt/data/cron/ronda-estado.json`. Antes, a Atena mandava o resumo do mesmo trabalho a cada ida e volta da unidade.
- **Habilidades da Atena:** servidor-atena 1.6.1 e lab 1.2.1, com o que só o servidor de origem sabia (os projetos do lab no terminal, onde ficam documentos e anexos, o 504, dado privado só no `local.processar`), o que fazer sem aprovação no celular e no 409 do `app.publicar`, e o texto da ronda. A ronda carrega também a habilidade lab, e o instalador deixa o texto dela igual ao do modelo nas atualizações.
- Testado: os 48 testes do painel (três novos: a versão e a casca no `sw.js`, o gzip e o 304, a resposta grande da API comprimida) e o `teste_ronda.py`; o CI inteiro pelo `ci-local.sh`. No navegador, num ensaio com o executor falso e os dados do servidor de origem, com 90 ms de latência: as medidas acima, os cliques de cada tela no celular e no PC (criar, editar e apagar agendamento, navegar e abrir arquivos, reiniciar um serviço, recusar uma aprovação), a troca de versão do cache, e cada commit do visual abrindo sem erro. No servidor de origem, o painel 0.7.0 subiu saudável e serve a casca nova com gzip e 304, e a ronda nova está no ar desde 2026-10-21.

## 0.14.0 (2026-10-21)

As regras de trabalho escritas, e o fim da falha intermitente do CI.

- **`CONTRIBUTING.md`** (e `CONTRIBUTING.en.md`): o que estava só na cabeça de quem mantém o repositório, num lugar só. Só valores de exemplo, e onde pôr os seus dados para o verificador procurar; commits em fatias pequenas, com o porquê e o teste no corpo; o `tools/ci-local.sh` e o verificador antes de cada push; as regras do executor (módulos de baixo para cima, lista fechada, ação nova com teste e com a linha na habilidade da Atena), do painel (sem npm, uma tela por arquivo, a CSP, o cache do service worker), do instalador e das versões; e, num servidor de verdade, o repositório primeiro e depois instalar.
- **`CLAUDE.md`:** curto, para um assistente de código que abre o repositório: o que vale em qualquer tarefa e quando ler cada seção do `CONTRIBUTING.md`.
- Os READMEs apontam para as regras na seção Contribuindo.
- **Executor:** um pedido grande demais (acima de 1 MB) recebe o 413 em vez de "conexão encerrada": o executor lê e joga fora o corpo, até 8 MB, antes de recusar. Era a falha intermitente do CI (`BrokenPipeError` no `teste_nucleo`), que as anotações novas mostraram; o teste usa agora o limite real, e no executor antigo ele falha sempre.
- Com esta versão fecha a passada de qualidade: o servidor de origem roda o mesmo código do repositório (0.11.0), o executor está em módulos (0.12.0), a interface do painel também (0.13.0), e o CI ganhou o ruff, os tipos do painel e as anotações de falha.
- Testado: os comandos e caminhos citados nos documentos foram conferidos no repositório; o teste novo do limite falha no executor antigo e passa no novo (aqui e no CI local, num Ubuntu 24.04 limpo); e, no servidor de origem, o executor com o conserto passou na conferência.

## 0.13.0 (2026-10-21)

A interface do painel em módulos (painel 0.6.1) e a checagem de tipos do servidor dele.

- **Uma tela por arquivo:** o `app.js` de 1500 linhas virou a casca (navegação, paleta e atualização), o `comum.js` (o que todas as telas usam), o `zonas.js` e uma tela por arquivo em `public/telas`. Continua JavaScript puro, sem build e sem pacote do npm.
- **Nada mudou na tela:** a divisão foi feita por um programa; as 126 declarações são idênticas às de antes (comparadas pela árvore do JavaScript), sem nome sem import nem import sem uso. As três funções da casca que as telas chamam (atualizar, telaAtual, mostrarEntrada) o `comum.js` expõe e o `app.js` liga ao começar, para nenhuma tela importar a casca. Antes de dividir, duas variáveis que uma tela reatribuía em outra (a zona em foco e a hora em que o PC ligou) passaram a mudar por funções.
- **Tipos:** o CI confere o servidor e os testes do painel com `tsc --noEmit` (strict, só a sintaxe que o Node apaga). O TypeScript e os tipos do Node entram só no container do CI e do `tools/ci-local.sh`.
- O service worker guarda os arquivos novos (cache v3): no celular, feche e abra o app uma vez depois de atualizar.
- Testado no navegador, no ensaio com o executor falso: das 27 capturas de antes (celular e PC, claro e escuro), 21 saíram iguais pixel a pixel e as outras só diferem no relógio da agenda e no "há N min" das aprovações; a zona em foco, ligar o PC (na tela e na paleta), a sessão caída e sair funcionam, sem erro na página. No servidor de origem, o painel 0.6.1 subiu saudável e serve a casca, as telas e o cache novo.

## 0.12.0 (2026-10-21)

O executor em módulos.

- **O pacote `atena_executor`:** o executor de 3000 linhas num arquivo só virou 17 módulos, um por assunto (base, segredos, inventario, celular, tokens, pedidos, sistema, arquivos, pc, local, arca, stacks, lab, claude, central, acoes e servidor). Um módulo só importa dos que vêm antes dele; nos 4 lugares em que um de baixo precisa de um de cima, o import fica dentro da função, com o motivo ao lado. O mapa está no `__init__.py`.
- **Nada mudou no que ele faz:** a divisão foi feita por um programa, não à mão, e as 236 definições são idênticas às do arquivo antigo (comparadas pela árvore do Python). O `/usr/local/sbin/atena-executor` agora só chama o pacote, que o instalador põe em `/usr/local/lib/atena-executor` (trocando a pasta inteira, sem sobrar módulo velho).
- **Testes:** veem o pacote como um módulo só (`tests/pacote_executor.py`), então nenhuma conferência mudou; cada carga é um pacote com nome próprio, para dois executores no mesmo teste não dividirem estado.
- **ruff no CI:** erros de verdade no Python (nome indefinido, import e variável sem uso, sintaxe, as armadilhas do bugbear), não estilo. Também roda no `tools/ci-local.sh`.
- Testado: a bateria inteira e o CI pelo `ci-local.sh`; o pacote instalado do jeito do instalador num Ubuntu 26.04 limpo, em container (carrega as 45 ações, e uma reinstalação não deixa módulo velho); e, no servidor de origem, as consultas do painel e da Atena com o executor em módulos.

## 0.11.0 (2026-10-21)

Skills no Claude Code do lab, e o servidor de origem roda o executor deste repositório.

- **Skills (opcional, `ATENA_CLAUDE_SKILLS=sim`):** cada conta do lab ganha os plugins frontend-design, mattpocock-skills, pyright-lsp e typescript-lsp e a skill Impeccable. O Impeccable vai só com o texto: o instalador baixa um commit fixo do GitHub e confere o sha256 dos arquivos, sem o lançador (que baixa um binário) e sem os hooks. A Atena escolhe a skill de cada trabalho pelo catálogo do lab (`host/lab/skills.json`) e por uma tabela "o dono pede → skill"; em projeto grande, segue o fluxo to-spec → implement-spec. O runner chama a skill na primeira linha do pedido.
- **`atena-tela`:** o Claude Code confere as telas que faz com prints de uma página local, num Chromium sem tela que roda dentro do sandbox, e vê os erros do console. As ferramentas ficam nas versões do `package-lock.json` (npm ci, sem scripts).
- **`sudo atena-claude-conta skills`:** põe os plugins e o Impeccable nas contas com login (o `entrar` já faz isso) ou, com a chave em `nao`, tira tudo.
- **O servidor de origem igual ao modelo:** o servidor onde a Atena nasceu passou a rodar o executor, o runner e o `atena-claude-conta` deste repositório, sem diferença. O que só existia lá virou chave do `atena.conf`.
- **CI:** a bateria de testes roda inteira mesmo depois de uma falha, e cada falha vira uma anotação do GitHub, que dá para ler sem abrir o log. O `actions/checkout` foi para a v5 (Node 24). O `tools/ci-local.sh` roda os mesmos jobs do CI em containers, antes do push.
- Testado: os testes novos do executor e do runner (skill ligada, desligada e fora do catálogo; PATH, regras e primeira linha do pedido); o trecho novo do instalador num Ubuntu 26.04 limpo, em container (ferramentas, Chromium, um print de verdade, o Impeccable baixado e conferido, e a segunda rodada sem baixar de novo); o CI inteiro pelo `ci-local.sh`; e, no servidor de origem, as consultas do painel e da Atena com o executor novo. O `atena-claude-conta skills` (os plugins nas contas) não foi rodado de novo: as contas do servidor já tinham os plugins.

## 0.10.0 (2026-10-21)

O visual do painel: um aparelho de mesa (painel 0.6.0).

- **A direção:** escolhida pelo dono entre três (um mapa de metrô, um grid suíço e um aparelho), com as skills de design: um aparelho na linha da Teenage Engineering (OP-1), de Dieter Rams/Braun e da calculadora Braun ET66. As regras ficam em `stacks/core/painel/DESIGN.md`, e o que o painel é e para quem em `stacks/core/painel/PRODUCT.md`.
- **O aparelho:** chassi de alumínio ou grafite, que segue o tema do aparelho; módulos com parafusos, régua, código de peça (IN-01) e a placa ATENA AT-1; teclas grafite que afundam ao apertar, com o amarelo sinal só na ação principal; LEDs como vocabulário de estado, sempre com o texto ao lado.
- **O visor:** um vidro preto com desenhos que vêm dos dados de verdade (carretéis que giram na velocidade da CPU, termômetro, tanque da RAM, chip da GPU, a torre do PC com a ventoinha, o mostrador de 24 h da agenda) e números em 7 segmentos, com os apagados por trás. A **vista explodida** desenha as zonas como placas encaixadas, com um LED por container; a da zona com problema sai do lugar.
- **Navegação:** barra embaixo no celular (Início, PC, Agenda, Serviços, Mais), trilho agrupado no PC e a paleta de comandos (Ctrl+K). Uma faixa amarela avisa quando há aprovação esperando e pulsa quando chega uma nova.
- **Cena só nos momentos:** os LEDs varrem ao entrar, a ventoinha acelera quando o PC liga e o mostrador gira quando um agendamento roda; com redução de movimento, nada se move.
- **Textos:** os estados do Docker e dos pedidos em português ("há 3 dias · verificação de saúde falhando", "parado há 5 h", "concluído").
- **Fontes e ícone:** Archivo e Martian Mono (licença OFL) servidas pelo próprio painel, porque a CSP não deixa buscar fora; ícone novo, uma tecla amarela no grafite.
- No PC, os módulos descem em colunas, sem vãos.
- Testado no servidor de origem (o painel 0.6.0 subiu saudável e serve a casca nova e as fontes) e no navegador, no tamanho de celular e de PC, nos temas claro e escuro. Um revisor separado, com as instruções da skill e sem o histórico de quem construiu, pediu duas rodadas de correção (códigos de peça, vãos no PC, o visor como foco, as teclas, os textos, os controles do navegador); as da segunda rodada foram aplicadas e conferidas nas capturas, sem um terceiro veredito.

## 0.9.0 (2026-10-21)

A agenda, os arquivos e o editor de stacks no painel (painel 0.5.0), e uma correção de segurança no executor.

- **Agenda:** o agendador fica no próprio painel. Uma vez, toda semana (com atalhos para dias úteis e todo dia) ou todo mês, só com as ações da lista de agendáveis: ligar, desligar e reiniciar o PC, reiniciar um serviço, reiniciar, parar e publicar um app do lab. Com o painel fora do ar na hora marcada, ao voltar ele roda o que atrasou até a tolerância (15 min por padrão); passou disso, a vez fica perdida e não roda depois. Aviso no celular sempre, só se falhar ou nunca. A lista mostra a próxima vez, a última e as últimas execuções, com Rodar agora, Pausar, Editar e Apagar, e o Início mostra os três próximos.
- **Editor das stacks de apps:** nos Serviços, as stacks da zona apps ganham Editar, com os arquivos da pasta, Gravar (com foto do anterior), Aplicar e Desfazer. O arquivo chega com os segredos ocultos; a gravação manda só o trecho que mudou, e um trecho com segredo oculto fica para o terminal, para nunca gravar `***` no lugar de uma senha.
- **Arquivos:** navegar pelo servidor, ver e baixar arquivos de texto, e procurar pelo nome, tipo e data ou pelo texto de dentro, sempre menos os segredos.
- **Pendências:** no Início, as suas e, quando o servidor tem `/opt/atena/README.md`, as da seção "Pendências conhecidas", que ficam resolvidas quando saem de lá.
- **Claude Code:** continuar um trabalho terminado, inclusive os da Atena, com a conversa; e escolher a skill, quando o executor tem skills.
- **Executor:** `aviso.celular`, para os agendamentos avisarem (o painel não tem rede); quem decide pelo dono continua os trabalhos dos clientes no alcance dele. A habilidade da Atena (servidor-atena 1.5.0) registra as duas coisas.
- **Correção de segurança:** `arquivo.ler` e `arquivo.buscar` não conferiam a zona prod, então quem não tem a zona (a Atena e o painel) lia e buscava texto nos arquivos de clientes em `/srv/prod`. Agora os dois respondem 403, como `arquivo.procurar` e `arquivo.entregar` já faziam.
- Com uma janela aberta, os avisos aparecem dentro dela (ficavam escondidos atrás). A tela que se atualiza sozinha não apaga um campo em que você está escrevendo. O banco da 0.4 ganha as tabelas novas sem perder nada.
- O instalador refaz o token do painel com as 38 ações.
- Testado no CI e no servidor de origem: o executor novo entrou conferindo o hash, o token da Atena ficou igual, o painel 0.5.0 subiu saudável com o banco antigo migrado, e pelo token novo responderam as skills, o README, as fotos das stacks e o aviso (sem mandar nada ao celular); a zona prod passou a responder 403 para o painel. O agendador tem testes com relógio falso (na hora, atrasado dentro e fora da tolerância, uma vez, pausado, falha e aviso). O ensaio da interface no navegador, no tamanho de celular e de PC, passou por agendar, editar, pausar e rodar agora, navegar, baixar e procurar arquivos, editar uma stack (inclusive o trecho com segredo recusado), desfazer, aplicar e continuar um trabalho com skill. Sem VM nesta versão: o instalador só ganhou nomes no token.

## 0.8.0 (2026-10-21)

O lab e o Claude Code pelo painel (painel 0.4.0).

- **Apps do lab:** publicar (ou publicar de novo), reiniciar, parar, cancelar o que estiver em andamento, restaurar da lixeira e rodar um comando dentro do app, com a saída na tela. Apagar abre uma janela para escolher o que sai: o container e a imagem (publicar de novo reconstrói), o código (vai para a lixeira por 30 dias) ou os dados, que não têm volta e só saem digitando o nome do app.
- **Claude Code:** um trabalho novo com conta, modelo, esforço, tempo, só planejar e publicar quando terminar bem. O rascunho fica guardado se a tela atualizar. A lista mostra os trabalhos de todos os clientes, inclusive os da Atena, com o resumo, os commits, o aviso quando um espera a sua permissão e o botão Cancelar.
- **Executor:** quem decide pelo dono (o token com `aprovacoes.decidir`, ou seja, o painel) vê e cancela os trabalhos do Claude Code dos clientes no alcance dele, e decide as permissões e as perguntas dos trabalhos que ele mesmo mandou, porque quem pede é o Claude Code. Para a Atena nada muda.
- **Histórico:** o que ficou em andamento quando a tela fechou é conferido ao abrir o histórico, e uma ação demorada não diz mais "feito" antes de terminar.
- O instalador refaz o token do painel com as 30 ações. A habilidade da Atena (servidor-atena 1.4.0) sabe que o dono vê e cancela os trabalhos dela pelo painel.
- Testado no CI e no servidor de origem: o executor novo entrou no lugar do anterior conferindo o hash, o token da Atena ficou igual, o painel 0.4.0 subiu saudável e, pelo token novo, viu os trabalhos da Atena. O ensaio da interface no navegador, no tamanho de celular e de PC, com um executor falso, passou por mandar trabalho, apagar com os dados, rodar comando, cancelar, restaurar e publicar de novo; achou um defeito (a saída do comando não aparecia), corrigido antes do commit. Sem VM nesta versão: o instalador só ganhou nomes no token.

## 0.7.0 (2026-10-21)

A aba Sistema do painel (painel 0.3.0).

- **Sensores:** temperatura da CPU (e dos núcleos, quando o chip mostra), do NVMe e da GPU; uso, watts e ventoinha da GPU; as ventoinhas e os sensores da placa. Cada barra enche até o ponto de alerta.
- **Processos:** os 25 que mais usam CPU ou RAM, com usuário, memória e há quanto tempo rodam. Tocar no comando mostra ele inteiro.
- **Rede:** os endereços de cada interface (as veth dos containers ficam de fora) e as portas abertas, cada uma com o alcance: só o servidor, containers, rede de casa, Tailscale ou todas as redes.
- **Registro do systemd:** por unidade, gravidade e período (de 30 min a 7 dias), com os segredos ocultos.
- No celular, as abas quebram em linhas em vez de sumir pela direita.
- O instalador refaz o token do painel com as 22 ações. O executor não muda: as três ações que o painel ganhou (`sistema.processos`, `sistema.rede` e `servico.journal`) já existiam para a Atena.
- Testado no CI e no servidor de origem: o token foi refeito, o painel 0.3.0 subiu saudável e as três ações responderam pelo token novo. O ensaio da interface no navegador, no tamanho de celular e de PC, com um executor falso, achou um defeito (o registro vazio não dizia nada), corrigido antes do commit. Sem VM nesta versão: o instalador só ganhou três nomes no token, num caminho que a VM da 0.6.0 já testou.

## 0.6.0 (2026-10-20)

A central de aprovações e a atividade do executor no painel (painel 0.2.0).

- **Aprovações no painel:** o que a Atena e o Claude Code pedem e espera por você (pedidos de aprovação, permissões e perguntas do Claude Code) aparece com o mesmo texto que foi ao celular, quem pediu e quando vence. Aprovar, Recusar ou responder a pergunta (por opção ou texto livre) vale o mesmo que o toque no celular, que continua funcionando. Quem decidir primeiro decide. A aba mostra quantos esperam, e a lista dos decididos há pouco mostra quem decidiu.
- **Atividade:** o registro do executor no painel, do mais novo ao mais velho (cada pedido de cada cliente, as decisões e os erros), com filtro por cliente e só os erros. Parâmetros longos saem cortados e sem segredos.
- **Executor:** ações `aprovacoes.lista`, `aprovacoes.decidir` e `atividade.lista`. O pedido guarda o texto que foi ao celular. Nenhum cliente decide os próprios pedidos, e cada um só enxerga pedidos de clientes dentro das zonas dele. Só o token do painel recebe essas ações; o da Atena não muda.
- O instalador refaz o token do painel com as 19 ações e guarda o compose anterior.
- A habilidade da Atena (servidor-atena 1.3.0) sabe que o dono também decide pelo painel, e que essas ações são só dele.
- Testado numa VM Ubuntu 26.04 sem GPU, atualizando uma 0.5.0 com o painel: o token foi refeito com as 19 ações, o painel 0.2.0 subiu saudável e, com o executor e o ntfy de verdade, um cliente de teste pediu para reiniciar o Dockge, o painel viu o pedido com o texto do celular, aprovou (o Dockge reiniciou), recusou o seguinte e mostrou as duas decisões na atividade. Rodar o instalador de novo manteve o token.

## 0.5.0 (2026-10-20)

O painel: o servidor no navegador e no celular. Extraído do primeiro servidor Atena.

- **Painel** (opcional, `./install.sh --painel`): app instalável (PWA) com as telas Início (CPU, RAM, discos, GPU, temperaturas, serviços com problema, gasto de IA do mês e falhas do systemd), Serviços (stacks por zona, logs e reiniciar), PC (ligar, desligar, reiniciar e cancelar), Lab (apps publicados, reiniciar e parar), Histórico e Ajustes (aparelhos conectados).
- **Só pelo Tailscale e sem rede:** o `tailscale serve` entrega as visitas num socket (porta 3100), e o container roda com `network_mode: none`, sem root, com o disco só de leitura, sem capacidades e sem o socket do Docker. Na rede de casa, a porta nem existe.
- **Senha** com `atena-painel-senha` (scrypt, só num terminal). A sessão dura 30 dias e renova no uso; 5 erros em 15 minutos bloqueiam a entrada; trocar a senha desconecta todos os aparelhos.
- **Token próprio no executor:** 16 ações, nenhuma que apague ou edite, sem aprovação no celular, porque quem confirma é você, na tela. O instalador só refaz o token se ele não bater.
- **Sem pacotes do npm:** o Node 22 roda o TypeScript direto e traz o SQLite. Os 27 testes do painel rodam no CI.
- Correção que veio junto: o verificador de vazamentos encerrava sem mensagem, e bloqueava todo commit, quando um `.env` do servidor só tinha valores curtos.
- Ainda não: conversar com a Atena pelo painel, agendamentos e o visual definitivo.
- Testado numa VM Ubuntu 26.04 sem GPU, atualizando uma 0.4.0: o instalador criou o usuário, o token e a stack, deixou o painel saudável e avisou que faltavam o Tailscale e a senha. A senha foi gravada por um terminal de verdade. Pelo socket, como o Tailscale faz, 15 conferências passaram contra o executor de verdade: entrar, recusar a senha errada e o pedido sem o cabeçalho, consultas, reiniciar o Dockge com histórico, e os erros explicados sem LiteLLM, sem PC e sem lab. Rodar o instalador de novo manteve o token, a senha e o histórico. O ensaio da interface no navegador, no tamanho de celular e de PC, achou três defeitos de tela, corrigidos antes dos commits.

## 0.4.0 (2026-10-20)

O lab: a Atena manda trabalhos de programação ao Claude Code. Extraído do primeiro servidor Atena.

- **Claude Code pela Atena** (opcional, `./install.sh --lab`): `claude.tarefa` põe o trabalho na fila, e o runner roda o Claude Code como `atena-claude` (sem sudo, sem Docker) em `/srv/lab/projetos/<projeto>`, num sandbox estrito, até 3 ao mesmo tempo. O Claude Code tem versão fixa (`ATENA_CLAUDE_VERSAO`), baixada do repositório oficial e conferida pelo checksum.
- **Permissões e perguntas no celular:** o que o Claude Code pede vem com Aprovar e Recusar; uma dúvida dele chega ao celular e à Atena, que decide se você não responder em 10 min.
- **Contas:** as de `ATENA_CLAUDE_CONTAS`, com login pelo `atena-claude-conta`. No limite de uso, o trabalho para e a Atena avisa; a troca automática para outra conta é opcional (`ATENA_CLAUDE_TROCA=sim`). Continuar em outra conta, a seu pedido, leva a conversa junto.
- **Apps do lab:** `app.publicar` constrói pelo Dockerfile e põe no ar na zona lab (porta 8000-8999 na rede de casa e, com Tailscale, fora de casa). `app.reiniciar`, `app.parar`, `app.cancelar`, `app.apagar` (o código vai para uma lixeira por 30 dias), `app.restaurar`, `app.comando` e `app.lista`. Publicar e apagar pedem o celular.
- **A Atena no lab:** os projetos ficam no terminal dela, para ajustes pequenos com commit; a habilidade `lab` diz quando fazer ela mesma e quando mandar ao Claude Code; a ronda avisa quando um trabalho termina e quando o Claude Code pergunta algo.
- **Lab interativo:** o seu Claude Code em `/srv/lab` ganha o mesmo sandbox e um guarda de escopo.
- **Travas para quem escreve nos projetos:** o Claude Code só lê a configuração da conta e o `lab.json`, sem hooks do projeto, e o git do runner ignora fsmonitor e hooks; um `.git/config` que rode comandos faz o trabalho ser recusado.
- Correção que veio junto: depois de trocar de conta, o aviso de limite da rodada anterior não vale mais para a nova.
- Ainda não: as skills do Claude Code e os prints de tela (próxima versão).
- Testado numa VM Ubuntu 26.04 sem GPU, instalando o lab sobre uma 0.3.1 com a Atena: o Claude Code (de mentira, com a ponte e a fila de verdade) fez um app e perguntou pela ponte; a Atena respondeu; o app foi publicado com o Aprovar pelo ntfy, respondeu na rede de casa, foi parado, apagado (código para a lixeira) e restaurado; a Atena fez commit no projeto pelo terminal dela; e o instalador rodou de novo sem refazer o token nem mexer nas permissões. O teste achou dois defeitos, já corrigidos: o arquivo de configuração do git da Atena tinha ficado fora do repositório, e o needrestart reiniciava serviços durante a instalação.

## 0.3.1 (2026-10-20)

- **Correção nas stacks de apps:** com o Docker Compose 2.x, o executor não enxergava o `env_file` e o `label_file` de um compose, e deixava uma stack de apps ler o `.env` de outra. Agora ele lê o compose uma segunda vez com `--no-interpolate`, que mostra esses caminhos em qualquer versão (testado no 2.24, 2.38, 2.40 e 5.6). Com o Compose v5, que o instalador traz, a regra já funcionava.

## 0.3.0 (2026-10-20)

Voz, temperaturas, o Arca e as stacks de apps nas mãos da Atena, extraídos do primeiro servidor Atena.

- **Temperaturas e ventoinhas**: `sistema.sensores` (CPU AMD ou Intel, NVMe, GPU e o chip da placa) e as temperaturas no `status.recursos`. A ronda avisa CPU acima de 85 °C e NVMe acima de 70 °C. O chip da placa, que lê as ventoinhas, vem de um módulo opcional (`ATENA_SENSORES_MODULO`).
- **Arca pela Atena**: `arca.lista`, `arca.pegar` e `arca.guardar`, pelo nome original e no formato do próprio Arca (texto com segredos ocultos).
- **Stacks de apps pela Atena**: `stack.editar` (com foto antes de cada mudança), `stack.desfazer`, `stack.fotos` e `stack.aplicar`, que sobe a stack em segundo plano. O compose inteiro precisa caber nas regras da zona `apps`.
- **Voz** (opcional, com GPU: `ATENA_VOZ=sim`): stack `ai/voz` com o Kokoro, modelo `voz` no LiteLLM (custo zero) e respostas em voz no Telegram com `/voice`.
- O Ollama sai da GPU depois de 2 minutos sem uso, para caber com o Whisper e a voz numa placa de 6 GB.
- O executor reconhece chave privada pelo cabeçalho do bloco PEM (antes recusava até o próprio código) e aceita pedidos de até 1 MB.
- Numa atualização, o token da Atena ganha as ações novas, com as mesmas zonas e a mesma regra de aprovação. Os passos que são seus (LiteLLM, chave da Atena e Ollama) estão em [operação](docs/pt/operacao.md#atualizar-da-02-para-a-03).
- O token da Atena agora é gravado num arquivo novo e movido para o lugar, e o instalador refaz o token quando o do arquivo não vale mais: no Ubuntu 26.04, o `install` não copia de `/dev/stdin` por cima de um arquivo que já existe.
- Testado numa VM Ubuntu 26.04 sem GPU, atualizando uma 0.2 em uso: a Atena listou, pegou e guardou arquivos no Arca, editou e aplicou a stack do Arca (com o `docker compose up --build` dentro do sandbox do executor), desfez a edição, teve compose com `privileged` e `.env` recusados, e o instalador rodou mais três vezes sem refazer o token nem duplicar nada.

## 0.2.0 (2026-10-19)

O executor de ações e a Atena (Hermes), extraídos do primeiro servidor Atena.

- **Executor de ações** (`atena-executor`): o único caminho dos agentes até o servidor. Lista fechada de ações, sem shell, token por cliente com ações e zonas, leitura do servidor inteiro sem segredos (só `CAP_DAC_READ_SEARCH`), aprovação no celular pelo ntfy, PC opcional da rede de casa (Wake-on-LAN e desligar por SSH restrito) e texto privado num modelo de casa (`local.processar`).
- **ntfy** na zona `core`, com login obrigatório, e a rede interna `svc-ntfy`.
- **Avisos no celular**: unidade `atena-*` que falha e container parado ou doente (`atena-avisar`, `atena-vigia.timer`).
- **A Atena** (opcional, `--hermes`): Hermes Agent na zona `agents`, sem Docker nem sudo, com personalidade, habilidades `servidor-atena` e `notas`, ronda de 3 em 3 minutos que só gasta API quando algo muda, voz pelo Whisper e configuração aplicada pelo `hermes config set`.
- Comandos novos: `atena-ntfy-celular`, `atena-hermes-chave` e `atena-telegram` (os segredos não aparecem na tela).
- LiteLLM com o modelo `whisper`, para quem só alcança o LiteLLM.
- `atena.conf`: `ATENA_TZ`, `ATENA_NTFY_URL`, modelo local e o PC opcional (`ATENA_PC_*`). Um `atena.conf` antigo continua valendo.
- Testes do executor e da ronda, rodando a cada envio ao GitHub. O verificador de vazamentos reconhece tokens do Telegram, do ntfy e do executor.
- Instalador testado de ponta a ponta numa VM Ubuntu 26.04 sem GPU, com `--hermes`: executor pela Atena, segredos recusados, aprovação pelo ntfy de verdade, avisos de falha, chave do LiteLLM e três execuções seguidas sem duplicar nada.

## 0.1.0 (2026-10-17)

Primeira versão do modelo, extraída do primeiro servidor Atena.

- Seis zonas (`prod`, `core`, `apps`, `ai`, `agents`, `lab`) com redes de faixa fixa e limites de CPU/RAM por slice do systemd.
- Firewall dos containers: saída só para a internet, entrada só da rede de casa.
- Instalador em etapas, que pode rodar de novo sem estragar o que já existe.
- GPU NVIDIA opcional (driver headless assinado, sem DKMS) e Tailscale opcional.
- Stacks: Dockge, Beszel, Ollama, Whisper, LiteLLM (com tetos de gasto por modelo e por chave), Open WebUI e Arca.
- Verificador de vazamentos, trava de commit e verificação no GitHub (shellcheck, composes e gitleaks).
- Documentação em português e inglês.
