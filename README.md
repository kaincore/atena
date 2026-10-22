<h1 align="center">
  <img src="docs/assets/banner.svg" width="100%" alt="ATENA: logotipo em néon entre colunas gregas, com as mãos da Criação de Adão em arte ASCII quase se tocando">
</h1>

<p align="center">
  <img alt="Ubuntu 26.04" src="https://img.shields.io/badge/ubuntu-26.04-ff2a6d?style=for-the-badge&labelColor=0b0618&logo=ubuntu&logoColor=ff2a6d">
  <img alt="Docker em zonas" src="https://img.shields.io/badge/docker-6%20zonas-05d9e8?style=for-the-badge&labelColor=0b0618&logo=docker&logoColor=05d9e8">
  <img alt="Atena no Hermes Agent" src="https://img.shields.io/badge/atena-hermes%20agent-d300c5?style=for-the-badge&labelColor=0b0618">
  <img alt="Lab com Claude Code" src="https://img.shields.io/badge/lab-claude%20code-ff2a6d?style=for-the-badge&labelColor=0b0618">
  <img alt="Painel no celular" src="https://img.shields.io/badge/painel-pwa-f9f002?style=for-the-badge&labelColor=0b0618">
  <a href="https://github.com/kaincore/atena/actions/workflows/verificar.yml"><img alt="Verificação" src="https://img.shields.io/github/actions/workflow/status/kaincore/atena/verificar.yml?branch=main&style=for-the-badge&labelColor=0b0618&color=05d9e8&label=verifica%C3%A7%C3%A3o"></a>
  <a href="LICENSE"><img alt="Licença MIT" src="https://img.shields.io/badge/licen%C3%A7a-MIT-f9f002?style=for-the-badge&labelColor=0b0618"></a>
</p>

<p align="center">
  <b>Um servidor caseiro pronto para usar, organizado em zonas isoladas.</b><br>
  Ubuntu + Docker, com firewall para containers, limites de CPU e RAM por zona, IA local na GPU,
  um gateway de LLM com tetos de gasto, uma assistente pelo Telegram que cuida de tudo isso,
  um lab onde o Claude Code programa para você e um painel no celular para ver e mandar no servidor.
</p>

<p align="center">
  <a href="README.en.md">English</a> ·
  <a href="docs/pt/arquitetura.md">Arquitetura</a> ·
  <a href="docs/pt/seguranca.md">Segurança</a> ·
  <a href="docs/pt/operacao.md">Operação</a> ·
  <a href="docs/pt/licoes.md">Lições</a>
</p>

```text
atena@servidor:~$ sudo ./install.sh --hermes --lab --painel
 [ OK ] zonas ........ prod · core · apps · ai · agents · lab
 [ OK ] firewall ..... nenhum container alcança a sua rede de casa
 [ OK ] ia local ..... ollama · whisper · litellm com teto de gasto
 [ OK ] executor ..... lista fechada de ações, aprovação no celular
 [ OK ] atena ........ online no telegram
 [ OK ] lab .......... o claude code programa para você
 [ OK ] painel ....... o servidor no celular, só pelo tailscale
atena@servidor:~$ █
```

## ▌01 // O que vem pronto

- **Seis zonas** separadas por nível de confiança, cada uma com rede, pasta de dados e limite de CPU/RAM próprios.
- **Firewall para containers.** Nenhum container alcança a sua rede de casa nem os seus aparelhos no Tailscale. De fora, só a rede de casa chega aos serviços. O ufw sozinho não faz isso, porque não enxerga as portas do Docker.
- **Limites de recursos.** Os agentes de IA nunca deixam os sistemas de clientes lentos: a zona `prod` tem prioridade e memória garantida.
- **IA local:** Ollama (modelos de linguagem), Whisper (transcrição de voz) e Kokoro (respostas em voz) na GPU, inclusive em placas antigas como a GTX 1060.
- **LiteLLM** como porta única para Claude (Haiku, Sonnet, Opus) e para os modelos locais, com teto de gasto por modelo e por chave, renovado todo dia 1º.
- **Painéis:** Dockge (gerenciar as stacks), Beszel (monitoramento, inclusive da GPU) e Open WebUI (chat no navegador).
- **A Atena** (opcional): assistente pessoal pelo Telegram, feita com o [Hermes Agent](https://github.com/NousResearch/hermes-agent). Vigia o servidor (até a temperatura), responde sobre ele, guarda as suas notas, usa o Arca, edita as stacks de apps com foto e desfazer e age só por uma lista fechada de ações, pedindo o seu ok para o que é destrutivo.
- **O lab** (opcional): a Atena manda trabalhos de programação ao Claude Code, que trabalha sozinho num sandbox, pergunta pelo celular quando precisa e deixa o app pronto para ela publicar na rede de casa.
- **O painel** (opcional): o servidor no navegador e no celular, instalável como app. Mostra o estado, os serviços, os sensores, os processos, a rede, o registro do systemd, o gasto de IA e os apps do lab; reinicia serviços e liga ou desliga o PC da rede de casa; manda trabalhos ao Claude Code e publica, apaga e restaura os apps do lab; agenda tarefas (ligar o PC às 19h, reiniciar um serviço de madrugada), edita as stacks de apps e mostra os arquivos; aprova ou recusa o que a Atena e o Claude Code pedem e mostra tudo o que o executor fez. Só pelo Tailscale, com senha, num container sem rede nenhuma.
- **Executor de ações** com aprovação no celular: o único caminho dos agentes até o servidor, sem shell, com um token por cliente.
- **Avisos no celular** (ntfy): serviço que falhou, container parado e pedidos de aprovação com botões.
- **Instalador** que monta tudo numa máquina nova e pode rodar de novo sem estragar o que já existe.

## ▌02 // Mapa das zonas

<p align="center"><img src="docs/assets/zonas.svg" width="100%" alt="Mapa das zonas: a internet não entra; a rede de casa e o Tailscale chegam ao servidor Atena, desenhado como um templo grego. Dentro dele ficam as zonas prod, core, apps, agents, ai e lab, e o executor no host. Ligações permitidas: agents para core (svc-ntfy), apps e agents para ai (svc-llm), agents e o painel (na core) para o executor (socket) e agents para lab (workers)."></p>

<details>
<summary>Mapa em texto</summary>

```text
   INTERNET  ×  ── nada exposto, nada entra ──

   REDE DE CASA ──────────┐              ┌────────── TAILSCALE
   qualquer aparelho      │              │        fora de casa
                          v              v
 ╔═══════════════════════ SERVIDOR ATENA ════════════════════════╗
 ║                                                               ║
 ║  ┌─ prod ──────────┐  ┌─ core ──────────┐  ┌─ apps ────────┐  ║
 ║  │ clientes        │  │ dockge · beszel │  │ arca          │  ║
 ║  │ prioridade máx. │  │ ntfy · painel   │  │ open webui    │  ║
 ║  └─────────────────┘  └──┬─────^────────┘  └───────┬───────┘  ║
 ║ ┌────────────────────────┘     │ svc-ntfy          │ svc-llm  ║
 ║ │┌─ agents ────────────────────┴───┐       ┌───────v───────┐  ║
 ║ ││ atena (hermes) · agentes        ├──────>│ ai            │  ║
 ║ │└──┬──────────────────────┬───────┘svc-llm│ ollama        │  ║
 ║ │   │ socket               │ workers       │ whisper       │  ║
 ║ │┌──v──────────────┐  ┌────v────────────┐  │ litellm       │  ║
 ║ └> EXECUTOR · host │  │ lab             │  └───────────────┘  ║
 ║  │ lista fechada   │  │ claude code     │                     ║
 ║  └─────────────────┘  └─────────────────┘                     ║
 ╚═══════════════════════════════════════════════════════════════╝
```

</details>

Zonas diferentes não se enxergam. As ligações do desenho são as únicas permitidas, e cada uma é feita de propósito; os workers dos agentes também alcançam a zona `apps`, e o painel não tem rede: fala com o executor por socket e recebe as visitas pelo Tailscale (veja [arquitetura](docs/pt/arquitetura.md)).

| Zona | Para quê | Limite |
|---|---|---|
| `prod` | Sistemas de clientes | Prioridade máxima, 4 GB de RAM garantidos |
| `core` | Infra da plataforma | Prioridade alta |
| `apps` | Apps pessoais | Até 4 GB |
| `ai` | IA local e gateway de LLM | Até 6 GB |
| `agents` | Agentes de IA | Até 6 threads e 6 GB, prioridade baixa |
| `lab` | Projetos do Claude Code e testes | Até 6 threads e 4 GB (6 GB com o lab), prioridade baixa |

Os limites foram pensados para 16 GB de RAM. Ajuste em `host/systemd/atena-*.slice`.

## ▌03 // Requisitos

- **Ubuntu 26.04** (servidor, direto no hardware) com **IP fixo** na rede de casa.
- Um usuário administrador com **sudo** e **chave SSH** configurada.
- Opcional: **GPU NVIDIA**. A série 580 do driver é a última que suporta placas Pascal (GTX 10xx).
- Opcional: assinatura do **Claude** (Pro ou Max), para o lab.
- Opcional: conta no **Tailscale** para acessar de fora de casa (obrigatória para o painel).

## ▌04 // Instalação

```bash
git clone https://github.com/kaincore/atena.git
cd atena
cp atena.conf.example atena.conf
nano atena.conf          # interface de rede, IP, faixa da rede, roteador, usuário, GPU
sudo ./install.sh        # --ssh: SSH só com chave · --hermes: a Atena · --lab: o lab · --painel: o painel
```

Depois:

1. **Dockge** em `http://<ip-do-servidor>:5001` e **Beszel** em `:8090`. **Crie as contas logo**: a primeira pessoa que abrir vira administradora.
2. No Beszel, adicione o sistema com o host `/beszel_socket/beszel.sock`.
3. Para usar o Claude, rode `atena-chave-anthropic` e cole a chave da API (ela não aparece na tela).
4. Suba as outras stacks pelo Dockge.
5. Avisos no celular: instale o app ntfy e crie o seu usuário com `sudo atena-ntfy-celular <nome>`.
6. Com `--hermes`: `sudo atena-hermes-chave` (chave da Atena no LiteLLM, com teto) e `sudo atena-telegram` (o bot). Detalhes em [operação](docs/pt/operacao.md#atena-hermes).
7. Com `--lab`: `sudo atena-claude-conta entrar <conta>` para cada conta de `ATENA_CLAUDE_CONTAS`. Detalhes em [operação](docs/pt/operacao.md#lab-claude-code).
8. Com `--painel`: `sudo atena-painel-senha` e, com o Tailscale ligado, abra o endereço que o instalador mostrar (`https://<servidor>.<tailnet>.ts.net:3100`). No celular: menu ⋮ do Chrome → Instalar app. Detalhes em [operação](docs/pt/operacao.md#painel).

## ▌05 // Serviços incluídos

| Serviço | Zona | Porta | Observação |
|---|---|---|---|
| Dockge 1.5.0 | core | 5001 | Gerencia as stacks. Tem acesso total ao Docker: use senha forte |
| Beszel 0.21.0 | core | 8090 | Monitoramento. O agente não abre porta de rede |
| ntfy 2.28.0 | core | 2586 | Avisos e aprovações no celular. Só com usuário |
| Ollama 0.40.5 | ai | só no servidor | Usa o CUDA 12 (o CUDA 13 não suporta GPUs Pascal) |
| Whisper (Speaches 0.8.3) | ai | só no servidor | API compatível com a OpenAI, int8 na GPU |
| Voz (Speaches 0.8.3 + Kokoro) | ai | só no servidor | Respostas em voz da Atena (`ATENA_VOZ=sim`), fp32 na GPU |
| LiteLLM 1.101.6 | ai | 4000 | Exige chave. Tetos de gasto por modelo e por chave |
| Open WebUI 0.11.4 | apps | 3000 | Fala só com o LiteLLM |
| Arca | apps | 3002 | Envio de arquivos pelo navegador, sem senha |
| Hermes Agent 0.22.2 | agents | nenhuma | A Atena (com `--hermes`). Conversa pelo Telegram |
| Painel 0.7.0 | core | 3100, só pelo Tailscale | O painel (com `--painel`). Sem rede, sem root, sem pacotes do npm, com senha |
| Claude Code 2.1.302 | lab | apps em 8000-8999 | O lab (com `--lab`). Roda em sandbox, sem sudo e sem Docker; usa a sua assinatura do Claude |

As versões são fixas de propósito. Antes de atualizar, leia os avisos de segurança e as notas da versão.

## ▌06 // Documentação

- [Arquitetura](docs/pt/arquitetura.md): zonas, redes, limites, o executor, a Atena, o lab e o painel
- [Segurança](docs/pt/seguranca.md): o que está protegido, como foi testado e o que não está
- [Operação](docs/pt/operacao.md): stacks, clientes, avisos no celular, a Atena, o lab, o painel e as atualizações
- [Lições aprendidas](docs/pt/licoes.md): armadilhas encontradas montando o primeiro servidor

## ▌07 // Estrutura do repositório

```text
atena/
├── install.sh, install/   instalador (uma etapa por arquivo)
├── host/                  arquivos do sistema: Docker, systemd, firewall, SSH, executor, avisos, lab
│   ├── lab/               ponte, sandbox e guarda de escopo do Claude Code do lab
│   └── windows/           script e passo a passo do PC da rede de casa (opcional)
├── stacks/<zona>/<nome>/  composes das stacks
│   └── core/painel/app/   o painel: servidor, interface e testes
├── hermes/                a Atena: personalidade, habilidades, ronda e configuração
├── tests/                 testes do executor, da ronda e do lab
├── tools/                 CI local, verificador de vazamentos e trava de commit
└── docs/                  documentação em português e inglês
```

## ▌08 // Contribuindo

As regras de trabalho (commits, testes, o que nunca entra no repositório, como mudar o executor e o painel) estão no [CONTRIBUTING.md](CONTRIBUTING.md). Antes do primeiro commit, ative a trava que impede commitar segredos:

```bash
git config core.hooksPath tools/hooks
```

## ▌09 // Licença

[MIT](LICENSE)

<p align="center"><sub>░▒▓ feito em casa · zonas isoladas · nada exposto ▓▒░</sub><br>
<sub>Banner: as mãos de <i>A Criação de Adão</i> (Michelangelo, c. 1512, domínio público) em arte ASCII.</sub></p>
