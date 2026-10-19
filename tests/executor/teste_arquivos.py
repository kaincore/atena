"""Procurar e entregar arquivos: tipos, datas, zona prod, segredos e a validade das cópias."""
import os
import time

from comum import carregar, confere, erro, fim

ex, tmp = carregar()
fotos, docs, prod = f"{tmp}/fotos", f"{tmp}/docs", f"{tmp}/prod"
for d in (fotos, f"{fotos}/viagem", docs, f"{docs}/.ssh", prod, f"{tmp}/entregas"):
    os.makedirs(d)
ex.ENTREGAS, ex.PASTAS_PROD = f"{tmp}/entregas", (prod,)
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

fim()
