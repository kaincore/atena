# Atena

Modelo público de um servidor caseiro (Ubuntu 26.04, Docker em zonas isoladas, um executor com lista fechada de ações, a assistente Atena, o lab do Claude Code e o painel). Português do Brasil em código, comentários, mensagens e commits; a documentação anda em pt e en juntas.

As regras de trabalho estão em [CONTRIBUTING.md](CONTRIBUTING.md). Leia a seção certa antes de:
- **commitar** (fatias, mensagem, autoria);
- **mudar o executor, o painel ou o instalador** (as regras de cada um);
- **preparar uma versão** (o `CHANGELOG.md` e a linha Testado:).

Em qualquer tarefa:
- **Só valores de exemplo** entram no repositório, os do `atena.conf.example`; os de um servidor de verdade ficam no `/etc/atena/atena.conf` dele.
- **Antes de cada push:** `tools/ci-local.sh` e `tools/verificar-vazamentos.sh --historico`, os dois passando.
