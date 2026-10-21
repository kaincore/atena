# Mudanças

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
