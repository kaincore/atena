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

**Depois de desligar, o PC continua "ligado" na tabela de vizinhos por alguns minutos.**
O executor trata o SSH sem rota como "desligado", em vez de dar erro.

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
