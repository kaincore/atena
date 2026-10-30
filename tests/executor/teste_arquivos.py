"""Procurar e entregar arquivos: tipos, datas, zona prod, segredos, bancos de dados, as pastas de entrega
e a validade das cópias."""
import os
import time

from comum import carregar, confere, erro, fim

ex, tmp = carregar()
fotos, docs, prod = f"{tmp}/fotos", f"{tmp}/docs", f"{tmp}/prod"
for d in (fotos, f"{fotos}/viagem", docs, f"{docs}/.ssh", prod, f"{tmp}/entregas"):
    os.makedirs(d)
ex.ENTREGAS, ex.PASTAS_PROD, ex.PASTAS_ENTREGA = f"{tmp}/entregas", (prod,), (fotos, docs)
open(f"{fotos}/praia.jpg", "wb").write(b"\xff\xd8\xff" + b"\0" * 2000)
open(f"{fotos}/viagem/montanha.PNG", "wb").write(b"\x89PNG\r\n\x1a\n" + b"\0" * 100)
open(f"{fotos}/antiga.jpg", "wb").write(b"\xff\xd8\xff\0")
velho = time.time() - 40 * 86400
os.utime(f"{fotos}/antiga.jpg", (velho, velho))
open(f"{docs}/contrato-aluguel.pdf", "wb").write(b"%PDF-1.4\0binario")
open(f"{docs}/config.yaml", "w").write("nome: loja\nsenha: hunter2\napi_key: abc123\nporta: 8000\n")
open(f"{docs}/.ssh/id_ed25519", "w").write("segredo")
open(f"{docs}/chave.pem", "w").write("-----BEGIN " + "PRIVATE KEY-----\nabc\n")
open(f"{docs}/ruim.txt", "w").write("-----BEGIN " + "OPENSSH PRIVATE KEY-----\nxyz\n")
open(f"{prod}/cliente.pdf", "wb").write(b"%PDF\0")

c = {"cliente": "hermes", "zonas": ["apps", "ai", "agents", "lab", "core"], "acoes": []}
confere("ações registradas, sem aprovação", ex.ACOES["arquivo.procurar"][2] is None and ex.ACOES["arquivo.entregar"][2] is None)

r = ex.acao_arquivo_procurar(c, {"pasta": fotos, "tipo": "foto"})
nomes = [os.path.basename(a["arquivo"]) for a in r["achados"]]
confere("procurar fotos (subpastas, extensão em maiúscula), mais novas primeiro",
        set(nomes) == {"praia.jpg", "montanha.PNG", "antiga.jpg"} and nomes[-1] == "antiga.jpg", nomes)
r = ex.acao_arquivo_procurar(c, {"pasta": fotos, "tipo": "foto", "dias": 7})
confere("filtro de data (últimos 7 dias)", {os.path.basename(a["arquivo"]) for a in r["achados"]} == {"praia.jpg", "montanha.PNG"})
r = ex.acao_arquivo_procurar(c, {"pasta": tmp, "nome": "contrato"})
confere("procurar por pedaço do nome", [os.path.basename(a["arquivo"]) for a in r["achados"]] == ["contrato-aluguel.pdf"], r)
r = ex.acao_arquivo_procurar(c, {"pasta": tmp, "nome": "*.pdf"})
confere("procurar por padrão, sem entrar na pasta de clientes", [os.path.basename(a["arquivo"]) for a in r["achados"]] == ["contrato-aluguel.pdf"], r)
r = ex.acao_arquivo_procurar(c, {"pasta": docs})
nomes = {os.path.basename(a["arquivo"]) for a in r["achados"]}
confere("segredos não aparecem na procura (.ssh, .pem)", "id_ed25519" not in nomes and "chave.pem" not in nomes and "config.yaml" in nomes, nomes)
confere("tipo inválido: 400", erro(ex.acao_arquivo_procurar, c, {"pasta": fotos, "tipo": "exe"})[0] == 400)
confere("pasta de clientes: 403", erro(ex.acao_arquivo_procurar, c, {"pasta": prod})[0] == 403)
confere("com a zona prod, pode", ex.acao_arquivo_procurar({**c, "zonas": c["zonas"] + ["prod"]}, {"pasta": prod})["total"] == 1)
confere("ler arquivo de cliente: 403", erro(ex.acao_arquivo_ler, c, {"caminho": f"{prod}/cliente.pdf"})[0] == 403)
confere("listar a pasta de clientes: 403", erro(ex.acao_arquivo_ler, c, {"caminho": prod})[0] == 403)
confere("com a zona prod, lê", ex.acao_arquivo_ler({**c, "zonas": c["zonas"] + ["prod"]}, {"caminho": f"{prod}/cliente.pdf"})["binario"] is True)

r = ex.acao_arquivo_entregar(c, {"caminho": f"{fotos}/praia.jpg"})
copia = os.path.join(ex.ENTREGAS, os.path.basename(r["copia"]))
confere("foto entregue: cópia idêntica no espaço da Atena", r["copia"].startswith("/opt/data/entregas/")
        and open(copia, "rb").read() == open(f"{fotos}/praia.jpg", "rb").read() and not r["segredos_ocultos"], r)
confere("cópia legível só pelo grupo (640)", oct(os.stat(copia).st_mode & 0o777) == "0o640")
r = ex.acao_arquivo_entregar(c, {"caminho": f"{docs}/config.yaml"})
texto = open(os.path.join(ex.ENTREGAS, os.path.basename(r["copia"]))).read()
confere("texto entregue com os segredos ocultos", "hunter2" not in texto and "abc123" not in texto and "porta: 8000" in texto
        and r["segredos_ocultos"], texto)
r = ex.acao_arquivo_entregar(c, {"caminho": f"{docs}/contrato-aluguel.pdf"})
confere("PDF (binário) entregue inteiro", open(os.path.join(ex.ENTREGAS, os.path.basename(r["copia"])), "rb").read().startswith(b"%PDF"))
confere("chave .pem: 403", erro(ex.acao_arquivo_entregar, c, {"caminho": f"{docs}/chave.pem"})[0] == 403)
confere("arquivo com chave privada dentro: 403", erro(ex.acao_arquivo_entregar, c, {"caminho": f"{docs}/ruim.txt"})[0] == 403)
confere("dentro de .ssh: 403", erro(ex.acao_arquivo_entregar, c, {"caminho": f"{docs}/.ssh/id_ed25519"})[0] == 403)
confere("área do sistema: 403", erro(ex.acao_arquivo_entregar, c, {"caminho": "/proc/self/environ"})[0] == 403)
confere("arquivo de cliente: 403", erro(ex.acao_arquivo_entregar, c, {"caminho": f"{prod}/cliente.pdf"})[0] == 403)
confere("pasta em vez de arquivo: 400", erro(ex.acao_arquivo_entregar, c, {"caminho": fotos})[0] == 400)
confere("não existe: 404", erro(ex.acao_arquivo_entregar, c, {"caminho": f"{tmp}/nada.jpg"})[0] == 404)
ex.LIMITE_ENTREGA = 1000
confere("grande demais para o Telegram: 413", erro(ex.acao_arquivo_entregar, c, {"caminho": f"{fotos}/praia.jpg"})[0] == 413)
ex.LIMITE_ENTREGA = 45 * 1024 * 1024
os.symlink(f"{docs}/.ssh/id_ed25519", f"{fotos}/atalho.jpg")
confere("atalho para segredo: 403 (vale o caminho real)", erro(ex.acao_arquivo_entregar, c, {"caminho": f"{fotos}/atalho.jpg"})[0] == 403)

antigas = os.listdir(ex.ENTREGAS)
for n in antigas:
    os.utime(os.path.join(ex.ENTREGAS, n), (velho, velho))
ex.acao_arquivo_entregar(c, {"caminho": f"{fotos}/praia.jpg"})
confere("cópias com mais de 24 h somem", not set(antigas) & set(os.listdir(ex.ENTREGAS)) and len(os.listdir(ex.ENTREGAS)) == 1)

# binário só sai inteiro das pastas de entrega; texto sai de qualquer lugar, com os segredos ocultos
outra = f"{tmp}/outra"
os.makedirs(outra)
open(f"{outra}/foto.jpg", "wb").write(b"\xff\xd8\xff\0")
open(f"{outra}/notas.txt", "w").write("token: tk_abc\nlista de compras\n")
status, msg = erro(ex.acao_arquivo_entregar, c, {"caminho": f"{outra}/foto.jpg"})
confere("binário fora das pastas de entrega: 403, dizendo como liberar", status == 403 and "ATENA_PASTAS_ENTREGA" in msg, msg)
r = ex.acao_arquivo_entregar(c, {"caminho": f"{outra}/notas.txt"})
texto = open(os.path.join(ex.ENTREGAS, os.path.basename(r["copia"]))).read()
confere("texto fora das pastas de entrega: sai, com os segredos ocultos", "tk_abc" not in texto and "compras" in texto, texto)
open(ex.CONF, "w").write(f"ATENA_PASTAS_ENTREGA={outra} relativa/nao\n")
confere("pasta acrescentada no atena.conf: o binário sai", ex.acao_arquivo_entregar(c, {"caminho": f"{outra}/foto.jpg"})["tamanho_kb"] == 0)
os.unlink(ex.CONF)

# bancos de dados: nem lidos, nem copiados, nem na busca (os tokens do ntfy, os gastos do LiteLLM)
bancos = f"{docs}/bancos"
os.makedirs(f"{bancos}/pg/base/1")
open(f"{bancos}/user.db", "wb").write(b"SQLite format 3\0" + b"\0" * 100)
open(f"{bancos}/sem-extensao", "wb").write(b"SQLite format 3\0" + b"\0" * 100)
open(f"{bancos}/cache.db-wal", "wb").write(b"\x37\x7f\x06\x82")
open(f"{bancos}/appendonly.aof", "w").write("*3\r\n$3\r\nSET\r\n$5\r\nchave\r\n$8\r\nmaracujá\r\n")
open(f"{bancos}/pg/PG_VERSION", "w").write("17\n")
open(f"{bancos}/pg/base/1/1259", "w").write("maracujá no postgres\n")
for nome in ("user.db", "sem-extensao", "cache.db-wal", "appendonly.aof", "pg/base/1/1259"):
    status, msg = erro(ex.acao_arquivo_entregar, c, {"caminho": f"{bancos}/{nome}"})
    confere(f"entregar o banco {nome}: 403", status == 403 and "banco de dados" in msg, f"{status} {msg}")
    confere(f"ler o banco {nome}: 403", erro(ex.acao_arquivo_ler, c, {"caminho": f"{bancos}/{nome}"})[0] == 403)
r = ex.acao_arquivo_buscar(c, {"pasta": bancos, "texto": "maracujá"})
confere("buscar não entra no AOF do Redis nem na pasta do Postgres", r["achados"] == [], r)
confere("buscar dentro da pasta do Postgres: 403", erro(ex.acao_arquivo_buscar, c, {"pasta": f"{bancos}/pg/base", "texto": "maracujá"})[0] == 403)
confere("a pasta dos bancos ainda se lista (só os nomes)", "user.db" in ex.acao_arquivo_ler(c, {"caminho": bancos})["itens"])

# buscar texto também não entra na pasta de clientes
open(f"{prod}/pedido.txt", "w").write("maracujá do cliente\n")
open(f"{docs}/feira.txt", "w").write("maracujá da feira\n")
r = ex.acao_arquivo_buscar(c, {"pasta": tmp, "texto": "maracujá"})
confere("buscar texto pula a pasta de clientes", [os.path.basename(a["arquivo"]) for a in r["achados"]] == ["feira.txt"], r)
confere("buscar dentro da pasta de clientes: 403", erro(ex.acao_arquivo_buscar, c, {"pasta": prod, "texto": "maracujá"})[0] == 403)
r = ex.acao_arquivo_buscar({**c, "zonas": c["zonas"] + ["prod"]}, {"pasta": tmp, "texto": "maracujá"})
confere("com a zona prod, acha os dois", sorted(os.path.basename(a["arquivo"]) for a in r["achados"]) == ["feira.txt", "pedido.txt"], r)

fim()
