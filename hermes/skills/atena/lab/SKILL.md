---
name: lab
description: "Programar no lab do servidor Atena: mandar trabalhos de programação ao Claude Code (apps, scripts, sites), repassar as perguntas dele ao dono, programar você mesma nos projetos do lab pelo terminal, cuidar dos apps do lab (publicar na rede de casa, rodar comandos dentro deles, reiniciar, parar, cancelar, apagar e restaurar) e as receitas de estilo (estudar o visual de um site que o dono gostou e usar nos projetos). Use sempre que o dono pedir um programa, app, script ou site, falar de um projeto do lab ou de um app publicado, disser que gostou do estilo de um site, e quando a ronda trouxer uma linha do Claude Code."
version: 1.4.0
author: Atena
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [lab, claude-code, apps, atena]
    category: atena
---

# Lab: Claude Code e apps

O lab é a zona de testes do servidor. Os projetos ficam em `/srv/lab/projetos/<projeto>`. As ações
abaixo passam pelo executor, do mesmo jeito da habilidade servidor-atena (pelo
`/opt/data/scripts/acao.py`).

Quem faz o quê:
- Claude Code (`claude.tarefa`): programação grande (app novo, várias telas, horas de trabalho). Até
  3 projetos ao mesmo tempo. Roda na assinatura do dono, não na sua API.
- Você mesma no lab (terminal): ajuste pequeno, ler código, rodar testes, conferir um app, conserto
  rápido (veja "Você mesma no terminal").

## Claude Code

Quando o dono pedir um programa, app, script ou site ("faz um app de lista de compras", "cria um
script que..."), quem faz é o Claude Code: ele trabalha sozinho, por minutos ou horas, numa pasta
do lab, num sandbox estrito: escreve só nessa pasta e não tem como sair dele. O celular do dono só
recebe pedido de permissão para `git push`, páginas web e edição de arquivo fora da pasta.

| Ação | Params | O que faz |
|---|---|---|
| `claude.trabalhos` | — | As contas do Claude Code (`contas`), as que têm login (`contas_com_login`), as `skills` (só se o dono ligou as skills no servidor) e os 10 últimos trabalhos, com estado |
| `claude.tarefa` | `pedido`, `projeto`, `conta?` (uma de `contas`; com uma conta só, ela vale sozinha), `modelo?` (`fable`, `opus`, `sonnet`, `haiku`), `esforco?` (`low`, `medium`, `high`, `xhigh`, `max`), `minutos?` (5 a 600, padrão 60), `skill?` (uma de `skills`; veja Skills do Claude Code), `receitas?` (até 3 nomes de receitas prontas; veja Receitas de estilo), `somente_plano?`, `continuar?`, `publicar?` | Começa um trabalho; responde 202 com o id. Com `publicar: true`, publica a versão nova sozinho quando terminar bem |
| `claude.cancelar` | `pedido` (id do trabalho) | Interrompe um trabalho em andamento (a conversa fica guardada) |
| `claude.perguntas` | — | Perguntas do Claude Code esperando resposta: `id`, `projeto`, `pergunta`, `opcoes`, `por_que`, `esperando_min` |
| `claude.responder` | `pergunta` (id), `resposta`, `quem` (`dono` ou `atena`) | Manda a resposta ao Claude Code, que estava parado esperando |

Como fazer:
1. Veja com `claude.trabalhos` as contas e quais têm login. Pergunte ao dono, numa mensagem só, o
   que faltar: a conta (se houver mais de uma com login), o modelo e o esforço, e quanto tempo pode
   levar. Se só uma conta tiver login, diga qual vai usar em vez de perguntar. Se ele não quiser
   escolher, deixe modelo e esforço de fora (vale o padrão da conta).
   - Modelo: `fable` (o mais capaz), `opus` (muito bom), `sonnet` (equilibrado), `haiku` (rápido e
     barato).
   - Esforço (quanto ele pensa antes de agir): "baixo" `low`, "médio" `medium`, "alto" `high`,
     "muito alto" `xhigh`, "máximo" `max`. Mais modelo e mais esforço gastam mais do limite da conta.
   - A regra "Opus só com ok" da sua alma vale para o SEU modelo (pago por uso, pela API). O Claude
     Code roda na assinatura do dono: qualquer modelo e esforço que ele pedir, mande direto.
   Projeto novo ou grande com decisões em aberto (quem usa, o que entra na primeira versão, como
   deve parecer): na MESMA mensagem, faça até 5 perguntas curtas, cada uma com a sua sugestão
   ("Sugiro X, porque Y"). Se ele disser "segue" ou "tanto faz", use as suas sugestões. Pedido
   pequeno ou já claro: não pergunte nada além da conta, mande direto.
2. Escolha um nome curto para o projeto (minúsculas e hífen, ex.: `lista-compras`). Para mexer num
   projeto que já existe, use o mesmo nome.
3. Escreva o `pedido` completo e claro, com tudo o que o dono disse e decidiu (o que fazer, porta,
   linguagem, as respostas das perguntas, o estilo visual se ele falou): é tudo o que o Claude Code
   vai saber. Se `claude.trabalhos` trouxe `skills`, escolha a `skill` pela tabela de Skills do
   Claude Code (ou deixe de fora). Mande `claude.tarefa`.
4. Responda ao dono que começou (id, pasta e, se usou, a skill em palavras simples: "com o polish do
   Impeccable") e PARE. Não acompanhe com `GET /pedido` nem
   `claude.trabalhos` enquanto ele trabalha: cada consulta gasta. O dono recebe no celular o aviso
   de início (com Cancelar) e os pedidos de permissão.
5. Quando o trabalho terminar, a ronda te acorda (veja Ronda) e você manda o resumo.

Continuar e trocar:
- Continuar um trabalho terminado (ajustes, "agora adiciona X"): `claude.tarefa` com
  `"continuar": "<id>"` e o novo `pedido`. Vem a mesma conta, o mesmo projeto e a conversa anterior.
- Trocar o modelo ou o esforço no meio: não dá. Faça `claude.cancelar`, espere o estado virar
  `cancelado` (`GET /pedido/<id>`, segundos) e mande `claude.tarefa` com `continuar` (o id
  cancelado), o `modelo`/`esforco` novos e o pedido "Continue de onde parou". Num `continuar`,
  modelo e esforço vêm do trabalho anterior, a menos que você mande outros.
- Limite de uso da assinatura: se a conta bater o limite no meio, o trabalho para (estado `falhou`,
  e o resumo diz a hora em que a conta volta). Conte ao dono e pergunte: continuar depois, na mesma
  conta, ou já em outra (`claude.tarefa` com `continuar` e a `conta` nova; a conversa vai junto).
  Se o servidor estiver com a troca automática ligada, ele passa sozinho para outra conta e o
  resultado traz `trocas`.
- Servidor caiu no meio (queda de energia, reinício): o trabalho termina `falhou`, com o resumo
  começando por "interrompido"; com `sessao`, dá para continuar de onde parou (`claude.tarefa` com
  `continuar`): conte ao dono e pergunte se segue. Sem resultado nenhum, o executor fecha o trabalho
  no prazo (os minutos dele mais 15 min), com o motivo em `erro`: aí só dá para pedir de novo.
- `somente_plano: true` faz só um plano, sem mudar nada.
- Até 3 trabalhos rodam ao mesmo tempo (e mais 2 esperam na fila), um por projeto.
- Erro 409 "ainda não tem login": diga ao dono para rodar no servidor
  `sudo atena-claude-conta entrar <conta>`. Erro 503: o lab não está instalado neste servidor.

### Skills do Claude Code (só se `claude.trabalhos` trouxer `skills`)

Com as skills ligadas, o Claude Code do lab já usa sozinho: frontend-design (direção visual de tela
nova), impeccable (refinar telas), tdd, diagnosing-bugs (bug difícil), prototype e revisão do
próprio diff; e confere as telas com prints (`atena-tela`). O campo `skill` serve para FORÇAR um
caminho quando o pedido do dono pede isso. Uma skill por trabalho; na dúvida, deixe de fora. O dono
não precisa saber os nomes.

| O dono pede | `skill` |
|---|---|
| App ou site novo com tela | `frontend-design` |
| "deixa mais bonito", "capricha", "dá um acabamento" | `impeccable polish` |
| "o que está ruim nessa tela?", "dá uma olhada no visual" (só avaliar, sem mudar) | `impeccable critique` |
| "revisa acessibilidade, contraste, celular, desempenho" (relatório técnico) | `impeccable audit` |
| "mais discreto/sóbrio" / "mais chamativo, com personalidade" | `impeccable quieter` / `impeccable bolder` |
| cores / fontes e textos / organização e espaçamento | `impeccable colorize` / `impeccable typeset` / `impeccable layout` |
| "funciona bem no celular?", responsivo | `impeccable adapt` |
| animações, movimento | `impeccable animate` |
| simplificar a tela / textos confusos | `impeccable distill` / `impeccable clarify` |
| telas de erro, vazio, casos estranhos | `impeccable harden` |
| primeiro uso, boas-vindas, tutorial | `impeccable onboard` |
| "está lento" (front-end) | `impeccable optimize` |
| "cria a identidade visual do projeto" | `impeccable init` (gera PRODUCT.md e DESIGN.md; faz perguntas ao dono pelo celular) |
| "o código está bagunçado", "organiza", "melhora a arquitetura" | `improve-codebase-architecture` |
| Projeto grande, de várias partes | `to-spec`, depois `implement-spec` (veja abaixo) |

Projeto grande (várias telas ou funções, mais de uma noite de trabalho):
1. Faça as perguntas do passo 1 e mande `claude.tarefa` com `skill: "to-spec"` e o pedido com tudo
   o que foi decidido. Ele escreve a especificação em `.scratch/` no projeto, sem programar.
2. Quando terminar, mande ao dono o resumo da especificação em poucas linhas e, na mesma hora,
   `claude.tarefa` com `continuar` (o id do to-spec), `skill: "implement-spec"`, `minutos` maior
   (ex.: 240) e o pedido "Implemente a especificação". Não espere ok: ele pode cancelar pelo celular.
3. Muito grande (dias): entre os dois passos, `skill: "to-tickets"` quebra em tarefas pequenas.
Depois de um trabalho longo que deu problemas, `skill: "retro"` com `continuar` faz uma retrospectiva
curta do que aprender (só se o dono pedir ou se o trabalho falhou mais de uma vez).

## Receitas de estilo (só se `claude.trabalhos` trouxer a skill `receita`)

Quando o dono gostar do visual de um site ou de um programa ("gostei do estilo desse site", "guarda
o jeito desse app"), estude e guarde a receita: o Claude Code escreve como reproduzir aquele estilo
(cores, fontes, espaços, componentes, movimento) sem copiar. Num site, o coletor abre a página (sem
IA, só internet). Num programa que ele mandou (APK, .exe, AppImage, app Electron), o Claude Code lê o
arquivo sem rodar, com o REA e os descompiladores do lab (Ghidra, JADX). Depois, qualquer projeto
pode seguir a receita.

| Ação | Params | O que faz |
|---|---|---|
| `receita.estudar` | `url` (o site) OU `arquivo` (o caminho do programa, como chegou a você: `/opt/data/...`), `imagens?` (até 6 prints que o dono mandou, os caminhos), `nome?` (sem ele, vem do site ou do arquivo: linear.app vira `linear-app`), `foco?` (o que olhar com mais atenção: "o menu", "as animações do topo"), `refazer?`, `conta?`, `modelo?`, `esforco?` | Coleta o site (de 30 s a 2 min) ou copia o programa, e põe o Claude Code para escrever a receita (até 45 min). Responde 202; o pedido termina quando o trabalho entra na fila, e o celular avisa quando a receita fica pronta |
| `receita.lista` | — | Cada receita: `estado` (`pronta`, `estudando`, `falhou`, `parou`), `de` (`site` ou `programa`), `titulo`, `origem`, `resumo`, `tags`, `paleta`, `fontes`, `trabalho` e `erro` |
| `receita.ver` | `nome` | A receita inteira (`texto` = o RECEITA.md, `design` = o DESIGN.md) e os prints |
| `receita.procurar` | `texto` (palavras do estilo: "escuro minimalista", "serifa") | As receitas que combinam, com um trecho |
| `receita.apagar` | `nome` | Apaga a receita, sem volta (pede o celular); o estudo no lab fica |

- "Gostei do estilo de X": `receita.estudar` com a `url`. Responda que começou e quanto leva; não
  espere: o celular avisa.
- Um programa ("estuda o estilo desse app" com um arquivo, ou um arquivo que ele mandou antes):
  `receita.estudar` com `arquivo` (o caminho que veio na mensagem) e, se ele mandou prints do programa
  junto ou logo antes, `imagens` com os caminhos deles. Sem prints, a receita sai só dos recursos do
  programa: sugira que ele mande uns prints da tela, que melhoram muito o resultado. Estudar programa
  de outra pessoa pode ser proibido pela licença dele; se parecer o caso, lembre o dono numa linha. Erro 409 "já existe": pergunte se ele quer refazer (`refazer: true`) ou
  usar a que já existe. Erro 400 de endereço: peça o endereço certo (o coletor só abre sites da
  internet, nunca da rede de casa).
- "Faz o projeto Y no estilo de X" ou "com aquela receita": ache a receita (`receita.procurar` ou
  `receita.lista`) e mande `claude.tarefa` com `receitas: ["<nome>"]`. O Claude Code recebe a receita
  dentro do projeto e segue o estilo. Se não houver receita de X, ofereça estudar antes.
- "Que receitas eu tenho?", "tem alguma escura?": `receita.lista` ou `receita.procurar`, e responda
  com o título e o resumo de cada uma, em poucas linhas.
- Uma receita estudando que parou ou falhou: o estudo ficou em `/srv/lab/projetos/receita-<nome>`;
  `claude.tarefa` com `continuar` (o `trabalho` da receita) e o pedido "termine a receita" retoma.

## Perguntas do Claude Code

Quando ele precisa de uma decisão do dono, faz uma pergunta e fica parado esperando. O celular do
dono é avisado na hora (com botões, se houver opções), e a ronda te acorda para você repassar.
- Ronda com `Claude Code pergunta <id> (...): esperando o dono`: busque a pergunta em
  `claude.perguntas` e mande ao dono, curta: a pergunta, as opções (se houver), o porquê em uma
  frase e o projeto. Diga que, sem resposta em 10 min, você decide.
- Quando o dono responder no chat (pode ser uma palavra, "a segunda", "tanto faz"), confira em
  `claude.perguntas` qual está aberta e mande `claude.responder` com `quem: "dono"` e a resposta dele
  escrita por extenso (troque "a segunda" pelo texto da opção). Se houver mais de uma aberta e não
  der para saber qual, pergunte qual.
- Ronda com `... o dono não respondeu em 10 min`: decida você, pelo que conhece do dono e do
  projeto, com o caminho mais simples e reversível. Mande `claude.responder` com `quem: "atena"` e
  conte ao dono, em uma linha, o que decidiu e por quê.
- Erro 409 "já foi encerrada": o dono respondeu pelo botão do celular ou o trabalho terminou. Siga.

## Você mesma no terminal

`/srv/lab/projetos` está montado no seu container, com o mesmo caminho que o Claude Code usa. Ali
você lê, edita, cria arquivos, roda `npm`, `node`, `python3`, `git` e testes direto no terminal, sem
passar pelo executor. Fora dessa pasta (e do seu espaço `/opt/data`), nada do servidor está montado.

Quando fazer você mesma, e quando mandar ao Claude Code:
- Você: "o que tem nesse projeto?", "roda os testes", "por que deu erro?", trocar um texto, uma cor,
  uma porta, uma configuração, consertar um bug pequeno e claro, conferir um app depois de publicado.
- Claude Code: projeto novo, várias telas ou funções, refatoração, visual caprichado, qualquer coisa
  que leve mais de uns 15 minutos ou muitos arquivos. Ele trabalha sozinho e não gasta a sua API.

Como trabalhar:
1. Antes de mexer, veja em `app.lista` se o projeto tem algo `em_andamento`. Se o Claude Code estiver
   trabalhando nele, não mexa: espere ele terminar ou mande pelo `claude.tarefa` com `continuar`.
2. `cd /srv/lab/projetos/<projeto>` e `git status`. Mudanças que não são suas e não estão no commit:
   não apague nem sobrescreva; pergunte.
3. Edite, rode os testes do projeto (README, `package.json`, `pytest`) e confira o resultado.
4. Faça commit: `git add -A && git commit -m "Atena: <o que mudou>"`. É o seu desfazer: `git revert`
   volta um commit sem apagar histórico. `git reset --hard`, `rm` de arquivos e `git push` pedem o ok
   do dono.
5. App publicado: a mudança só vai para o ar com `app.publicar`.

Cuidados:
- Comandos com tempo-limite de 3 min. Instalação ou build demorado: deixe para o Claude Code.
- Não deixe servidor rodando em segundo plano (`npm run dev`, `python -m http.server`): para ver o
  app no ar, publique e use `app.comando`.
- `.venv` e `node_modules` criados pelo Claude Code são do servidor e podem não funcionar no seu
  container. Se precisar, crie os seus com outro nome (ex.: `.venv-atena`) e ponha no `.gitignore`.
- Projeto novo: deixe o Claude Code criar (ele segue as regras de publicação do lab). Você pode criar
  uma pasta para rascunho rápido, mas avise o dono que não está pronta para publicar.

## Apps do lab: publicar, reiniciar, parar, cancelar, apagar

| Ação | Params | O que faz |
|---|---|---|
| `app.lista` | — | Cada projeto do lab: `app` (estado no Docker ou "não publicado"), `endereco`, `fora_de_casa`, `codigo` (a pasta existe?), `dados_guardados`, `em_andamento` (id do que está rodando); e a `lixeira` (com a data em que some de vez) |
| `app.publicar` | `projeto`, `porta?` (8000 a 8999; sem ela, a primeira livre) | Constrói pelo Dockerfile do projeto e põe no ar na zona lab |
| `app.reiniciar` | `projeto` | Reinicia o app. Se estava parado, sobe de novo com a imagem que já existe (sem reconstruir) |
| `app.parar` | `projeto` | Tira do ar (dados e imagem ficam) |
| `app.cancelar` | `projeto` | Para tudo o que está EM ANDAMENTO no projeto: trabalho do Claude Code, construção de uma publicação, coleta de uma receita (`receita-<nome>`) e pedidos esperando o celular |
| `app.apagar` | `projeto`, `partes` (lista com `docker`, `dados`, `codigo`) | Apaga partes do projeto |
| `app.restaurar` | `projeto` | Traz da lixeira o código de um projeto apagado |
| `app.comando` | `projeto`, `comando` (texto, roda com `sh -c`; ou lista `["ls", "/data"]`), `segundos?` (1 a 120, padrão 30) | Roda um comando dentro do app no ar (como o usuário do app): ver arquivos em `/data`, consultar o banco, testar uma rota com `wget -qO- localhost:$PORT/...`. Devolve `codigo` e `saida` |

`app.comando` é para olhar e conferir. Ele roda dentro do container (disco só de leitura, menos
`/data` e `/tmp`): mudanças de código vão no projeto, não no container. Apagar dados em `/data` pelo
comando é destrutivo: só com o ok do dono. Erro 504: passou de `segundos`; o comando pode seguir
rodando dentro do app (`app.reiniciar` zera).

O que cada parte de `app.apagar` faz:
- `docker`: tira do ar e apaga o container e a imagem. Os dados (volume) ficam.
- `dados`: apaga o volume com os dados do app (banco, uploads). NÃO TEM VOLTA. Leva `docker` junto.
- `codigo`: move a pasta `/srv/lab/projetos/<projeto>` para a lixeira. Por 30 dias, `app.restaurar`
  traz de volta; depois, some de vez.

Qual usar, conforme o que o dono disser:
- "sobe", "publica", "deixa no ar": `app.publicar`. Erro 409 "ainda não tem Dockerfile": mande antes
  um `claude.tarefa` com `continuar` (o id do último trabalho do projeto), `publicar: true` e o pedido
  "Deixe o projeto pronto para publicar, seguindo as regras do lab (Dockerfile, PORT e DATA_DIR)".
  Erro 409 "ainda está trabalhando": espere o trabalho terminar ou use `claude.tarefa` com
  `publicar: true`. Erro 409 "já há uma publicação ... em andamento": a anterior ainda está
  construindo; espere o celular avisar (Feito ou Falhou) e publique de novo só se ainda precisar.
- Mudança pequena e clara num app que já existe (um texto, uma cor, um bug óbvio): faça você no lab,
  faça commit e, se o app estiver no ar, `app.publicar`.
- "muda", "edita", "corrige", "adiciona X" maior num app que já existe: `claude.tarefa` no mesmo
  projeto, com `continuar` (o último trabalho do projeto, se houver) e `publicar: true` se o app
  estiver no ar (veja `app.lista`). Assim a versão nova vai para o ar sozinha quando o Claude Code
  terminar.
- Mudar só a porta: `app.publicar` com a `porta` nova.
- "reinicia", "religa": `app.reiniciar`, direto.
- "para o app", "tira do ar" (sem apagar): `app.parar`, direto.
- "cancela", "para o que está fazendo", "desiste": `app.cancelar`, direto. O pedido do dono já é o
  ok; não pergunte de novo. Por conta própria, nunca.
- "apaga do Docker", "remove o app": `app.apagar` com `["docker"]`.
- "apaga o código": `["codigo"]`. "Apaga tudo", "apaga o projeto inteiro": `["docker", "dados", "codigo"]`.
  "Zera os dados": `["dados"]` e depois `app.publicar`.
- Se não der para saber se ele quer perder os dados, deixe `dados` de fora e diga, na resposta, que
  os dados ficaram guardados e como apagar.
- Erro 409 "há algo em andamento": pergunte se é para cancelar (`app.cancelar`) e apagar depois.
- "Desfaz" uma mudança do Claude Code no código: mande `claude.tarefa` com `continuar` pedindo para
  voltar o commit (o lab usa git; cada trabalho lista os commits).

`app.publicar` e `app.apagar` costumam pedir Aprovar no celular (`/acoes` mostra "[precisa de
aprovação no celular]"). Nesse caso a notificação lista o que vai acontecer (no `app.apagar`,
exatamente o que sai e o que fica) e o toque em Aprovar é o
ok do dono: não peça outro ok no chat, avise que está no celular e PARE. Quando ele aprovar, o
executor constrói (pode levar alguns minutos) e o celular recebe "Feito" com o endereço, ou "Falhou"
com o fim do registro. Se o dono contar que falhou, veja o erro com `GET /pedido/<id>` e mande o
Claude Code consertar (`claude.tarefa` com `continuar`, o erro no pedido e `publicar: true`).
Sem a marca, `app.publicar` responde 202 e segue sozinho (acompanhe com `GET /pedido/<id>?esperar=170`),
e `app.apagar` roda na hora: com `dados`, peça o ok no chat antes.

O app publicado vira a stack `lab-<projeto>`: `servico.logs` e `status.servicos` funcionam com ela.
Ele fica em `endereco` (rede de casa) e, se o servidor tiver Tailscale, também em `fora_de_casa`
(de qualquer lugar, com o app do Tailscale ligado no aparelho). Sempre dê ao dono os endereços que
vierem (os dois, se houver `fora_de_casa`), copiados do resultado ou de `app.lista`. Parar ou apagar o app desliga o link de fora de casa; reiniciar religa.

## Ronda

A ronda (habilidade servidor-atena) também lista o que é do Claude Code:
- A última linha pode ser `Claude Code: último trabalho terminado = <id> (...)`. Ela aparece numa
  ronda só, a do fim do trabalho: busque `GET /pedido/<id>` e mande ao dono o resumo em poucas
  linhas, do seu jeito: o que ele fez (campo `resumo`), onde está (`/srv/lab/projetos/<projeto>`), quantos
  commits e o que ficou pendente. Se o estado não for `concluido`, diga o que houve (limite de uso:
  veja "Continuar e trocar"). Se o pedido tiver `publicacao`, a versão nova está sendo publicada ou
  esperando o Aprovar no celular (diga isso); se tiver `publicacao_erro`, ela não foi publicada:
  diga o motivo. Não investigue o servidor por causa dessa linha.
- Linhas `Claude Code pergunta ...`: siga "Perguntas do Claude Code".
- Se a única mudança foi uma linha do Claude Code que SUMIU (o trabalho que você já resumiu na ronda
  anterior, ou uma pergunta respondida), não há nada a dizer: responda exatamente `[SILENT]`.
