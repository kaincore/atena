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

Edite a seção "exceções" de `/usr/local/sbin/atena-docker-firewall` (por exemplo, para um container monitorar uma impressora da rede de casa) e aplique:

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
- **Virada do mês:** os tetos das chaves (`1mo`) renovam sozinhos no dia 1º às 00:00 UTC. Os tetos por modelo são zerados no mesmo horário pelo `atena-litellm-virada-mes.timer`.
- **Depois de editar o `config.yaml`:** `docker compose up -d --force-recreate litellm`.

## Atualizar versões

As imagens têm versão fixa. Para atualizar:

1. Leia as notas da versão e os **avisos de segurança** do projeto (no GitHub, aba Security).
2. Prefira versões publicadas há pelo menos duas semanas. Correção de segurança importante é a exceção.
3. Troque a versão no compose e rode `docker compose up -d`.
4. **GPUs Pascal (GTX 10xx):** depois de atualizar o Ollama ou o Whisper, confira nos logs se a GPU continua sendo usada (`library=CUDA compute=6.1` no Ollama).

O driver da NVIDIA atualiza junto com o sistema, sempre dentro da mesma série. **Não use `apt-mark hold`** (veja as [lições](licoes.md)).

## Rodar o instalador de novo

`sudo ./install.sh` pode rodar quantas vezes quiser:
- **Stacks que já existem** não são sobrescritas.
- **Arquivos do sistema diferentes do modelo** são substituídos, e uma cópia do anterior fica ao lado (`*.antes-atena-<data>`).
