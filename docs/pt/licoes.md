# Lições aprendidas

Armadilhas encontradas montando o primeiro servidor Atena. Cada uma custou um teste que falhou, ou pior, um teste que passou sem provar nada.

## Rede e firewall

**O `"ip": "127.0.0.1"` do `daemon.json` só vale para a rede padrão do Docker.**
O primeiro teste usou a rede padrão e passou. Mas as redes das zonas publicavam em `0.0.0.0`, e um serviço ficou visível na rede de casa por alguns minutos. A solução usa três camadas: IP explícito nos composes, `host_binding_ipv4=127.0.0.1` nas redes e um firewall de entrada.

**O ufw não protege portas do Docker.**
O Docker cria as próprias regras de NAT e encaminhamento, que passam por fora do ufw. Use a cadeia `DOCKER-USER`.

**Regra nova não corta conexão já aberta.**
Um ping ao roteador continuou passando depois do bloqueio, porque a conexão já estava registrada (conntrack) e cada teste a mantinha viva. O firewall agora roda `conntrack -D` ao ser aplicado e sobe antes do Docker.

**Um teste feito de dentro do servidor engana.**
O tráfego que o próprio servidor gera não passa pelas mesmas regras que o tráfego de outra máquina. Para testar a entrada, simule outra máquina com um namespace de rede (`ip netns`) ou teste de outro aparelho.

**O `tailscale serve` escuta pelo kernel.**
Sem uma regra no ufw para a interface `tailscale0`, os outros aparelhos ficam bloqueados. De dentro do servidor, porém, o teste passa.

## GPU (placas Pascal, como a GTX 1060)

**O CUDA 13 não suporta Pascal.**
O Ollama recente ignora as bibliotecas do CUDA 13 para essa placa e usa as do CUDA 12. Use imagens baseadas no CUDA 12 e confira nos logs se a GPU continua em uso depois de cada atualização.

**Com Secure Boot, `apt-mark hold` no driver quebra a GPU.**
Os módulos assinados do kernel acompanham a versão do driver. Travar o driver separa os dois na próxima atualização do kernel. O pacote já é por série (`-580`), e o apt nunca troca de série sozinho.

**Pascal é lento em float16.**
No Whisper (faster-whisper/CTranslate2), use `int8`. A GTX 1060 suporta DP4A, então o int8 roda rápido.

**Na voz (Kokoro, ONNX), é o contrário: use a versão completa (fp32).**
A int8 cai para a CPU nas placas Pascal e fica cerca de 5 vezes mais lenta.

**A memória da voz na GPU cresce com o texto.**
Números e porcentagens viram muitos fonemas: 837 letras passaram de 3,4 GB e travaram o pedido numa placa de 6 GB, e 300 letras chegaram a 4,2 GB. Em pedaços de 150 letras, a voz fica em ~2,2 GB. Por isso o Hermes fala em pedaços (`tts.openai.max_text_length 150`) e o LiteLLM desiste em 10 s, sem repetir.

**Três modelos não cabem juntos em 6 GB.**
Ollama (3,2 GB), Whisper (1,1 GB) e voz (2,2 GB) passam do limite. Cada um sai da GPU sozinho depois de um tempo parado: a voz em 60 s, o Ollama em 2 min e o Whisper em 10 min (ouvir rápido importa mais).

## LiteLLM e a API do Claude

**Haiku, Sonnet e Opus 5.5 recusam `temperature`, `top_p` e `top_k` fora do padrão** (erro 400). Vários clientes mandam esses parâmetros. Use `additional_drop_params` em cada modelo.

**O teto por modelo nas chaves (`model_max_budget`) é recurso pago do LiteLLM.**
Na versão gratuita, use `max_budget` + `budget_duration` em cada modelo. Também é preciso um **Redis**: sem ele, o gasto fica só em memória e zera a cada reinício.

**O `id` do modelo não pode ser igual ao `model_name`.**
Se for, o LiteLLM trata a chamada como "modelo específico" e **pula o teto**. O teste mostrou o gasto acima do limite e as chamadas passando.

**O teto por modelo conta a partir do primeiro gasto, e não do dia 1º.**
Um agendamento do systemd zera os contadores todo dia 1º. Os tetos das chaves usam `budget_duration: 1mo`, que já renova no dia 1º.

**Modelos novos podem não estar no mapa de preços do LiteLLM.**
Sem preço, o custo registrado é zero e o teto nunca bloqueia. Coloque os preços em `model_info`.

**Teste tetos com um teto menor que uma chamada.**
Na primeira tentativa, cada chamada custava US$ 0,0000037 e o teto era US$ 0,00002: o teste "passou" sem provar nada.

## Docker e Compose

**`sed -i` troca o arquivo, e um bind mount de arquivo único continua vendo o antigo.**
Depois de editar um arquivo montado sozinho (como o `config.yaml`), use `docker compose up -d --force-recreate`, e não `restart`.

**O Dockge não lê subpastas** (pedido #687 do projeto). A solução é uma pasta de atalhos mantida por um `.path` do systemd.

**A primeira pessoa que abre o Dockge, o Beszel ou o Open WebUI vira administradora.** Crie as contas logo depois de subir.

**`docker compose config` junta o `env_file` no `environment`, e o caminho some.**
Para conferir de onde vêm as variáveis (e barrar um `.env` de outra stack), leia o compose uma segunda vez com `--no-interpolate`: é a única forma que mostra o caminho em todas as versões. O `--no-env-resolution` só funciona no Compose v5; no 2.x o caminho some mesmo com ele, e a regra deixava passar o `.env` de outra stack. Quem achou foi o CI do GitHub, que roda um Compose 2.x.

## Executor, ntfy e Hermes

**Monte a pasta do socket, não o arquivo.**
O socket do executor é recriado a cada reinício. Com o arquivo montado, o container do Hermes ficava olhando o socket antigo. Monte a pasta `/run/atena-executor` e use `RuntimeDirectoryPreserve=yes` na unidade, senão o systemd recria a pasta e o container perde o caminho.

**O Hermes precisa de `command: ["gateway", "run"]`.**
Sem isso, o container abre o chat interativo, sai e reinicia sem parar.

**A documentação do Hermes no GitHub é da versão em desenvolvimento.**
Algumas chaves ainda não existiam na versão instalada. Confira no `config.yaml` que ela gera, e configure com `hermes config set`, que valida cada chave.

**ntfy: tópicos em minúsculas, e o celular precisa assinar todos.**
O teclado do celular põe maiúscula sozinho (`Aprovacoes` é outro tópico). E quem assina só `atena` não vê os pedidos de aprovação, que vão para `aprovacoes`.

**O botão de aprovação chama o endereço que o celular alcança.**
O executor publica no ntfy por `127.0.0.1`, mas o botão vai para o celular: ele precisa do endereço da rede de casa ou do Tailscale (`ATENA_NTFY_URL`).

**Uma ação aceita não é uma ação concluída.**
A Atena dizia "reiniciei" quando o pedido ainda esperava o celular. A `SOUL.md` agora manda conferir o resultado antes de afirmar, e o executor responde 202 enquanto o pedido espera.

**Texto privado não passa pelo LiteLLM.**
O LiteLLM pode cair para um modelo da nuvem quando o modelo de casa não responde. O `local.processar` fala direto com o Ollama ou o LM Studio.

**O qwen3 4B "thinking" escreve o raciocínio antes da resposta e gasta o limite de saída.**
Use a versão instruct (`qwen3:4b-instruct-2507`) e mande `/no_think`.

**No Ubuntu 26.04, o `install` não copia de `/dev/stdin` por cima de um arquivo que já existe.**
O `install` agora é o do uutils (coreutils em Rust) e responde só "No such file or directory". Num arquivo novo funciona, por isso o primeiro token da Atena gravava e a troca na atualização falhava, deixando no arquivo um token já revogado. Grave num arquivo novo e mova, ou use `tee` num arquivo que já existe. Achado no teste em VM da 0.3.

**Depois de desligar, o PC continua "ligado" na tabela de vizinhos por alguns minutos.**
O executor trata o SSH sem rota como "desligado", em vez de dar erro.

**Procure o cabeçalho do bloco PEM, não só "PRIVATE KEY".**
Recusar qualquer texto com "PRIVATE KEY-----" barrava arquivos que só citam o trecho, como o próprio executor. O que identifica uma chave é `-----BEGIN ... PRIVATE KEY-----`.

**O executor escreve no lugar, sem trocar o arquivo.**
Uma stack pode montar um arquivo sozinho, e o app pode reescrever os arquivos dele enquanto roda. Gravar um arquivo novo e renomear trocaria o dono e o inode; `stack.editar` escreve no mesmo arquivo.

**O Speaches não gera opus.**
O Hermes pede a voz em opus (formato das mensagens de voz do Telegram) e o Speaches responde 422. Um gancho no LiteLLM troca o pedido para mp3, e o Hermes converte de volta com o ffmpeg. O Hermes manda a voz antes do texto, então o texto espera a fala ficar pronta.

## Lab (Claude Code)

**No Ubuntu 26.04, o sandbox do Claude Code precisa de `allowAllUnixSockets`.**
O AppArmor tira as capacidades de tudo que roda dentro do bubblewrap, e o ajudante de seccomp do Claude Code (que bloqueia sockets locais) aborta. Todo comando falhava no sandbox, era repetido fora dele e virava um pedido de permissão. Sem o ajudante, os sockets perigosos (Docker, executor, D-Bus, systemd) ficam escondidos pelo `denyRead`.

**Um servidor de teste esquecido em segundo plano segura o `claude -p` aberto.**
O resumo final já tinha saído, mas o processo não fechava, e o trabalho só terminaria no limite de tempo, como erro. O runner fecha o Claude Code 30 s depois do resumo final, e as regras pedem que nada fique rodando em segundo plano.

**Depois de trocar de conta, leia só a rodada nova do registro.**
O aviso de "limite atingido" da conta anterior continuava no registro; se a rodada nova não mandasse outro aviso, o trabalho parava à toa.

**Se alguém além do Claude Code escreve nos projetos, o projeto não pode configurar nada que rode fora do sandbox.**
`--setting-sources user` (sem hooks e sem `apiKeyHelper` do projeto) e o git com `core.fsmonitor=false` e `core.hooksPath=/dev/null` no ambiente. Um `.git/config` com fsmonitor rodaria um programa do projeto no próprio runner.

**Mover para a lixeira é um rename.** Com `ReadWritePaths` separados para os projetos e para a lixeira, o systemd monta os dois à parte e o rename falha (`EXDEV`). Um `ReadWritePaths=/srv/lab` só resolve.

**No Ubuntu 26.04, o `/usr/bin/test` (uutils) ignora ACL.**
`sudo -u atena-claude test -w arquivo` disse que não dava para escrever num arquivo liberado por ACL, e dava. O `test` embutido do bash e o `os.access` do Python acertam. Achado no teste em VM da 0.4.

**Para continuar uma conversa em outra conta, copie a sessão.** O `--resume` procura a conversa na pasta da conta (`projects/*/<sessão>.jsonl`); o runner copia o arquivo, e a pasta de subagentes, antes de continuar.

**Servidor MCP do Claude Code roda fora do sandbox.** O sandbox vale para o Bash; um servidor MCP é um processo do próprio Claude Code, com a rede e o disco do usuário. Por isso o REA das receitas entra pela linha de comando (`rea ...` no Bash), sob as mesmas travas do resto, e não como servidor MCP.

**O REA na pasta inteira de scripts de um site desiste.** O `analyze-javascript-application` com os 393 scripts de um site passou do limite de 5 min por fonte e parou sem resultado. Com até 5 scripts de cada vez leva segundos, e o registro da rede (`inspect-web-network-capture` no HAR) leva 3 s. A skill `receita` manda escolher os scripts antes.

**O REA pede um Node mais novo que o do Ubuntu.** O `rea-agents` 6.8.0 quer 22.23.4+ ou 24.22.1+, e o Ubuntu 26.04 tem o 22.22.1. O lab ganhou um Node próprio (fixo, do nodejs.org, conferido pelo checksum) na frente do PATH do trabalhador, sem mexer no do sistema.

## Painel

**O `tailscale serve` entrega num socket unix** (`unix:/caminho/do.sock`). Assim o container do painel fica sem rede nenhuma (`network_mode: none`), e ainda assim tem HTTPS fora de casa. O ufw continua precisando liberar a porta na `tailscale0`.

**O Node do Ubuntu 26.04 não roda TypeScript direto.** A partir do 22.18, o Node oficial roda `.ts` sem compilar e traz o `node:sqlite`, o que deixou o painel sem nenhum pacote do npm. O pacote `nodejs` do Ubuntu (22.22) responde `ERR_UNKNOWN_FILE_EXTENSION`: use a imagem oficial do Node.

**No Node 22, `node --test pasta/` não funciona.** Ele tenta abrir a pasta como arquivo. Passe o padrão: `node --test 'test/*.test.ts'`.

**O atributo `hidden` perde para o `display` de uma classe.** A tela de senha aparecia embaixo do painel, porque `.entrada { display: grid }` vencia o `hidden`. Resolve com `[hidden] { display: none !important; }`.

**Uma CSP sem `'unsafe-inline'` bloqueia o atributo `style`.** A largura das barras tem de ir pelo `elemento.style.width`, que a CSP permite.

**`grep` sem resultado num pipeline com `pipefail` encerra o script calado.** O verificador de vazamentos travava todo commit quando um `.env` do servidor só tinha valores curtos. Um `{ grep ... || true; }` resolve.

## Aplicativos

**Envio de arquivos com Express (`express-fileupload`):**
- Sem `defParamCharset: 'utf8'`, nomes com acento chegam corrompidos ("ação" vira "aÃ§Ã£o").
- Sem `abortOnLimit: true`, um arquivo acima do limite é **salvo cortado** e a resposta diz "sucesso".
- Nome de arquivo inserido no HTML sem tratamento permite injeção de código.

## Sobre testes

**O teste tem que conseguir falhar.** Três vezes um teste "passou" por motivo errado:
- um servidor de teste sem páginas devolvia 404, e isso foi contado como "bloqueado";
- o `xargs -r` sem entrada devolve sucesso;
- o teto do LiteLLM era maior do que as chamadas de teste conseguiam gastar.

Sempre que possível, rode o mesmo teste também **com a proteção desligada** e confirme que ele detecta a falha.
