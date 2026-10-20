"""Arca pela Atena: listar, guardar (com segredos ocultos, no formato do Arca) e pegar, com pastas temporárias."""
import json
import os

from comum import carregar, confere, erro, fim

ex, tmp = carregar()
c = {"cliente": "hermes", "zonas": ["apps", "ai", "agents", "lab", "core"], "acoes": []}
sem_apps = {**c, "zonas": ["ai", "agents", "lab", "core"]}
confere("ações registradas, sem aprovação", all(ex.ACOES[n][2] is None for n in ("arca.lista", "arca.guardar", "arca.pegar")))

with open(ex.CONF, "w") as f:
    f.write("ATENA_LAN_IP=192.168.0.10\n")
arca, hermes, prod = f"{tmp}/arca", f"{tmp}/hermes", f"{tmp}/prod"
for d in (f"{arca}/uploads", f"{arca}/data", hermes, prod, f"{tmp}/entregas"):
    os.makedirs(d)
ex.ARCA_UPLOADS, ex.ARCA_META = f"{arca}/uploads", f"{arca}/data/metadata.json"
ex.ESPACO_HERMES, ex.ENTREGAS, ex.PASTAS_PROD = ("/opt/data", hermes), f"{tmp}/entregas", (prod,)


def escreve(caminho, conteudo):
    with open(caminho, "wb" if isinstance(conteudo, bytes) else "w") as f:
        f.write(conteudo)


confere("Arca sem metadata.json: 503", erro(ex.acao_arca_lista, c, {})[0] == 503)
antigo = {"id": "1769970668230", "originalName": "37.jpg", "savedName": "1769970668224-37.jpg", "size": 5,
          "mimetype": "image/jpeg", "uploadDate": "2026-02-01T18:31:08.230Z"}
escreve(ex.ARCA_META, json.dumps([antigo], indent=2))
escreve(f"{arca}/uploads/1769970668224-37.jpg", b"\xff\xd8\xff\0\0")
inode = os.stat(ex.ARCA_META).st_ino

r = ex.acao_arca_lista(c, {})
confere("lista com nome original e caminho", r["total"] == 1 and r["arquivos"][0]["nome"] == "37.jpg"
        and r["arquivos"][0]["caminho"] == f"{arca}/uploads/1769970668224-37.jpg", r)
confere("lista traz o endereço do Arca pelo IP do atena.conf", r["endereco"] == "http://192.168.0.10:3002", r["endereco"])

escreve(f"{hermes}/relatorio.csv", "nome,valor\nsenha: hunter2\nluz,120\n")
r = ex.acao_arca_guardar(c, {"arquivo": "/opt/data/relatorio.csv"})
meta = json.load(open(ex.ARCA_META))
novo = meta[-1]
confere("guardar: entrada nova no formato do Arca, a antiga fica", len(meta) == 2 and meta[0] == antigo
        and novo["originalName"] == "relatorio.csv" and novo["savedName"] == f"{novo['id']}-relatorio.csv"
        and novo["mimetype"] == "text/csv" and novo["uploadDate"].endswith("Z") and r["id"] == novo["id"], novo)
salvo = f"{arca}/uploads/{novo['savedName']}"
confere("guardar: arquivo nos uploads, legível pelo Arca (644)", os.path.isfile(salvo) and oct(os.stat(salvo).st_mode & 0o777) == "0o644")
confere("guardar: texto com segredos ocultos", "hunter2" not in open(salvo).read() and r["segredos_ocultos"])
confere("guardar: metadata.json escrito no lugar (mesmo inode, segue do Arca)", os.stat(ex.ARCA_META).st_ino == inode)

png = b"\x89PNG\r\n\x1a\n" + bytes(range(256))
escreve(f"{hermes}/grafico.png", png)
ex.acao_arca_guardar(c, {"arquivo": f"{hermes}/grafico.png", "nome": "../../etc/passwd"})
ex.acao_arca_guardar(c, {"arquivo": f"{hermes}/grafico.png"})
meta = json.load(open(ex.ARCA_META))
confere("guardar: binário idêntico", open(f"{arca}/uploads/{meta[-1]['savedName']}", "rb").read() == png)
confere("guardar: nome com / não sai da pasta de uploads", "/" not in meta[-2]["savedName"]
        and os.path.isfile(f"{arca}/uploads/{meta[-2]['savedName']}"), meta[-2])
confere("guardar: ids diferentes mesmo no mesmo milissegundo", len({m["id"] for m in meta}) == len(meta))

escreve(f"{hermes}/.env", "X=1\n")
confere("guardar .env: 403", erro(ex.acao_arca_guardar, c, {"arquivo": "/opt/data/.env"})[0] == 403)
escreve(f"{prod}/cliente.pdf", "%PDF")
confere("guardar arquivo de cliente: 403", erro(ex.acao_arca_guardar, c, {"arquivo": f"{prod}/cliente.pdf"})[0] == 403)
confere("guardar o que não existe: 404", erro(ex.acao_arca_guardar, c, {"arquivo": "/opt/data/nada.txt"})[0] == 404)
confere("guardar pasta: 400", erro(ex.acao_arca_guardar, c, {"arquivo": "/opt/data"})[0] == 400)
confere("guardar sem a zona apps: 403", erro(ex.acao_arca_guardar, sem_apps, {"arquivo": "/opt/data/relatorio.csv"})[0] == 403)
ex.LIMITE_ARCA = 10
confere("guardar acima do limite: 413", erro(ex.acao_arca_guardar, c, {"arquivo": "/opt/data/relatorio.csv"})[0] == 413)
ex.LIMITE_ARCA = 50 * 1024 * 1024
confere("nada sobrou nos uploads de um envio recusado", len(os.listdir(f"{arca}/uploads")) == len(meta))

r = ex.acao_arca_lista(c, {"nome": "RELAT"})
confere("lista filtra pelo nome, sem diferenciar maiúsculas", r["total"] == 1 and r["arquivos"][0]["nome"] == "relatorio.csv", r)
confere("lista: o mais novo primeiro", ex.acao_arca_lista(c, {})["arquivos"][0]["id"] == meta[-1]["id"])
confere("lista sem a zona apps: 403", erro(ex.acao_arca_lista, sem_apps, {})[0] == 403)

r = ex.acao_arca_pegar(c, {"id": antigo["id"]})
confere("pegar: cópia em entregas com o nome original", r["nome"] == "37.jpg" and r["copia"].startswith("/opt/data/entregas/")
        and os.path.isfile(os.path.join(ex.ENTREGAS, os.path.basename(r["copia"]))), r)
confere("pegar id que não existe: 404", erro(ex.acao_arca_pegar, c, {"id": "123"})[0] == 404)
confere("pegar id inválido: 400", erro(ex.acao_arca_pegar, c, {"id": True})[0] == 400)
confere("pegar sem a zona apps: 403", erro(ex.acao_arca_pegar, sem_apps, {"id": antigo["id"]})[0] == 403)
meta = json.load(open(ex.ARCA_META))
meta[0]["savedName"] = "../../segredo"
escreve(ex.ARCA_META, json.dumps(meta))
confere("pegar com savedName que sai da pasta: 500", erro(ex.acao_arca_pegar, c, {"id": antigo["id"]})[0] == 500)

escreve(ex.ARCA_META, "{quebrado")
confere("metadata.json corrompido: 500", erro(ex.acao_arca_lista, c, {})[0] == 500)

fim()
