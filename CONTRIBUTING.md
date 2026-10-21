# Contribuindo

Como mudar este repositório sem quebrar um servidor de verdade nem publicar o que é de alguém. Vale para pessoas e para assistentes de código (o [CLAUDE.md](CLAUDE.md) aponta para cá).

Português do Brasil em código, comentários, mensagens de erro e commits. A documentação anda junta nas duas línguas: mudou `docs/pt`, `README.md` ou este arquivo, mude também `docs/en`, `README.en.md` ou o `CONTRIBUTING.en.md`.

## Antes do primeiro commit

```bash
git config core.hooksPath tools/hooks
```

A trava (`tools/hooks/pre-commit`) roda o `tools/verificar-vazamentos.sh` em cada commit. Ele procura segredos genéricos (chaves de API, tokens, chaves privadas) e, se você tiver um servidor, os seus dados: um padrão (regex do `grep -E`) por linha em `~/.config/atena/padroes-privados.txt`, fora do repositório. Ponha lá o IP e a faixa da sua rede, o nome da tailnet, os MACs, os nomes das máquinas, o seu nome, os seus e-mails e qualquer nome de empresa.

## Só valores de exemplo

O repositório é um modelo: tudo o que é de um servidor de verdade fica no `/etc/atena/atena.conf` dele, e aqui só entram os valores do `atena.conf.example`.
- Rede de casa: os do exemplo (`192.168.0.10`, `192.168.0.0/24`); Tailscale: `<servidor>.<tailnet>.ts.net`.
- Nomes: `atena` (o usuário admin), `principal` ou `pessoal` e `trabalho` (as contas do Claude Code), `PC` (o da rede de casa).
- Ficam fora, sempre: `.env`, dados de `/srv`, chaves e tokens, `sudoers`, o estado do Tailscale, capturas de tela com nomes reais.

## Commits

- **Fatias pequenas e lógicas**, cada uma passando nos testes sozinha: uma refatoração que só move código vai num commit, e a mudança de comportamento em outro.
- **Mensagem:** `tipo(área): o que muda`, curta, em português, com o corpo explicando o porquê e como foi testado. Tipos: `feat`, `fix`, `refactor`, `docs`, `ci`, `tools`; áreas: `executor`, `painel`, `lab`, `hermes`, `install`.
- **O autor é quem assina:** as mensagens levam só o texto do commit, sem as linhas que algumas ferramentas acrescentam (`Co-Authored-By` de assistente, "Generated with").

## Testes e CI

Antes de cada push:

```bash
tools/ci-local.sh                         # os mesmos jobs do CI, em containers (--arvore: os arquivos como estão)
tools/verificar-vazamentos.sh --historico # também todo o histórico
```

Os jobs estão em `.github/workflows/verificar.yml`; os testes de Python ficam em `tests/<área>/teste_*.py` (cada um roda sozinho: `cd tests/executor && python3 teste_nucleo.py`), e os do painel com `npm test` em `stacks/core/painel/app`. Uma falha nos testes de Python vira anotação do GitHub, que dá para ler pela API sem abrir o log.

## Executor (`host/executor/atena_executor`)

- **Um módulo por assunto, de baixo para cima:** um módulo só importa dos que vêm antes dele (o mapa está no `__init__.py`). Quando um de baixo precisa de um de cima, o import fica dentro da função, com o motivo ao lado.
- **Lista fechada:** cada ação entra em `acoes.py` (função, ajuda e, se ela muda algo, o `preparar` que valida e escreve o texto da aprovação). Os parâmetros são conferidos contra o que existe de verdade, e todo comando é uma lista de argumentos para o `rodar`, nunca um texto para o shell.
- **O erro diz o que fazer:** `Erro(status, mensagem)` vira a resposta HTTP, e a mensagem dá o próximo passo ("rode sudo atena-claude-conta entrar trabalho").
- **Ação nova:** um teste em `tests/executor` (ou `tests/lab`), a linha na habilidade da Atena (`hermes/skills/atena/*/SKILL.md`: o `teste_habilidade.py` confere que toda ação está lá) e, se o painel usa, a ação no `ACOES_PAINEL` de `install/85-painel.sh`.
- Só a biblioteca padrão do Python, mais o PyYAML; o ruff (regras no `ruff.toml`) confere nomes e imports.

## Painel (`stacks/core/painel`)

- **Sem pacote do npm:** o servidor é TypeScript que o Node 22 roda direto (só a sintaxe que ele apaga; o CI confere com `tsc --noEmit`), e a interface é JavaScript puro, sem build.
- **Uma tela por arquivo** em `app/public/telas`; o que todas usam fica no `comum.js`, e a casca (`app.js`) cuida da navegação. As telas chamam `atualizar`, `telaAtual` e `mostrarEntrada` pelo `comum.js`.
- **Tudo vem do próprio painel:** a CSP é `default-src 'self'`, e o container não tem rede. Estilo muda pelo CSSOM (`el.style.setProperty`), e os dados do servidor entram na tela como texto, pelo `h()`.
- **Arquivo novo na interface:** entra na lista `CASCA` do `sw.js`, e o `CACHE` sobe de versão (senão o celular continua com a casca velha).
- **O visual** segue o `DESIGN.md`, e o que o painel é e para quem está no `PRODUCT.md`. Confira a tela de verdade, no celular e no PC, nos temas claro e escuro.

## Instalador e scripts (`install/`, `host/sbin/`)

- Bash com `set -euo pipefail`, limpo no shellcheck.
- **Cada etapa roda de novo sem estragar nada:** confira antes de criar, e instale arquivos com `instalar_arquivo` (ele guarda uma cópia do que já existia). Mensagens com `ok`, `aviso` e `erro`.
- O que só você pode fazer (login, colar uma senha) sai no fim, como próximo passo.

## Versões

- Cada versão tem uma entrada no `CHANGELOG.md` (`## x.y.z (data)`) com uma linha **Testado:** que diz exatamente o que foi testado e onde, e o que ficou sem testar.
- O banner (`docs/assets/banner.svg` e `banner.en.svg`) mostra a versão.
- O painel tem versão própria: `app/package.json`, a imagem no `compose.yaml` e as tabelas dos dois READMEs.

## Num servidor de verdade

Mude primeiro o repositório, com teste; depois instale (`sudo ./install.sh` com as mesmas opções de antes atualiza o que mudou). Uma troca feita à mão num servidor leva backup e um jeito de desfazer, e a mesma mudança volta para o repositório, para o servidor continuar igual ao modelo.
