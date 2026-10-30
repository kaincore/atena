# Operação

## Adicionar uma stack

1. Crie a pasta na zona certa: `/opt/atena/stacks/<zona>/<nome>/`. O nome precisa ser único entre todas as zonas.
2. Escreva o `compose.yaml` seguindo as [regras](arquitetura.md#regras-para-toda-stack).
3. A stack aparece sozinha no Dockge. Suba por lá ou com `docker compose up -d`.
4. Para acessar de fora de casa:
   ```bash
   sudo tailscale serve --bg --https=<porta> http://127.0.0.1:<porta>
   sudo ufw allow in on tailscale0 to any port <porta> proto tcp comment '<nome> via Tailscale Serve'
   ```
   O tailscaled escuta essa porta pelo kernel, então sem a regra do ufw os outros aparelhos ficam bloqueados. **Teste de outro aparelho**: um teste feito de dentro do servidor passa mesmo sem a regra.

## Adicionar um cliente na zona prod

Cada cliente tem rede própria, para um não enxergar o outro:

```bash
sudo docker network create --subnet 10.10.101.0/24 \
  -o com.docker.network.bridge.name=br-prod-<nome> \
  -o com.docker.network.bridge.host_binding_ipv4=127.0.0.1 \
  --label atena.zone=prod zone-prod-<nome>
sudo install -d -m 700 -o <admin> -g <admin> /opt/atena/stacks/prod/<nome> /srv/prod/<nome>
```

Use a próxima faixa livre (10.10.102.0/24, 10.10.103.0/24...). O nome da interface tem no máximo 15 caracteres.

**Antes de colocar um cliente no ar:** nobreak instalado e backup testado, com uma restauração concluída.

## Liberar uma exceção no firewall dos containers

Edite a seção "exceções" de `host/sbin/atena-docker-firewall` no repositório (por exemplo, para um container monitorar uma impressora da rede de casa), copie para `/usr/local/sbin/` e aplique. Editado só no servidor, ele aparece como diferente no `./aplicar --conferir`. O PC da rede de casa não precisa disso: ele entra pelo `atena.conf`.

```bash
sudo systemctl restart atena-docker-firewall
```

## LiteLLM

- **Chave da Anthropic:** `atena-chave-anthropic`. A chave não aparece na tela, é conferida na Anthropic sem custo e só então é gravada.
- **Chaves para cada consumidor:** crie uma chave virtual por consumidor (Open WebUI, agentes...), cada uma com o próprio teto:
  ```bash
  curl -s http://127.0.0.1:4000/key/generate \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' \
    -d '{"key_alias":"open-webui","models":["local","haiku"],"max_budget":10,"budget_duration":"1mo"}'
  ```
- **Tetos por modelo:** `max_budget` em `config.yaml`. O `id` de cada modelo não pode ser igual ao `model_name` (veja as [lições](licoes.md)).
- **Virada do mês:** os tetos das chaves (`1mo`) renovam sozinhos no dia 1º às 00:00 UTC. Os tetos por modelo são zerados no mesmo horário pelo `atena-litellm-virada-mes.timer`. Se o servidor estava desligado, a virada roda no boot, espera o Redis e o LiteLLM e tenta de novo de 5 em 5 min (até 5 vezes); a falha final avisa no celular.
- **Depois de editar o `config.yaml`:** `docker compose up -d --force-recreate litellm`.

## Avisos no celular (ntfy)

1. Instale o app **ntfy** no celular (Android).
2. Crie o seu usuário, só de leitura: `sudo atena-ntfy-celular <seu-nome>`.
3. No app, adicione o servidor de `ATENA_NTFY_URL` com esse usuário e assine os tópicos `alertas`, `aprovacoes` e `atena`, em minúsculas e sem acento.
4. Teste: `sudo atena-avisar "Teste" "Chegou?"`.

Para receber fora de casa, publique o ntfy pelo Tailscale (como em [Adicionar uma stack](#adicionar-uma-stack), porta 2586) e troque o endereço:

1. Em `/etc/atena/atena.conf`, `ATENA_NTFY_URL=https://<servidor>.<sua-tailnet>.ts.net:2586`. O executor lê o arquivo a cada pedido.
2. Em `/opt/atena/stacks/core/ntfy/server.yml`, o mesmo endereço em `base-url`, e `docker compose up -d --force-recreate` na pasta do ntfy.
3. No app, troque o servidor pelo endereço novo.

## Containers depois de um boot

Depois de um desligamento sujo, o Docker pode religar um container sem uma das redes, sem erro nenhum. O `atena-reconciliar` confere as redes e as portas de cada container contra o compose da stack: 3 min depois do boot, recria uma vez o que voltou errado e avisa; depois, de 5 em 5 min, só avisa, uma vez por problema. Ele nunca liga o que você parou e nunca cria o que sumiu.

- Ver as diferenças sem mexer: `sudo atena-reconciliar --so-ver`.
- O que ele avisa e o que o vigia avisa (container parado com erro ou doente) chegam no tópico `alertas`.
- O Docker só sobe com o `/srv` montado: se o disco de dados não montar, os serviços ficam parados em vez de subir vazios no disco do sistema.

## Executor: clientes e tokens

```bash
sudo atena-executor tokens                                    # quem pode pedir o quê
sudo atena-executor token-novo <cliente> <ações> <zonas> [aprovar]
sudo atena-executor token-remover <cliente>
sudo atena-executor token-acertar                            # o painel e a Atena ganham as ações novas do catálogo
journalctl -u atena-executor -f                               # cada pedido, com o resultado
```

- Listas separadas por vírgula. `aprovar` diz quais ações pedem o celular, além das destrutivas, que sempre pedem. `nenhuma` é só para o painel: lá, quem confirma na tela é você, e nem a destrutiva pede o celular. Sem esse campo, toda ação que pode pedir aprovação pede.
- O instalador monta os tokens do painel e da Atena pelo catálogo do executor (`atena-executor acoes painel`, `atena` ou `atena-lab`). Cada ação diz lá o risco dela, e o `GET /acoes` mostra o catálogo a quem tem o token. Uma ação nova chega ao token no `./aplicar` seguinte (`token-acertar`), sem trocar o token nem as aprovações.
- O token aparece uma única vez. Criar de novo para o mesmo cliente revoga o anterior.
- Exemplo: a Atena passa a pedir o celular antes de reiniciar algo (o token dela fica em `/srv/agents/hermes/executor.token`):
  ```bash
  sudo atena-executor tokens | grep hermes      # copie a lista de ações e de zonas dela
  sudo atena-executor token-novo hermes <ações> <zonas> servico.reiniciar \
    | sudo tee /srv/agents/hermes/executor.token >/dev/null   # o arquivo continua do hermes, com 600
  ```

## Atena (Hermes)

**Instalar.** `sudo ./install.sh --hermes`. Depois:

1. Suba o LiteLLM (stack `ai/litellm`) e grave a chave da Anthropic com `atena-chave-anthropic`. Para ouvir mensagens de voz, suba também o Whisper (`ai/whisper`).
2. `sudo atena-hermes-chave [teto]`: cria a chave da Atena no LiteLLM, com teto em dólares por mês (padrão 10), e grava no Hermes sem mostrar.
3. Crie um bot com o **@BotFather** no Telegram e rode `sudo atena-telegram`. O script pede o token sem mostrar, espera você mandar "oi" ao bot e confirma o seu ID. Só você conversa com ela.
4. Para o texto privado (`local.processar`), baixe o modelo do servidor: `docker exec ollama ollama pull qwen3:4b-instruct-2507-q4_K_M` (ou o de `ATENA_LOCAL_MODELO`).
5. Voz (opcional, com GPU): `ATENA_VOZ=sim` no `atena.conf` e rode o instalador de novo. Suba a stack `ai/voz`, baixe o modelo uma vez com `curl -X POST http://127.0.0.1:8003/v1/models/speaches-ai/Kokoro-82M-v1.0-ONNX` e mande `/voice` no Telegram (`on`: responde em voz quando você manda voz; `tts`: sempre; `off`: desliga). A voz padrão é `pf_dora`; outras em português: `pm_alex` e `pm_santa` (`docker exec -u hermes hermes hermes config set tts.openai.voice pm_alex`).

**No dia a dia.**

- `/new` no Telegram começa uma conversa nova (use depois de mudar a personalidade ou as habilidades).
- Terminal: `docker exec -it -u hermes hermes hermes`.
- Personalidade e habilidades: `/srv/agents/hermes/SOUL.md` e `/srv/agents/hermes/skills/atena/`. O instalador guarda uma cópia antes de sobrescrever um arquivo que você mudou.
- Configuração: `docker exec -u hermes hermes hermes config set <chave> <valor>`. Para voltar ao padrão do modelo: `sudo sh hermes/configurar.sh` e `docker restart hermes`.
- Tarefas agendadas: na tela Agenda do painel, junto com as do painel, ou `docker exec -u hermes hermes hermes cron list`. Se a ronda sumir, rode o instalador de novo (com as mesmas opções): ele cria a ronda e, nas atualizações, deixa o texto e as habilidades dela iguais aos do modelo (com o lab, `servidor-atena` e `lab`). À mão:
  ```bash
  docker exec -u hermes hermes hermes cron create "every 3m" "Ronda do servidor. Siga a seção Ronda das habilidades servidor-atena e lab." \
    --name ronda --monitor-script ronda.py --skill servidor-atena --skill lab --deliver telegram --failure-deliver ntfy
  ```
  (sem o lab, tire o `--skill lab`). Quando a IA não responde, a falha da ronda chega pelo ntfy, e não pelo Telegram da Atena calada.
- Bom-dia: às 8h, sem IA, o `bom_dia.py` manda no Telegram como o servidor amanheceu (containers, temperaturas, gasto do mês e o Claude Code da noite). Chega mesmo com a IA fora do ar. Mudar a hora: `docker exec -u hermes hermes hermes cron edit <id> --schedule "30 7 * * *"`.
- Lembretes de uma vez só somem 1 hora depois de rodar (`cron.completed_retention_days`); os diários, semanais e mensais continuam.
- O executor, à mão como ela faz: `docker exec -u hermes hermes python3 /opt/data/scripts/acao.py status.servicos` (a primeira linha é o código HTTP).
- Memória: `/srv/agents/hermes/memories` (USER.md e MEMORY.md) é dela; o instalador só põe a semente de `hermes/memoria` quando ainda não existe. Para conferir se ela guardou algo que já não vale: `python3 tests/hermes/teste_memoria.py <pasta com a cópia da memória>`.
- Gasto: pergunte a ela ("quanto gastamos este mês?").
- Atualizar o Hermes: leia as notas da versão, troque a imagem no compose e confira o `config.yaml` gerado. A documentação no GitHub é da versão em desenvolvimento, que pode ser mais nova que a sua.

## Lab (Claude Code)

**Instalar.** Ponha as contas do Claude Code em `ATENA_CLAUDE_CONTAS` (só nomes, ex.: `pessoal trabalho`; com uma, a Atena nem pergunta qual usar) e rode `sudo ./install.sh --hermes --lab` (ou `--lab`, se a Atena já estiver instalada). Depois, para cada conta:

```bash
sudo atena-claude-conta entrar pessoal    # mostra um link: entre na conta e cole o código
sudo atena-claude-conta estado            # quais contas estão prontas
```

**No dia a dia**, peça à Atena: "faz um app de lista de compras", "publica a lista-compras", "muda a cor do botão". Ela pergunta a conta (se houver mais de uma), o modelo e o esforço, manda o trabalho e para. O celular recebe o aviso de início (com Cancelar), os pedidos de permissão e as perguntas; a Atena manda o resumo quando termina.

- Projetos em `/srv/lab/projetos/<projeto>`, cada um com git (os commits são o jeito de desfazer). Para editar com o seu usuário, saia e entre de novo no SSH depois de instalar (grupo `atena-lab`).
- O seu Claude Code no lab: `cd /srv/lab && claude`. Vale o sandbox de `/srv/lab/.claude/settings.json`, mais o guarda de escopo.
- Apps publicados: `http://<ip-do-servidor>:<porta>` (8000-8999) e, com Tailscale, `https://<servidor>.<tailnet>.ts.net:<porta>`. Viram stacks `lab-<projeto>` no Dockge.
- Limite de uso: o trabalho para e a Atena pergunta se continua depois ou em outra conta. Para a troca automática, `ATENA_CLAUDE_TROCA=sim` no `/etc/atena/atena.conf`.
- Queda de energia no meio de um trabalho: ao voltar, o runner sobe sozinho e fecha o trabalho como interrompido (dá para continuar). Se nem o runner subir, o executor fecha no prazo (os minutos do trabalho mais 15 min) e libera o projeto.
- Skills: com `ATENA_CLAUDE_SKILLS=sim` no `atena.conf` e o instalador de novo, o login de cada conta já põe os plugins e o Impeccable. Para conferir ou refazer: `sudo atena-claude-conta skills` (com `nao`, o mesmo comando tira).
- Lixeira: `app.apagar` com `codigo` move a pasta para `/srv/lab/lixeira`; o `atena-lab-lixeira.timer` apaga de vez depois de 30 dias.
- Trocar a versão do Claude Code: `ATENA_CLAUDE_VERSAO` no `atena.conf` e o instalador de novo (ele baixa e confere o checksum oficial). Leia as notas da versão antes.
- Registros: `journalctl -u atena-claude` (o runner) e a conversa completa de cada trabalho em `/var/lib/atena-claude/registros`.

**Receitas de estilo** (com `ATENA_CLAUDE_SKILLS=sim`). Diga à Atena "gostei do estilo de https://exemplo.com" (ou use a tela Receitas do painel). O coletor abre o site em até 2 minutos, e o Claude Code escreve a receita em até 45; o celular avisa quando ela fica pronta. Para usar: "faz o projeto lista-compras no estilo da receita exemplo-com", ou o campo Estilo no trabalho novo do Lab. Também dá para perguntar "que receitas eu tenho?" ou "tem alguma escura?".

- A receita pronta fica em `/srv/lab/receitas/<nome>` (`RECEITA.md`, `DESIGN.md`, `receita.json` e os prints), e o estudo, com a coleta do site e o git, em `/srv/lab/projetos/receita-<nome>`. O índice fica em `/var/lib/atena-executor/receitas.db` e se refaz das pastas quando o executor sobe: perdê-lo não perde receita.
- A conta que escreve as receitas, quando o pedido não diz: `ATENA_RECEITAS_CONTA` no `atena.conf` (vazia, a primeira de `ATENA_CLAUDE_CONTAS` com login).
- Refazer: peça de novo com `refazer` (ou Refazer no painel). A receita atual continua valendo até a nova ficar pronta, e uma tentativa que falha não a apaga. Apagar (`receita.apagar`) pede o celular e não tem volta; o estudo no lab fica, e `app.apagar` tira.
- Estudo que parou (limite de uso, prazo, queda de energia): continue o trabalho do Claude Code da receita (`claude.tarefa` com `continuar`, ou Continuar no Lab) com "termine a receita"; ao terminar bem, ela é guardada.
- O coletor é a imagem `atena/coletor`, construída pelo instalador a partir de `host/lab/coletor`. Mudou o coletor: suba a tag em `COLETOR` no `host/executor/atena_executor/receitas.py` e no `install/88-lab.sh` (o teste confere que são iguais) e rode o instalador de novo.
- O REA (`rea-agents`, fixo no `package-lock.json` das ferramentas) e o Node do lab (fixo no `88-lab.sh`, com o checksum) mudam do mesmo jeito: a versão nova no repositório e o instalador de novo.

## Painel

**Instalar.** Precisa do Tailscale logado no servidor e do HTTPS ligado no tailnet (no painel do Tailscale: DNS → HTTPS Certificates). Rode `sudo ./install.sh --painel` e depois:

```bash
sudo atena-painel-senha    # a senha de entrada (num terminal; não aparece na tela)
```

O instalador mostra o endereço: `https://<servidor>.<tailnet>.ts.net:3100`. No celular, com o Tailscale ligado, abra o endereço no Chrome e use o menu ⋮ → **Instalar app**.

- **Na rede de casa, sem o Tailscale:** ponha `ATENA_PAINEL_CASA=sim` no `atena.conf` e rode `sudo ./install.sh --painel` de novo. O painel passa a abrir também em `http://<ATENA_LAN_IP>:3100`, em HTTP puro: a senha passa aberta no Wi-Fi, e lá ele não instala como app. Para tirar, volte para `nao` e rode o instalador de novo (as unidades `atena-painel-casa` e a regra do ufw saem).
- **Trocar a senha:** `sudo atena-painel-senha` de novo. Todos os aparelhos saem.
- **Aparelhos conectados:** na aba Ajustes, com o botão Desconectar.
- **Registros:** `docker logs painel` (o painel e o agendador) e `journalctl -u atena-executor` (cada pedido dele, com o cliente `painel` e a origem `agendamento` nos agendados).
- **Agendamentos:** ficam no banco do painel (`/srv/core/painel/painel.db`). Com o painel parado, nada roda; ao voltar, ele roda o que atrasou até a tolerância de cada um e marca o resto como perdido.
- **Tirar do ar:**
  ```bash
  sudo tailscale serve --https=3100 off
  sudo systemctl disable --now atena-painel-casa.socket 2>/dev/null   # se estava na rede de casa
  cd /opt/atena/stacks/core/painel && docker compose down
  sudo atena-executor token-remover painel
  ```
  Os dados ficam em `/srv/core/painel` até você apagar a pasta.

## Temperaturas e ventoinhas

`sistema.sensores` (e a Atena, quando você pergunta) lê a CPU, o NVMe e a GPU sem configurar nada. As ventoinhas vêm do chip da placa-mãe, que costuma precisar de um módulo do kernel: descubra qual com `sudo apt install lm-sensors && sudo sensors-detect`, ponha em `ATENA_SENSORES_MODULO` (ex.: `nct6683`) e rode o instalador de novo. A ronda avisa CPU acima de 85 °C, GPU acima de 85 °C e NVMe acima de 70 °C.

## PC da rede de casa

Opcional: a Atena liga o PC pela rede, usa o modelo dele para textos maiores e desliga quando você pede. O passo a passo está em [`host/windows/LEIAME.md`](../../host/windows/LEIAME.md).

Com `ATENA_PC_IP` no `atena.conf`, o LiteLLM ganha o modelo `pc`, a Atena o vê na lista dela, e o firewall dos containers deixa o LiteLLM chegar só à porta do LM Studio. Com o PC desligado, a chamada falha. Com `ATENA_PC_RESERVA` (ex.: `sonnet`), ela vai para esse modelo, e aí o texto sai de casa.

## Atualizar versões

As imagens têm versão fixa. Para atualizar:

1. Leia as notas da versão e os **avisos de segurança** do projeto (no GitHub, aba Security).
2. Prefira versões publicadas há pelo menos duas semanas. Correção de segurança importante é a exceção.
3. Troque a versão no compose e rode `docker compose up -d`.
4. **GPUs Pascal (GTX 10xx):** depois de atualizar o Ollama ou o Whisper, confira nos logs se a GPU continua sendo usada (`library=CUDA compute=6.1` no Ollama).

O driver da NVIDIA atualiza junto com o sistema, sempre dentro da mesma série. **Não use `apt-mark hold`** (veja as [lições](licoes.md)).

## Atualizar da 0.2 para a 0.3

`git pull` e `sudo ./install.sh` (com `--hermes`, se você usa a Atena). O instalador atualiza o executor, a habilidade e a personalidade, e refaz o token da Atena com as ações novas, mantendo as zonas e a regra de aprovação. Como as stacks que já existem não são sobrescritas, três passos são seus:

1. **LiteLLM** (para a voz): copie `stacks/ai/litellm/ganchos.py` para `/opt/atena/stacks/ai/litellm/`, acrescente o modelo `voz` e a linha `callbacks: ganchos.voz` do `config.yaml` do modelo e a montagem do `ganchos.py` do `compose.yaml`, e rode `docker compose up -d --force-recreate` na pasta.
2. **Chave da Atena** (para a voz): `sudo atena-hermes-chave [teto]` de novo, para a chave incluir o modelo `voz`.
3. **Ollama** (opcional): `OLLAMA_KEEP_ALIVE: 2m` no compose, se a GPU tiver de dividir espaço com o Whisper e a voz.

Depois, `/new` no Telegram.

## Atualizar o servidor pelo repositório

Depois de um `git pull`, `sudo ./aplicar`, na pasta do repositório, deixa o servidor igual a ele. Primeiro ele mostra o plano:
- **grava:** os arquivos que diferem ou faltam;
- **guarda no backup:** as sobras e as cópias antigas;
- **fica como está:** o que ele não mexe, com o motivo;
- **depois:** o que vai reiniciar.

Então ele pede confirmação (`--sim` pula a pergunta). Antes de mexer, guarda tudo o que vai mudar em `/var/backups/atena-aplicar/<quando>`. `sudo ./aplicar --desfazer` volta ao último backup, e `--backups` lista os que existem. Se um passo falha, ele desfaz sozinho.

Ele reinicia só o que mudou de verdade, e uma mudança só de comentário não reinicia nada:
- o systemd relê as unidades;
- o firewall e o executor reiniciam;
- o SSH confere a configuração nova antes de relê-la;
- cada stack que mudou sobe de novo e espera ficar saudável. Uma stack parada continua parada;
- por último, se o executor mudou, os tokens do painel e da Atena ganham as ações novas do catálogo.

`--parte executor` aplica só uma parte. Ele não começa com o Claude Code trabalhando quando o executor precisaria reiniciar. Ficam de fora, só avisados:
- o `/etc/docker/daemon.json`, porque aplicar reiniciaria todos os containers;
- uma stack que ainda não existe, que o instalador cria junto com os segredos dela;
- a memória da Atena, que só ganha a semente quando falta.

Uma stack de apps que a Atena editou com `stack.editar` volta à do repositório; o plano mostra isso antes.

## Conferir o servidor contra o repositório

`sudo ./aplicar --conferir`, na pasta do repositório, compara o servidor com o que o instalador poria nele, sem mudar nada. Os valores vêm do `/etc/atena/atena.conf`, e as opções (`--hermes`, `--lab`, `--painel`, `--ssh`) são descobertas pelo que já está instalado. Para cada parte (`host`, `executor`, `stacks`, `painel`, `hermes` e `lab`), ele lista:
- **difere:** o arquivo do servidor não é o do repositório, ou o modo e o dono não são. "Só nos comentários" quer dizer que o resto é igual;
- **falta:** o repositório põe o arquivo e o servidor não tem;
- **sobra:** o arquivo está numa pasta do modelo e não vem do repositório, como um drop-in feito à mão. As pastas do modelo são `/usr/local/sbin/atena-*`, as unidades `atena*` e os drop-ins delas, o executor e o código do painel;
- **cópias antigas:** os `.antes-*` que as trocas deixaram (`--copias` lista).

`--diff` mostra o que mudaria em cada arquivo, do servidor para o repositório, e `--parte executor,hermes` limita a conferência a essas partes. Sem `sudo`, o que só o root lê aparece com `?`. Ele sai com 0 quando está tudo igual.

Fica de fora o que é do servidor: os `.env`, os dados em `/srv`, as stacks que não vêm do repositório e a memória da Atena, que só precisa existir. Antes de uma troca à mão, rode o `--conferir`. Depois dela, ele mostra se a troca também precisa entrar no repositório.

## Rodar o instalador de novo

`sudo ./install.sh` pode rodar quantas vezes quiser:
- **Os valores** vêm do `atena.conf` da pasta do repositório, quando há um: ele passa a ser o do servidor, e uma cópia do anterior fica ao lado. Sem ele, o instalador lê o `/etc/atena/atena.conf`, e para mudar um valor basta editar esse arquivo.
- **Stacks que já existem** não são sobrescritas. A exceção é o painel: com `--painel`, o código dele vem sempre do repositório, e o compose anterior fica guardado se mudou. Para trazer as outras ao repositório, use o `sudo ./aplicar`.
- **Arquivos do sistema diferentes do modelo** são substituídos, e uma cópia do anterior fica ao lado (`*.antes-atena-<data>`).
