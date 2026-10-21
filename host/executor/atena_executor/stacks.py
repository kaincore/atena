"""Stacks de apps (zona apps): stack.editar escreve um arquivo da pasta da stack, no mesmo lugar (mesmo
inode e dono, para bind mounts de arquivo único), e antes guarda uma foto do conteúdo anterior em
/var/lib/atena-executor/fotos/<stack>; stack.desfazer volta a última foto. Mudança no compose só fica
se o compose inteiro (docker compose config, já com includes e overrides) passar nas regras da zona:
nada de privileged, cap_add, devices, rede ou PID do host, socket do Docker, pastas fora da stack e
de /srv/<zona>/<stack>, redes de outras zonas, portas sem IP. stack.aplicar confere de novo e roda
docker compose up -d --build em segundo plano."""

import glob
import json
import os
import re
import subprocess
import threading
import time

from .base import Erro, ler_conf, log, rodar
from .inventario import containers
from .pedidos import TRAVA, mudar
from .segredos import CHAVE_PRIVADA, PASTA_SEGREDO, SEGREDO, ocultar


STACKS = "/opt/atena/stacks"
DADOS_ZONAS = "/srv"
ZONAS_EDITAVEIS = ("apps",)
REDES_DA_ZONA = {"apps": {"zone-apps", "svc-llm"}}
FOTOS = "/var/lib/atena-executor/fotos"
MAX_FOTOS = 50              # por stack; as mais velhas saem
LIMITE_EDICAO = 256 * 1024
APLICANDO = set()           # stacks com stack.aplicar em andamento
# chaves de serviço que dariam ao container o host, o Docker ou outro container
PROIBIDAS = ("privileged", "cap_add", "devices", "device_cgroup_rules", "network_mode", "pid", "ipc", "uts",
             "userns_mode", "cgroup", "volumes_from", "runtime", "isolation", "external_links",
             "use_api_socket", "provider")


def stack_editavel(cliente, params):
    stack = params.get("stack")
    if not isinstance(stack, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", stack):
        raise Erro(400, "nome de stack inválido")
    for zona in ZONAS_EDITAVEIS:
        pasta = f"{STACKS}/{zona}/{stack}"
        if os.path.isdir(pasta) and not os.path.islink(pasta):
            if zona not in cliente["zonas"]:
                raise Erro(403, f"a zona {zona} está fora do alcance deste cliente")
            return zona, stack, os.path.realpath(pasta)
    editaveis = []
    for zona in ZONAS_EDITAVEIS:
        try:
            editaveis += sorted(n for n in os.listdir(f"{STACKS}/{zona}") if os.path.isdir(f"{STACKS}/{zona}/{n}"))
        except OSError:
            pass
    raise Erro(404, f"{stack} não é uma stack editável; as editáveis são as da zona apps: {', '.join(editaveis)}")


def arquivo_da_stack(pasta, arquivo):
    if (not isinstance(arquivo, str) or not arquivo or len(arquivo) > 300 or arquivo.startswith("/")
            or "\0" in arquivo):
        raise Erro(400, "arquivo deve ser um caminho relativo à pasta da stack (ex.: compose.yaml, app/src/index.ts)")
    real = os.path.realpath(os.path.join(pasta, arquivo))
    if not real.startswith(pasta + "/"):
        raise Erro(400, "o arquivo tem que ficar dentro da pasta da stack")
    rel = real[len(pasta) + 1:]
    if PASTA_SEGREDO.search(real) or SEGREDO.search(real):
        raise Erro(403, "arquivos de segredo (.env, chaves, senhas) só o dono edita")
    if re.search(r"(^|/)(\.git|node_modules)(/|$)", rel):
        raise Erro(400, "não edito dentro de .git nem de node_modules")
    return real, rel


def ler_editavel(real):
    """Conteúdo atual (None se ainda não existe); só texto UTF-8."""
    if not os.path.lexists(real):
        return None
    if not os.path.isfile(real):
        raise Erro(400, "não é um arquivo comum")
    if os.path.getsize(real) > LIMITE_EDICAO:
        raise Erro(413, f"arquivo grande demais para editar por aqui (até {LIMITE_EDICAO // 1024} KB)")
    with open(real, "rb") as f:
        bruto = f.read()
    if b"\0" in bruto:
        raise Erro(400, "arquivo binário: só edito texto")
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError:
        raise Erro(400, "o arquivo não está em UTF-8: só edito texto")
    if CHAVE_PRIVADA.search(texto):
        raise Erro(403, "esse arquivo guarda uma chave privada e não sai do servidor")
    return texto


def escrever_no_lugar(real, texto):
    """Mesmo inode e dono: um bind mount de arquivo único continua vendo o arquivo novo."""
    if os.path.lexists(real):
        with open(real, "r+", encoding="utf-8", newline="") as f:
            f.write(texto)
            f.truncate()
        return
    os.makedirs(os.path.dirname(real), mode=0o775, exist_ok=True)
    with open(os.open(real, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o664), "w", encoding="utf-8", newline="") as f:
        f.write(texto)


def restaurar(real, conteudo):
    """Volta o arquivo ao conteúdo de uma foto (None: o arquivo não existia)."""
    if conteudo is None:
        if os.path.isfile(real):
            os.remove(real)
    else:
        escrever_no_lugar(real, conteudo)


def tirar_foto(stack, rel, conteudo):
    pasta = f"{FOTOS}/{stack}"
    os.makedirs(pasta, mode=0o700, exist_ok=True)
    id_ = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() // 1000 % 1000000:06d}"
    with open(os.open(f"{pasta}/{id_}.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as f:
        json.dump({"foto": id_, "quando": time.time(), "arquivo": rel, "existia": conteudo is not None,
                   "conteudo": conteudo}, f, ensure_ascii=False)
    for velha in sorted(glob.glob(f"{pasta}/*.json"))[:-MAX_FOTOS]:
        os.remove(velha)
    return id_


def apagar_foto(stack, foto):
    try:
        os.remove(f"{FOTOS}/{stack}/{foto}.json")
    except FileNotFoundError:
        pass


def fotos_da_stack(stack):
    """Da mais nova para a mais velha."""
    lista = []
    for caminho in sorted(glob.glob(f"{FOTOS}/{stack}/*.json"), reverse=True):
        with open(caminho, encoding="utf-8") as f:
            lista.append(json.load(f))
    return lista


def projeto_da_stack(stack, pasta):
    """Nome do projeto no Docker: o rótulo dos containers que já existem, senão o nome da pasta."""
    codigo, saida = rodar(["docker", "ps", "-a", "--filter", f"label=com.docker.compose.project.working_dir={pasta}",
                           "--format", '{{.Label "com.docker.compose.project"}}'])
    nomes = set(saida.split()) if codigo == 0 else set()
    return nomes.pop() if len(nomes) == 1 else stack


def donos_no_docker(tipo):
    """{nome da rede ou volume: projeto do compose que o criou ('' se nenhum)}."""
    codigo, saida = rodar(["docker", tipo, "ls", "--format", '{{.Name}}\t{{.Label "com.docker.compose.project"}}'])
    return dict(linha.split("\t", 1) for linha in saida.splitlines() if "\t" in linha) if codigo == 0 else {}


def config_json(pasta, projeto, extra=()):
    try:
        r = subprocess.run(["docker", "compose", "-p", projeto, "config", "--format", "json", *extra],
                           cwd=pasta, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None, "docker compose config passou do tempo"
    if r.returncode != 0:
        return None, ocultar(r.stderr.strip()[-1500:]) or "docker compose config falhou"
    try:
        return json.loads(r.stdout), None
    except ValueError:
        return None, "docker compose config não devolveu JSON"


def compose_da_stack(pasta, projeto):
    """O compose como o Docker vai usar: includes, extends e overrides já juntos, caminhos absolutos.
    O env_file e o label_file vêm de uma segunda leitura, com --no-interpolate: na leitura normal, o
    Compose junta o conteúdo deles no environment e nos labels, e o caminho some (no 2.x, até com
    --no-env-resolution). As portas e as pastas ficam da leitura normal, já com as variáveis trocadas."""
    cfg, erro = config_json(pasta, projeto)
    if cfg is None:
        return None, erro
    cru, erro = config_json(pasta, projeto, ["--no-interpolate"])
    if cru is None:
        return None, erro
    for nome, s in (cfg.get("services") or {}).items():
        c = (cru.get("services") or {}).get(nome) or {}
        for chave in ("env_file", "label_file"):
            s.pop(chave, None)
            if c.get(chave):
                s[chave] = c[chave]
    return cfg, None


def problemas_compose(cfg, zona, stack, pasta, projeto):
    """O que impede de aplicar o compose (lista vazia = pode). Regras da zona: o container fica com
    o que a stack já tem (a pasta dela, /srv/<zona>/<stack>, as redes da zona) e nada do host."""
    raizes = (os.path.realpath(pasta), os.path.realpath(f"{DADOS_ZONAS}/{zona}/{stack}"))
    ip_casa = ler_conf().get("ATENA_LAN_IP")

    def dentro(caminho):
        if not isinstance(caminho, str) or not caminho.startswith("/"):
            return False
        real = os.path.realpath(caminho)
        return any(real == r or real.startswith(r + "/") for r in raizes)

    fora = f"fora de {raizes[0]} e {raizes[1]}"
    redes_ok = REDES_DA_ZONA.get(zona, set())
    achados = []
    redes, volumes = donos_no_docker("network"), donos_no_docker("volume")
    for nome, rede in (cfg.get("networks") or {}).items():
        rede = rede or {}
        nome_real = rede.get("name") or nome
        if rede.get("external"):
            if nome_real not in redes_ok:
                achados.append(f"rede {nome_real}: as stacks da zona {zona} só entram em {', '.join(sorted(redes_ok))}")
        elif rede.get("driver") not in (None, "", "bridge") or rede.get("driver_opts"):
            achados.append(f"rede {nome}: só rede bridge simples")
        elif nome_real in redes and redes[nome_real] != projeto:
            achados.append(f"rede {nome_real}: é de outra stack ou do Docker")
    for nome, vol in (cfg.get("volumes") or {}).items():
        vol = vol or {}
        nome_real = vol.get("name") or nome
        if vol.get("external"):
            achados.append(f"volume {nome_real}: volume de fora da stack não pode")
        elif vol.get("driver") not in (None, "", "local") or vol.get("driver_opts"):
            achados.append(f"volume {nome}: driver e driver_opts não podem (viram pasta do host)")
        elif nome_real in volumes and volumes[nome_real] != projeto:
            achados.append(f"volume {nome_real}: é de outra stack")
    for tipo in ("secrets", "configs"):
        for nome, item in (cfg.get(tipo) or {}).items():
            item = item or {}
            if item.get("external"):
                achados.append(f"{tipo} {nome}: externo não pode")
            if item.get("file") and not dentro(item["file"]):
                achados.append(f"{tipo} {nome}: arquivo {item['file']} {fora}")
    for nome, s in (cfg.get("services") or {}).items():
        onde = f"serviço {nome}"
        for chave in PROIBIDAS:
            if s.get(chave):
                achados.append(f"{onde}: {chave} não pode")
        if s.get("cgroup_parent") != f"atena-{zona}.slice":
            achados.append(f"{onde}: cgroup_parent tem que ser atena-{zona}.slice (limites de memória da zona)")
        for opcao in s.get("security_opt") or []:
            if re.sub(r"[\s=]", ":", str(opcao)) not in ("no-new-privileges:true", "no-new-privileges"):
                achados.append(f"{onde}: security_opt {opcao} não pode (só no-new-privileges)")
        for v in s.get("volumes") or []:
            tipo = v.get("type")
            if tipo == "bind" and not dentro(v.get("source")):
                achados.append(f"{onde}: pasta {v.get('source')} {fora}")
            elif tipo not in ("bind", "volume", "tmpfs"):
                achados.append(f"{onde}: volume do tipo {tipo} não pode")
        for porta in s.get("ports") or []:
            if porta.get("published") and porta.get("host_ip") not in ("127.0.0.1", ip_casa):
                achados.append(f"{onde}: a porta {porta.get('published')} precisa do IP na frente "
                               f"(\"{ip_casa}:porta:porta\" para a rede de casa, \"127.0.0.1:...\" só no servidor)")
        arquivos = [x for chave in ("env_file", "label_file") for x in
                    (s.get(chave) if isinstance(s.get(chave), list) else [s.get(chave)] if s.get(chave) else [])]
        for e in arquivos:
            caminho = e.get("path") if isinstance(e, dict) else e
            if not dentro(caminho):
                achados.append(f"{onde}: env_file/label_file {caminho} {fora}")
        b = s.get("build")
        if b:
            b = {"context": b} if isinstance(b, str) else b
            if not dentro(b.get("context")):
                achados.append(f"{onde}: build {b.get('context')} {fora}")
            elif b.get("dockerfile") and not dentro(os.path.join(b["context"], b["dockerfile"])):
                achados.append(f"{onde}: Dockerfile {b['dockerfile']} {fora}")
            for chave in ("network", "additional_contexts", "privileged", "entitlements", "ssh", "secrets"):
                if b.get(chave):
                    achados.append(f"{onde}: build.{chave} não pode")
        for gancho in (s.get("post_start") or []) + (s.get("pre_stop") or []):
            if isinstance(gancho, dict) and gancho.get("privileged"):
                achados.append(f"{onde}: post_start/pre_stop com privileged não pode")
    return achados


def conferir_stack(zona, stack, pasta):
    projeto = projeto_da_stack(stack, pasta)
    cfg, erro = compose_da_stack(pasta, projeto)
    if cfg is None:
        return [f"o compose não abre: {erro}"]
    return problemas_compose(cfg, zona, stack, pasta, projeto)


def e_yaml(rel):
    return rel.endswith((".yaml", ".yml"))   # pode ser o compose ou um arquivo que ele inclui


def acao_stack_editar(cliente, params):
    zona, stack, pasta = stack_editavel(cliente, params)
    real, rel = arquivo_da_stack(pasta, params.get("arquivo"))
    atual = ler_editavel(real)
    if "conteudo" in params:
        novo = params["conteudo"]
        if not isinstance(novo, str):
            raise Erro(400, "conteudo deve ser texto")
    elif "trocar" in params:
        trocas = params["trocar"]
        if atual is None:
            raise Erro(404, f"{rel} não existe; para criar, mande conteudo")
        if not isinstance(trocas, list) or not trocas or not all(
                isinstance(t, dict) and isinstance(t.get("de"), str) and t["de"] and isinstance(t.get("para"), str)
                for t in trocas):
            raise Erro(400, 'trocar deve ser uma lista de {"de": trecho exato do arquivo, "para": trecho novo}')
        novo = atual
        for i, t in enumerate(trocas, 1):
            vezes = novo.count(t["de"])
            if vezes != 1:
                raise Erro(400, f"troca {i}: o trecho aparece {vezes} vez(es) no arquivo; precisa aparecer "
                                "exatamente 1 (copie do arquivo, com mais contexto)")
            novo = novo.replace(t["de"], t["para"])
    else:
        raise Erro(400, "mande conteudo (o arquivo inteiro) ou trocar (lista de trocas)")
    if len(novo.encode("utf-8")) > LIMITE_EDICAO:
        raise Erro(413, f"conteúdo grande demais (até {LIMITE_EDICAO // 1024} KB)")
    if CHAVE_PRIVADA.search(novo):
        raise Erro(403, "não guardo chave privada em arquivo de stack")
    if novo == atual:
        return {"stack": stack, "arquivo": real, "mudou": False}
    foto = tirar_foto(stack, rel, atual)
    try:
        escrever_no_lugar(real, novo)
    except PermissionError:
        apagar_foto(stack, foto)
        raise Erro(403, "sem permissão de escrita nessa pasta")
    if e_yaml(rel):
        problemas = conferir_stack(zona, stack, pasta)
        if problemas:
            restaurar(real, atual)
            apagar_foto(stack, foto)
            raise Erro(422, "não gravei (o arquivo ficou como estava): " + "; ".join(problemas[:8]))
    log(evento="stack editada", cliente=cliente["cliente"], stack=stack, arquivo=rel, foto=foto)
    return {"stack": stack, "arquivo": real, "mudou": True, "foto": foto,
            "proximo": "stack.aplicar põe no ar; stack.desfazer volta esta edição"}


def acao_stack_fotos(cliente, params):
    zona, stack, pasta = stack_editavel(cliente, params)
    return {"stack": stack, "fotos": [
        {"foto": f["foto"], "quando": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(f["quando"])),
         "arquivo": f["arquivo"], "existia": f["existia"]} for f in fotos_da_stack(stack)[:30]]}


def acao_stack_desfazer(cliente, params):
    zona, stack, pasta = stack_editavel(cliente, params)
    fotos = fotos_da_stack(stack)
    if not fotos:
        raise Erro(404, "não há edição para desfazer nessa stack")
    alvo = params.get("foto")
    f = next((x for x in fotos if x["foto"] == alvo), None) if alvo else fotos[0]
    if not f:
        raise Erro(404, "foto não encontrada (stack.fotos lista as fotos)")
    real, rel = arquivo_da_stack(pasta, f["arquivo"])
    restaurar(real, f["conteudo"] if f["existia"] else None)
    apagar_foto(stack, f["foto"])
    log(evento="stack desfeita", cliente=cliente["cliente"], stack=stack, arquivo=rel, foto=f["foto"])
    resultado = {"stack": stack, "voltou": rel, "como_era_antes_de": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(f["quando"])),
                 "removido": not f["existia"], "fotos_restantes": len(fotos) - 1,
                 "proximo": "stack.aplicar põe no ar como era"}
    if e_yaml(rel):
        problemas = conferir_stack(zona, stack, pasta)
        if problemas:
            resultado["aviso"] = "do jeito que ficou, stack.aplicar vai recusar: " + "; ".join(problemas[:5])
    return resultado


def preparar_stack_aplicar(cliente, params):
    zona, stack, pasta = stack_editavel(cliente, params)
    if stack in APLICANDO:
        raise Erro(409, f"já estou aplicando {stack}; acompanhe o pedido anterior")
    problemas = conferir_stack(zona, stack, pasta)
    if problemas:
        raise Erro(422, "não aplico: " + "; ".join(problemas[:8]) + ". Conserte com stack.editar ou volte com stack.desfazer")
    return f"aplicar a stack {stack}", f"docker compose up -d --build em {pasta} (zona {zona})"


def acao_stack_aplicar(p):
    stack = p["params"]["stack"]
    with TRAVA:
        if stack in APLICANDO:
            raise Erro(409, f"já estou aplicando {stack}; acompanhe o pedido anterior")
        APLICANDO.add(stack)
    threading.Thread(target=aplicar_em_segundo_plano, args=(p,), daemon=True).start()
    return None   # o pedido fica em "executando": GET /pedido/<id>?esperar=170


def aplicar_em_segundo_plano(p):
    stack = p["params"]["stack"]
    try:
        resultado = aplicar_stack({"zonas": p["zonas"]}, p["params"])
        mudar(p, estado="concluido", resultado=resultado)
        log(evento="stack aplicada", stack=stack, pedido=p["id"])
    except Erro as e:
        mudar(p, estado="falhou", erro=str(e))
    except Exception as e:
        mudar(p, estado="falhou", erro=f"erro interno: {e}")
        log(evento="erro ao aplicar stack", pedido=p["id"], erro=repr(e))
    finally:
        APLICANDO.discard(stack)


def aplicar_stack(cliente, params):
    zona, stack, pasta = stack_editavel(cliente, params)
    problemas = conferir_stack(zona, stack, pasta)   # de novo: o arquivo pode ter mudado desde o pedido
    if problemas:
        raise Erro(422, "não aplico: " + "; ".join(problemas[:8]))
    projeto = projeto_da_stack(stack, pasta)
    try:
        r = subprocess.run(["docker", "compose", "-p", projeto, "up", "-d", "--build", "--remove-orphans"],
                           cwd=pasta, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        raise Erro(504, "passou de 15 min construindo ou subindo; confira com status.servicos")
    if r.returncode != 0:
        raise Erro(502, "falhou ao subir. Fim do registro:\n" + ocultar((r.stdout + r.stderr).strip()[-1500:])
                   + "\nstack.desfazer volta a última edição")
    time.sleep(8)   # um container que quebra na partida tem tempo de cair
    doks = [c for c in containers() if c["stack"] == projeto]
    resultado = {"aplicado": projeto, "containers": [
        {"container": c["container"], "estado": c["estado"], "status": c["status"]} for c in doks]}
    ruins = [c for c in doks if c["estado"] != "running" or "unhealthy" in c["status"]]
    if ruins:
        _, registro = rodar(["docker", "logs", "--tail", "30", ruins[0]["container"]])
        resultado["problema"] = (f"{ruins[0]['container']} não ficou de pé. Fim do log:\n"
                                 + ocultar(registro.strip()[-1200:]) + "\nstack.desfazer volta a última edição")
    return resultado
