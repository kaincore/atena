# Segurança

## Princípios

- **Rede de casa confiável, o resto não.** Qualquer aparelho da rede de casa acessa os serviços. De fora, só pelo Tailscale. Da internet, nada.
- **Containers não alcançam a rede de casa.** Se um container for comprometido, ele não chega ao roteador, aos seus computadores nem aos aparelhos do Tailscale.
- **Zonas isoladas.** Um problema numa zona não alcança as outras.
- **Segredos fora do código.** Ficam em arquivos `.env` com permissão 600, gerados no servidor e nunca versionados.
- **Agentes só agem por uma lista fechada.** A Atena não tem Docker nem sudo: tudo o que ela faz no servidor passa pelo executor, que só conhece ações fixas.

## As camadas

### Servidor (ufw)
- Entrada bloqueada por padrão.
- SSH só da rede de casa e pela interface do Tailscale.
- Com `--ssh`: login só por chave, sem root e só para o administrador.

### Containers (atena-docker-firewall)
O ufw **não protege portas do Docker**: o Docker cria as próprias regras. Por isso a Atena usa a cadeia `DOCKER-USER`, que o Docker consulta antes das regras dele.

**Saída (cadeia `ATENA-EGRESS`):**
- Libera respostas, o tráfego entre containers (o Docker já isola as redes) e o DNS do roteador.
- Bloqueia a interface do Tailscale e as faixas privadas: `192.168.0.0/16`, `172.16.0.0/12`, `10.0.0.0/8`, `100.64.0.0/10` e `169.254.0.0/16`.
- Ao ser aplicado, derruba as conexões que containers já tinham aberto para a rede de casa e o Tailscale. Uma regra nova não corta conexões já estabelecidas.

**Entrada:** só respostas e conexões novas vindas da rede de casa para o IP do servidor. O resto é descartado, mesmo que uma porta tenha sido publicada em `0.0.0.0` por engano.

As regras sobem **antes do Docker** (`Before=docker.service`). Assim, nenhum container chega a rodar sem elas.

### Portas publicadas
São três camadas para nenhuma porta escapar por engano:
1. Os composes escrevem o IP em toda porta.
2. As redes das zonas usam `host_binding_ipv4=127.0.0.1`: uma porta publicada sem IP fica só no servidor.
3. O firewall de entrada descarta o resto.

### Executor
- **Sem shell.** Cada ação roda um comando fixo; os parâmetros são conferidos contra o que existe (stack, unidade, caminho) e contra uma lista de formatos.
- **Token por cliente**, guardado só como hash, com as ações e as zonas que ele pode pedir. Revogar vale na hora.
- **Aprovação no celular.** O código de cada pedido só existe dentro da notificação, num tópico do ntfy que só você lê. O pedido vale 10 minutos, cada cliente tem no máximo 5 esperando, e a zona é conferida de novo na hora de rodar.
- **Serviço fechado.** Roda como `atena-exec`, com `ProtectSystem=strict`, `NoNewPrivileges` e só uma capacidade: `CAP_DAC_READ_SEARCH`, que lê arquivos e não escreve.
- **Segredos não saem.** `/proc`, `/run`, `/var/lib/docker`, `/etc/atena/executor`, pastas como `.ssh` e arquivos como `.env`, `*.key` e `tokens.json` são recusados, inclusive por atalho. No texto que sai, valores de senha, token e chave viram `***`.

### Atena (Hermes)
- **Sem Docker e sem sudo.** O usuário `hermes` só está no grupo `atena-acoes`, que dá acesso ao socket do executor. O instalador para se o `hermes` estiver no grupo `docker`.
- **Token sem a zona `prod`.** Sistemas de clientes ficam fora do alcance dela.
- **Só o dono conversa.** O Telegram aceita só o seu ID; mensagens de outras pessoas são ignoradas, sem resposta.
- **Conteúdo é dado, não ordem.** A `SOUL.md` manda tratar páginas, documentos e mensagens de terceiros como dados. Comandos no container dela passam pela aprovação "smart", e o destrutivo vai para você.
- **Chave do LiteLLM com teto mensal.** Um erro dela não esvazia o crédito da API.

### Lab (Claude Code)
- **Sem sudo e sem Docker.** O `atena-claude` só está nos grupos `atena-fila` e `atena-lab`. O instalador para se ele estiver no grupo `docker`.
- **Sandbox obrigatório e sem saída.** Escrita só na pasta do projeto; Docker, executor, D-Bus, systemd, as outras zonas e as credenciais das contas ficam escondidos; internet só para repositórios de pacotes. Se o sandbox não subir, o Claude Code não roda.
- **O projeto não configura o Claude Code nem o git.** Só valem a configuração da conta e o `lab.json`; hooks do projeto ficam desligados; o git do runner ignora fsmonitor e hooks, e um `.git/config` que rode comandos faz o trabalho ser recusado.
- **O que sai do servidor passa pelo celular.** `git push`, páginas web e edição fora da pasta viram pedido de permissão; sem resposta, é negado.
- **Apps do lab fechados.** Disco só de leitura, sem capacidades, `no-new-privileges`, 512 MB, só a rede `zone-lab`. Publicar e apagar pedem o celular por padrão.
- **Tailscale só pelo polkit.** O executor só consegue iniciar as unidades `atena-lab-tailscale-on@` e `-off@`, nas portas 8000-8999.

### Painel
- **Sem rede, sem root e sem Docker.** `network_mode: none`, disco só de leitura, sem capacidades, `no-new-privileges`, 256 MB. O usuário `atena-painel` só está no grupo `atena-acoes`; o instalador para se ele estiver no grupo `docker`.
- **Entrada pelo Tailscale**, por um socket que só o root e o painel abrem (`/srv/core/painel` é 700). A da rede de casa (`ATENA_PAINEL_CASA=sim`) é um segundo socket ao lado, aberto pelo repassador do systemd, que roda como `atena-painel`, sem rede própria e sem capacidades.
- **Senha difícil de adivinhar por força bruta:** scrypt (N=2^15, 32 MB por tentativa), 5 erros em 15 minutos bloqueiam a entrada por onde vieram (o Tailscale ou a rede de casa: quem erra no Wi-Fi não tranca o dono fora de casa), e uma conferência por vez.
- **Cookie** HttpOnly, Secure (pelo Tailscale) e SameSite=Strict. Todo POST exige JSON e um cabeçalho próprio, o que barra formulários de outros sites (CSRF).
- **CSP** que só aceita o próprio painel, sem frames. As telas são montadas sem `innerHTML`, então um nome de container ou uma linha de log nunca vira código.
- **Token próprio, sem aprovação no celular:** 38 ações. A única que apaga é `app.apagar`, só no lab: o código vai para a lixeira por 30 dias, e apagar os dados exige digitar o nome do app. Edita só as stacks da zona apps, sempre com foto antes, e lê o servidor menos os segredos, como a Atena. Quem tem a senha do painel tem esse alcance: é mais um motivo para uma senha só dele.
- **Agenda:** o agendador só roda as ações da lista de agendáveis (PC, reiniciar serviço, apps do lab), e a vez que passou da tolerância não roda depois.
- **Decidir pelo painel vale o toque no celular.** Só o token do painel tem `aprovacoes.decidir`; ele não decide pedidos dele mesmo (fora as permissões e perguntas do Claude Code nos trabalhos que ele mandou), e só enxerga pedidos de clientes das zonas dele (sem `prod`). Quem tem a senha do painel aprova o que a Atena pedir: é mais um motivo para uma senha só dele.

## O que foi testado no servidor original

| Teste | Resultado |
|---|---|
| Container da zona `agents` tentando o roteador, a rede de casa, o Tailscale e o SSH do servidor | Bloqueado |
| O mesmo container tentando a internet e o DNS | Liberado |
| Uma máquina simulada fora da rede de casa (namespace de rede) tentando um container publicado em `0.0.0.0` | Bloqueado. Sem a regra, passou, o que prova que o teste detecta a falha |
| Zona diferente tentando alcançar outra | Isolado |
| Os mesmos testes depois de reiniciar o Docker e o servidor | Mesmo resultado |
| Login por senha e como root no SSH | Recusado |
| A Atena pedindo ao executor `/etc/shadow`, um `.env` e uma chave SSH | Recusado (403) |
| Aprovação com código errado, toque repetido e pedido vencido | Nada rodou |
| Cliente pedindo ação fora do token ou stack de outra zona | Recusado (403) |
| Claude Code do lab escrevendo fora da pasta do projeto e usando `sudo` e o socket do Docker | Barrado pelo sandbox |
| Projeto com `core.fsmonitor` no `.git/config` | Trabalho recusado, sem abrir o Claude Code |
| Painel: ação fora da lista dele, POST sem o cabeçalho próprio, formulário de outro site | Recusado (403, 415), sem chegar ao executor |
| Painel: senha errada 5 vezes, depois a certa | Bloqueado por 15 min |
| Painel: `docker inspect` do container e a porta 3100 pela rede de casa | Sem rede, sem o socket do Docker; nada responde na rede de casa (com `ATENA_PAINEL_CASA=nao`, o padrão) |

Os testes automáticos do executor, da ronda e do lab ficam em `tests/`, os do painel em `stacks/core/painel/app/test/`, e todos rodam a cada envio ao GitHub.

## O que a Atena NÃO protege

- **O administrador e o Dockge têm acesso total.** O Dockge e o agente do Beszel usam o socket do Docker, que equivale a root. Quem entra no Dockge manda no servidor. Use senha forte.
- **Serviços sem senha ficam abertos para toda a rede de casa.** Os apps do lab, por exemplo, não têm login: qualquer aparelho do Wi-Fi pode abri-los.
- **As zonas dividem o mesmo kernel.** Uma falha grave de escape de container atravessaria as zonas. Para isolamento forte, use máquinas virtuais.
- **IPv6 dentro dos containers** não é usado. Se você ativar IPv6 nas redes do Docker, revise o firewall, que hoje só tem regras de IPv4.
- **Quem tem a senha do painel** reinicia serviços e desliga o PC, sem passar pelo celular. Use uma senha que você não usa em outro lugar.
- **O executor tem acesso ao Docker.** Isso equivale a root. A proteção é a lista fechada: um defeito no executor seria um defeito de segurança do servidor inteiro.
- **O filtro de segredos é por nome e por formato.** Um segredo num formato desconhecido, dentro de um arquivo de nome comum, pode passar. Guarde segredos em `.env`, `*.key` ou `*.token`.
- **O que a Atena lê vai para o modelo na nuvem** (Anthropic), menos o que passa por `local.processar`.
- **Painel na rede de casa (`ATENA_PAINEL_CASA=sim`) é HTTP.** Quem escuta o Wi-Fi pode ler a senha e o cookie da sessão, e com o cookie entra como você até a sessão vencer. O cookie também vai junto para os outros serviços do mesmo IP (Dockge, Beszel, ntfy), porque o cookie não separa portas. Prefira o Tailscale, e troque a senha (`sudo atena-painel-senha`, que derruba as sessões) se desconfiar de alguém na rede.
- **ntfy sem HTTPS na rede de casa.** Com `http://`, quem escuta o Wi-Fi pode ver o código de um pedido e aprovar antes de você. Fora de casa, use o endereço `https://` do Tailscale em `ATENA_NTFY_URL`.
- **Injeção de instruções** (um texto que tenta mandar na IA) é reduzida pelas regras e pela aprovação, não eliminada. Por isso a Atena só faz sem aprovação o que tem volta.
- **O Claude Code do lab baixa pacotes da internet** (npm, PyPI, GitHub). Um pacote malicioso roda dentro do sandbox, só na pasta do projeto, mas pode ir parar num app publicado. Leia o que ele instalou antes de publicar algo importante.
- **O Claude Code roda na sua assinatura.** O que ele lê no projeto vai para a Anthropic, como numa conversa.
- **Outros encaminhamentos de tráfego** (máquinas virtuais, subnet router do Tailscale) são descartados pela última regra da `DOCKER-USER`. Se precisar deles, crie exceções.

## Antes de publicar algo

O repositório tem uma trava (`tools/hooks/pre-commit`) e uma verificação no GitHub (gitleaks). Mantenha a sua lista de dados pessoais em `~/.config/atena/padroes-privados.txt`, **fora** do repositório.
