# Contributing

How to change this repository without breaking a real server or publishing what belongs to someone. It applies to people and to coding assistants (the [CLAUDE.md](CLAUDE.md) points here).

Brazilian Portuguese in code, comments, error messages and commits. The documentation moves in both languages together: if you change `docs/pt`, `README.md` or `CONTRIBUTING.md`, change `docs/en`, `README.en.md` or this file too.

## Before your first commit

```bash
git config core.hooksPath tools/hooks
```

The guard (`tools/hooks/pre-commit`) runs `tools/verificar-vazamentos.sh` on every commit. It looks for generic secrets (API keys, tokens, private keys) and, if you have a server, your own data: one pattern (a `grep -E` regex) per line in `~/.config/atena/padroes-privados.txt`, outside the repository. Put your network's IP and range there, the tailnet name, the MACs, the machine names, your name, your e-mails and any company name.

## Example values only

The repository is a template: everything that belongs to a real server lives in its `/etc/atena/atena.conf`, and only the values from `atena.conf.example` go in here.
- Home network: the example ones (`192.168.0.10`, `192.168.0.0/24`); Tailscale: `<server>.<tailnet>.ts.net`.
- Names: `atena` (the admin user), `principal` or `pessoal` and `trabalho` (the Claude Code accounts), `PC` (the one on the home network).
- Always left out: `.env`, data from `/srv`, keys and tokens, `sudoers`, the Tailscale state, screenshots with real names.

## Commits

- **Small, logical slices**, each passing the tests on its own: a refactor that only moves code goes in one commit, and the behavior change in another.
- **Message:** `type(area): what changes`, short, in Portuguese, with the body explaining why and how it was tested. Types: `feat`, `fix`, `refactor`, `docs`, `ci`, `tools`; areas: `executor`, `painel`, `lab`, `hermes`, `install`.
- **The author is whoever signs:** messages carry only the commit text, without the lines some tools add (an assistant's `Co-Authored-By`, "Generated with").

## Tests and CI

Before every push:

```bash
tools/ci-local.sh                         # the same CI jobs, in containers (--arvore: the files as they are)
tools/verificar-vazamentos.sh --historico # the whole history too
```

The jobs are in `.github/workflows/verificar.yml`; the Python tests live in `tests/<area>/teste_*.py` (each runs on its own: `cd tests/executor && python3 teste_nucleo.py`), and the panel's with `npm test` in `stacks/core/painel/app`. A failure in the Python tests becomes a GitHub annotation, readable through the API without opening the log.

## Executor (`host/executor/atena_executor`)

- **One module per topic, bottom to top:** a module only imports from the ones before it (the map is in `__init__.py`). When a lower one needs a higher one, the import goes inside the function, with the reason next to it.
- **Closed list:** each action goes into `acoes.py` (function, help and, if it changes something, the `preparar` that validates and writes the approval text). Parameters are checked against what really exists, and every command is an argument list for `rodar`, never a string for the shell.
- **The error says what to do:** `Erro(status, message)` becomes the HTTP response, and the message gives the next step ("rode sudo atena-claude-conta entrar trabalho").
- **New action:** a test in `tests/executor` (or `tests/lab`), the line in Atena's skill (`hermes/skills/atena/*/SKILL.md`: `teste_habilidade.py` checks every action is there) and, if the panel uses it, the action in `ACOES_PAINEL` in `install/85-painel.sh`.
- Python's standard library only, plus PyYAML; ruff (rules in `ruff.toml`) checks names and imports.

## Panel (`stacks/core/painel`)

- **No npm packages:** the server is TypeScript that Node 22 runs directly (only the syntax it erases; CI checks it with `tsc --noEmit`), and the interface is plain JavaScript, with no build step.
- **One screen per file** in `app/public/telas`; what they all use lives in `comum.js`, and the shell (`app.js`) handles navigation. Screens call `atualizar`, `telaAtual` and `mostrarEntrada` through `comum.js`.
- **A screen that rereads itself gives focus back by key:** a row or card whose buttons repeat ("Ver", "Aprovar") carries the key of what it is (`item({ chave })` or `data-chave`, such as `pedido:<id>`). Without a key, focus only comes back when the button's text is unique on the screen; when in doubt, it does not come back.
- **Everything comes from the panel itself:** the CSP is `default-src 'self'`, and the container has no network. Style changes go through the CSSOM (`el.style.setProperty`), and server data reaches the screen as text, through `h()`.
- **The phone cache renews itself:** the panel server writes into `sw.js` the list of every interface file and a version that is a digest of them. A new or changed file already installs the new shell; there is no list or number to update by hand.
- **The look** follows `DESIGN.md`, and what the panel is and who it is for is in `PRODUCT.md`. Check the real screen, on the phone and on the PC, in the light and dark themes.

## Installer and scripts (`install/`, `host/sbin/`)

- Bash with `set -euo pipefail`, clean under shellcheck.
- **Every step runs again without breaking anything:** check before creating, and install files with `instalar_arquivo` (it keeps a copy of what was there). Messages through `ok`, `aviso` and `erro`.
- What only you can do (a login, pasting a password) comes at the end, as the next step.
- **A new file that goes to the server** also goes into `install/estado.py`, the desired state that `./aplicar --conferir` compares with the server. `tests/install/teste_estado.py` fails if it's left out.

## Releases

- Every release has an entry in `CHANGELOG.md` (`## x.y.z (date)`) with a **Testado:** line that says exactly what was tested and where, and what was left untested.
- The banner (`docs/assets/banner.svg` and `banner.en.svg`) shows the version.
- The panel has its own version: `app/package.json`, the image in `compose.yaml` and the tables in both READMEs.

## On a real server

Change the repository first, with a test; then install (`sudo ./install.sh` with the same options as before updates what changed). A change made by hand on a server comes with a backup and a way to undo it, and the same change goes back to the repository, so the server stays identical to the template. `sudo ./aplicar --conferir` shows how the server differs from the repository.
