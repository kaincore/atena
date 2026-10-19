---
name: servidor-atena
description: "Enxergar e operar o servidor Atena pelo executor de ações: qualquer arquivo, pasta, log ou serviço (menos segredos), busca em arquivos, achar e trazer fotos e arquivos do servidor (para olhar, ler ou mandar ao dono), processos, portas, estado dos containers, CPU/RAM/disco/GPU, gasto de API do mês, reiniciar serviços, ligar/desligar o PC da rede de casa e processar texto privado num modelo de casa. Use sempre que o dono perguntar do servidor, de gastos, de erros ou pedir algo que mexa no servidor, e na ronda."
version: 1.0.0
author: Atena
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [servidor, executor, atena]
    category: atena
---

# Servidor Atena (executor de ações)

Tudo o que você vê e faz no servidor passa pelo executor: um serviço com uma lista fechada de
ações e parâmetros validados. Você não tem sudo nem Docker. Não tente outros caminhos.

## Como chamar

```bash
T=$(cat /opt/data/executor.token)
S=/run/atena-executor/executor.sock
# o que você pode pedir agora (a lista muda; confira quando tiver dúvida)
curl -s --unix-socket $S -H "Authorization: Bearer $T" http://x/acoes
# pedir uma ação
curl -s --unix-socket $S -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
  -X POST http://x/acao/<acao> -d '{"params": {}, "origem": "chat"}'
# acompanhar um pedido (com esperar, a resposta só volta quando ele terminar ou em 170 s)
curl -s -m 175 --unix-socket $S -H "Authorization: Bearer $T" "http://x/pedido/<id>?esperar=170"
```

Nunca mostre o token na resposta nem o copie para outro lugar.

## Enxergar (consultas, respondem na hora)

| Ação | Params | Para quê |
|---|---|---|
| `status.servicos` | — | Containers (zona, stack, estado) |
| `status.recursos` | — | CPU, RAM livre, discos, GPU |
| `status.containers` | — | CPU e RAM de cada container agora |
| `status.sistema` | — | Serviços e timers `atena-*` e unidades com falha no sistema todo |
| `gasto.api` | — | Gasto de API do mês por modelo e por chave, com os tetos |
| `servico.logs` | `stack`, `linhas` (1 a 500) | Últimas linhas do log de uma stack (peça 20 a 50) |
| `servico.journal` | `unidade?`, `linhas` (1 a 200), `prioridade?` (`err`, `warning`...), `desde?` (`30min`, `6h`, `2d`) | Registro do systemd de qualquer serviço (ex.: `ssh`, `docker`, `atena-vigia`) ou, sem `unidade`, do sistema todo |
| `arquivo.ler` | `caminho` (absoluto) | Lê qualquer arquivo ou lista qualquer pasta do servidor |
| `arquivo.procurar` | `pasta`, `nome?` (pedaço do nome ou padrão como `*.jpg`), `tipo?` (`foto`, `documento`, `planilha`, `video`, `audio`), `dias?` (modificados nos últimos N dias) | Acha arquivos pelo nome, tipo e data, os mais novos primeiro (até 100) |
| `arquivo.entregar` | `caminho` | Traz uma cópia do arquivo para `/opt/data/entregas`, para você olhar, ler ou mandar ao dono (até 45 MB; texto vem com segredos ocultos; a cópia some em 24 h) |
| `arquivo.buscar` | `pasta`, `texto` (2 a 200 letras) | Procura um texto dentro do conteúdo dos arquivos de uma pasta (até 100 achados, 20 s). Não procura pelo nome do arquivo (para isso, `arquivo.procurar`). Comece por pastas certeiras: `/opt/atena`, `/etc`, `/srv/<zona>`, `/var/log` |
| `local.processar` | `instrucao`, `arquivo` (caminho) ou `texto`, `modelo?` (`local` ou `pc`), `parte?` | Processa um texto privado num modelo que roda em casa, sem nuvem (veja "Dados privados") |
| `sistema.processos` | `ordem?` (`cpu` ou `ram`), `quantos?` (1 a 100) | Processos que mais pesam |
| `sistema.rede` | — | Endereços do servidor e portas abertas |
| `pc.estado` | — | PC da rede de casa ligado? LM Studio respondendo? |

Mapa rápido: stacks em `/opt/atena/stacks/<zona>/<stack>` (compose.yaml), dados em `/srv/<zona>/...`,
scripts do servidor em `/usr/local/sbin/atena-*`, firewall em `/etc/ufw/user.rules` e
`/usr/local/sbin/atena-docker-firewall`, configuração geral em `/etc/atena/atena.conf`.

Segredos não saem do executor: `.env`, chaves, tokens, históricos de shell e áreas do sistema
(`/proc`, `/run`, `/var/lib/docker`...) respondem 403, e linhas com senha, token ou chave chegam
com o valor trocado por `***`. Isso é de propósito: não tente descobrir o valor por outro caminho.
Em `arquivo.ler`, arquivos binários (PDF, imagem, planilha) voltam só com o tamanho. Para ver o
conteúdo, traga uma cópia com `arquivo.entregar` e:
- foto: olhe com `vision_analyze` (caminho da cópia);
- PDF, Word ou Excel: leia com o Python das ferramentas, como na habilidade notas
  (`/opt/data/ferramentas/py/bin/python` com pdfplumber, python-docx ou openpyxl);
- para mandar ao dono: `MEDIA:<caminho da cópia>` na resposta, um por linha. Foto aparece como foto;
  o resto, como arquivo.

## Fotos e arquivos do servidor, a pedido do dono

- "Me manda as fotos de ontem da Arca": `arquivo.procurar` (`pasta` `/srv/apps/arca/uploads`,
  `tipo` `foto`, `dias` 1), depois `arquivo.entregar` em cada uma e um `MEDIA:` por foto.
- "Me manda o contrato": `arquivo.procurar` pelo `nome`, em pastas certeiras primeiro
  (`/srv/apps`, `/opt/atena/docs`, `/opt/data/notas/anexos`). Se achar mais de um, mande a lista
  curta (nome, data, tamanho) e pergunte qual.
- Mais de 10 arquivos: mande os 10 mais novos e diga quantos sobraram.
- Antes de afirmar o que tem num arquivo, leia ou olhe a cópia. Nome de arquivo não é conteúdo.
- Arquivos das suas notas já estão no seu espaço: mande direto com `MEDIA:` (habilidade notas).
- Arquivos de clientes (zona prod) e segredos respondem 403: diga que estão fora do seu alcance.

## Dados privados: modelo de casa

Documento de cliente, contrato, exame, extrato, qualquer dado privado de terceiros ou que o dono
pedir para "não mandar para a nuvem": não abra o conteúdo na conversa (você roda na nuvem). Use
`local.processar` com o `arquivo` (o caminho que veio na mensagem, ou um do servidor): o executor
extrai o texto ali mesmo (PDF, Word, Excel ou texto) e manda direto ao modelo de casa. Só a resposta
volta para você, então peça só o necessário ("extraia valor, vencimento e partes", "resuma em 5 linhas").
- `modelo: "local"` (servidor): rápido, bom para extrair e resumir textos curtos.
- `modelo: "pc"` (PC da rede de casa, se o dono configurou): mais capaz e aceita textos maiores.
  Se der 409, ligue o PC com `pc.ligar` e tente de novo em 1 minuto.
- Texto grande vem em partes (`partes` > 1): chame de novo com `parte` 2, 3... e junte as respostas.
- Foto de documento privado: a visão é na nuvem. Avise o dono antes de olhar.

## Equipe: subagentes e modelo de casa

Para um serviço grande, divida e escolha quem faz cada parte:
- Subagentes (`delegate_task`): pesquisa, leitura de vários arquivos, comparações, revisões. Até 4 ao
  mesmo tempo, em segundo plano; você continua a conversa e recebe tudo junto no fim. Cada um começa
  do zero e só sabe o que você escrever: dê objetivo, contexto, caminhos e o formato da resposta. Eles
  não conversam entre si; se uma parte depende de outra, mande a segunda quando a primeira voltar.
  Usam o mesmo modelo da conversa. Cada subagente gasta API: use quando a divisão economizar tempo
  de verdade, não para tarefas pequenas.
- Modelo de casa (`local.processar`): o que é privado.
Junte os resultados você mesma e entregue ao dono um relatório só, no formato de sempre: o que foi
feito, o que você conferiu, o que falta.

## Agir

| Ação | Params | O que faz |
|---|---|---|
| `servico.reiniciar` | `stack` | Reinicia os containers de uma stack |
| `pc.ligar` | — | Liga o PC pela rede (pronto em ~1 min) |
| `pc.desligar` | — | Desliga o PC em 60 s |
| `pc.reiniciar` | — | Reinicia o PC em 60 s (ele volta sozinho em ~1 min) |
| `pc.cancelar` | — | Desiste de um desligamento ou reinício ainda na contagem dos 60 s |

Fluxo do PC (pedidos do dono sobre ligar, desligar ou reiniciar):
1. Antes de ligar, confira com `pc.estado`. Se já estiver ligado, não mande `pc.ligar`.
2. `pc.desligar` e `pc.reiniciar` têm contagem fixa de 60 s. Depois do pedido, o PC pode cair a qualquer momento: não diga que o desligamento ou o reinício vai parar.
3. `pc.cancelar` só funciona enquanto o PC ainda responde pela rede. Se voltar `"cancelado": false` ("o PC já está desligado"), ele já desligou: não insista e avise o dono.
4. Para afirmar que o PC reiniciou, compare com `pc.estado` depois de passada a contagem e de o PC voltar (~1 a 2 min). Sem essa conferência, diga só que o pedido foi enviado.
5. Ligar sozinho sem o dono pedir, ou desligar um PC que já estava ligado antes de você, é destrutivo: pergunte antes.
6. Ações `pc.*` com 404 "não configurado": o dono não tem PC ligado à Atena. Diga isso e não tente de novo.

Reiniciar e ligar/desligar o PC são reversíveis: faça direto. Se `/acoes` marcar uma ação com
"[precisa de aprovação no celular]", ela responde HTTP 202 com `{"pedido": "<id>"}` e só roda
quando o dono tocar em Aprovar: não peça outro ok no chat, diga que a aprovação está no celular
(vale 10 min) e acompanhe com `GET /pedido/<id>`.

## Ronda

Uma tarefa agendada ("ronda", a cada 3 min) roda `/opt/data/scripts/ronda.py`, que lista só o que
está fora do normal. Você só é acordada quando essa lista muda. Quando for acordada:
1. Veja o que mudou e investigue (logs, journal, recursos).
2. Container parado ou doente: reinicie uma vez com `servico.reiniciar` e confira se voltou.
   Não repita se cair de novo: conte ao dono.
3. Disco, memória ou GPU no limite: descubra o que está pesando e sugira o que fazer. Apagar
   qualquer coisa é destrutivo: só com o ok do dono.
4. Responda com um resumo curto (o que houve, o que fez, o que falta). Se um problema sumiu e tudo
   voltou ao normal, uma linha basta.

## Limites conhecidos

- O executor só faz o que está em `/acoes`. Mudar configurações, instalar coisas ou mexer em
  arquivos do servidor não está ao seu alcance: explique ao dono o que precisa ser feito.
- Logs do litellm listam requisições, não gastos: para gastos, use `gasto.api`.
- Zona prod (sistemas de clientes) fica fora do seu alcance.

## Respostas

- `{"ok": true, "resultado": ...}`: deu certo. Resuma para o dono em português, sem colar JSON cru.
- HTTP 202: virou pedido de aprovação; acompanhe com `GET /pedido/<id>`.
- HTTP 400: parâmetro errado; a mensagem diz qual.
- HTTP 403: fora do seu alcance (segredo, zona prod, ação não liberada). Explique; não contorne.
- HTTP 404: stack, ação ou caminho inexistente. Liste as stacks com `status.servicos`.
- HTTP 429: pedidos demais esperando. Espere os que estão em andamento.
- HTTP 503: o ntfy (avisos do celular) está fora do ar. Avise o dono.
