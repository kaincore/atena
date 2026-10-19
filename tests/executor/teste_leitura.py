"""Leitura do servidor sem segredos: caminhos recusados, linhas ocultas e buscas."""
import os

from comum import carregar, confere, erro, fim

ex, tmp = carregar()
c = {"cliente": "hermes", "zonas": ["apps"], "acoes": []}

# segredos montados em pedaços: o arquivo de teste não pode parecer um vazamento
CHAVE_PRIVADA = "-----BEGIN " + "OPENSSH PRIVATE KEY-----\nabc\n"
TOKEN_BOT = "12345678" + ":AA" + "b" * 33
TOKEN_GH = "ghp" + "_" + "c" * 36

d = f"{tmp}/servidor"
for pasta in ("app", "app/.ssh", "app/sub", "app/keys", "home/.config/atena"):
    os.makedirs(f"{d}/{pasta}")
arquivos = {
    "app/config.yaml": "porta: 8080\nsenha: hunter2\napi_key: abc123\nurl: postgres://loja:segredo@db/loja\n",
    "app/app.json": '{"nome": "loja", "client_secret": "xyz", "ok": true}\n',
    "app/notas.txt": f"bot {TOKEN_BOT}\ngit {TOKEN_GH}\nAuthorization: Bearer abcdefghijkl\nfim\n",
    "app/.env": "SEGREDO=1\n",
    "app/.env.producao": "SEGREDO=1\n",
    "app/servidor.key": "x",
    "app/tokens.json": "{}",
    "app/.bash_history": "ls\n",
    "app/.ssh/config": "Host x\n",
    "app/keys/qualquer.txt": "x",
    "app/sub/disfarce.txt": CHAVE_PRIVADA,
    "app/sub/leia.md": "procure a palavra GIRASSOL aqui\n",
    "app/id_ed25519": "x",
    "app/id_ed25519.pub": "ssh-ed25519 AAAA publico\n",
    "home/.config/atena/padroes.txt": "x",
}
for nome, conteudo in arquivos.items():
    with open(f"{d}/{nome}", "w") as f:
        f.write(conteudo)
with open(f"{d}/app/foto.jpg", "wb") as f:
    f.write(b"\xff\xd8\xff\0\0binario")
os.symlink(f"{d}/app/.env", f"{d}/app/atalho.txt")


def le(caminho):
    return ex.acao_arquivo_ler(c, {"caminho": caminho})


# --- caminhos recusados ---
for nome in ("app/.env", "app/.env.producao", "app/servidor.key", "app/tokens.json", "app/.bash_history",
             "app/.ssh/config", "app/keys/qualquer.txt", "app/id_ed25519", "home/.config/atena/padroes.txt"):
    confere(f"segredo recusado: {nome}", erro(le, f"{d}/{nome}")[0] == 403)
confere("chave pública passa", "publico" in le(f"{d}/app/id_ed25519.pub")["texto"])
confere("atalho para um segredo: vale o caminho real (403)", erro(le, f"{d}/app/atalho.txt")[0] == 403)
confere("arquivo com chave privada dentro: 403", erro(le, f"{d}/app/sub/disfarce.txt")[0] == 403)
for area in ("/proc/self/environ", "/run/atena-executor", "/etc/atena/executor/tokens.json", "/var/lib/docker"):
    confere(f"área do sistema: {area}", erro(le, area)[0] == 403)
confere("caminho relativo: 400", erro(le, "app/config.yaml")[0] == 400)
confere("caminho que não existe: 404", erro(le, f"{d}/nada.txt")[0] == 404)

# --- o que sai oculto ---
texto = le(f"{d}/app/config.yaml")["texto"]
confere("linha com senha e chave sai com ***", "hunter2" not in texto and "abc123" not in texto and "senha: ***" in texto, texto)
confere("senha dentro de URL sai com ***", "segredo@" not in texto and "loja:***@" in texto, texto)
confere("o resto continua legível", "porta: 8080" in texto)
texto = le(f"{d}/app/app.json")["texto"]
confere("JSON: valor de chave sensível oculto", "xyz" not in texto and '"nome": "loja"' in texto, texto)
texto = le(f"{d}/app/notas.txt")["texto"]
confere("tokens conhecidos (Telegram, GitHub, Bearer) saem ocultos",
        TOKEN_BOT not in texto and TOKEN_GH not in texto and "abcdefghijkl" not in texto and "fim" in texto, texto)

# --- pastas e binários ---
r = le(f"{d}/app")
confere("pasta: lista os nomes, com / nas subpastas", "sub/" in r["itens"] and "config.yaml" in r["itens"], r)
r = le(f"{d}/app/foto.jpg")
confere("binário volta só com o tamanho", r.get("binario") is True and "texto" not in r, r)

# --- busca ---
r = ex.acao_arquivo_buscar(c, {"pasta": d, "texto": "girassol"})
confere("busca acha sem diferenciar maiúsculas", [os.path.basename(a["arquivo"]) for a in r["achados"]] == ["leia.md"], r)
r = ex.acao_arquivo_buscar(c, {"pasta": d, "texto": "SEGREDO"})
confere("busca não entra em segredos (.env)", all(".env" not in a["arquivo"] for a in r["achados"]), r)
r = ex.acao_arquivo_buscar(c, {"pasta": d, "texto": "hunter2"})
confere("busca não devolve o valor oculto", r["achados"] == [], r)
confere("texto curto demais: 400", erro(ex.acao_arquivo_buscar, c, {"pasta": d, "texto": "a"})[0] == 400)
confere("pasta de segredos: 403", erro(ex.acao_arquivo_buscar, c, {"pasta": f"{d}/app/.ssh", "texto": "Host"})[0] == 403)

# --- journal, processos e rede ---
CHAMADAS = []


def rodar_falso(argv, tempo=30):
    CHAMADAS.append(argv)
    return 0, "out 10 10:00 atena sshd: senha: hunter2\n"


ex.rodar = rodar_falso
texto = ex.acao_servico_journal(c, {"unidade": "ssh", "linhas": 10, "prioridade": "err", "desde": "6h"})
confere("journal monta o comando fixo", CHAMADAS[-1] == ["journalctl", "--no-pager", "-o", "short-iso", "-u", "ssh",
                                                          "-n", "10", "-p", "err", "--since=-6h"], CHAMADAS[-1])
confere("journal sai com segredos ocultos", "hunter2" not in texto)
for params in ({"unidade": "ssh; reboot"}, {"unidade": "-x"}, {"linhas": 0}, {"prioridade": "tudo"},
               {"desde": "ontem"}, {"desde": "6h; ls"}):
    confere(f"journal recusa {params}", erro(ex.acao_servico_journal, c, params)[0] == 400)
r = ex.acao_sistema_processos(c, {"ordem": "ram", "quantos": 3})
confere("processos: cabeçalho e no máximo N linhas", 1 <= len(r.splitlines()) <= 4, r)
confere("processos: ordem inválida 400", erro(ex.acao_sistema_processos, c, {"ordem": "nome"})[0] == 400)
r = ex.acao_sistema_rede(c, {})
confere("rede chama ip e ss", CHAMADAS[-2][0] == "ip" and CHAMADAS[-1][0] == "ss" and set(r) == {"enderecos", "portas"})

fim()
