# Segurança

## Princípios

- **Rede de casa confiável, o resto não.** Qualquer aparelho da rede de casa acessa os serviços. De fora, só pelo Tailscale. Da internet, nada.
- **Containers não alcançam a rede de casa.** Se um container for comprometido, ele não chega ao roteador, aos seus computadores nem aos aparelhos do Tailscale.
- **Zonas isoladas.** Um problema numa zona não alcança as outras.
- **Segredos fora do código.** Ficam em arquivos `.env` com permissão 600, gerados no servidor e nunca versionados.

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

## O que foi testado no servidor original

| Teste | Resultado |
|---|---|
| Container da zona `agents` tentando o roteador, a rede de casa, o Tailscale e o SSH do servidor | Bloqueado |
| O mesmo container tentando a internet e o DNS | Liberado |
| Uma máquina simulada fora da rede de casa (namespace de rede) tentando um container publicado em `0.0.0.0` | Bloqueado. Sem a regra, passou, o que prova que o teste detecta a falha |
| Zona diferente tentando alcançar outra | Isolado |
| Os mesmos testes depois de reiniciar o Docker e o servidor | Mesmo resultado |
| Login por senha e como root no SSH | Recusado |

## O que a Atena NÃO protege

- **O administrador e o Dockge têm acesso total.** O Dockge e o agente do Beszel usam o socket do Docker, que equivale a root. Quem entra no Dockge manda no servidor. Use senha forte.
- **Serviços sem senha ficam abertos para toda a rede de casa.** O Arca, por exemplo, não tem login: qualquer aparelho do Wi-Fi pode ver e apagar arquivos.
- **As zonas dividem o mesmo kernel.** Uma falha grave de escape de container atravessaria as zonas. Para isolamento forte, use máquinas virtuais.
- **IPv6 dentro dos containers** não é usado. Se você ativar IPv6 nas redes do Docker, revise o firewall, que hoje só tem regras de IPv4.
- **Outros encaminhamentos de tráfego** (máquinas virtuais, subnet router do Tailscale) são descartados pela última regra da `DOCKER-USER`. Se precisar deles, crie exceções.

## Antes de publicar algo

O repositório tem uma trava (`tools/hooks/pre-commit`) e uma verificação no GitHub (gitleaks). Mantenha a sua lista de dados pessoais em `~/.config/atena/padroes-privados.txt`, **fora** do repositório.
