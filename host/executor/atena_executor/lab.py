"""Apps do lab: app.publicar constrói o projeto pelo Dockerfile e o põe no ar como a stack
/opt/atena/stacks/lab/lab-<projeto> (porta 8000-8999 na rede de casa e, com Tailscale, também fora
de casa, pela unidade atena-lab-tailscale-on@<porta>, que o polkit libera ao executor).
app.reiniciar, app.cancelar, app.apagar e app.restaurar cuidam do resto da vida do app: apagar o
código só o move para /srv/lab/lixeira (o atena-lab-lixeira.timer, como root, esvazia depois de 30
dias); apagar os dados do volume não tem volta. app.comando roda um comando dentro de um app do lab."""

import glob
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time

from .base import Cancelado, Erro, PROCESSOS, ler_conf, log, rodar
from .inventario import containers, ip_casa
from .pedidos import ESTADO, TRAVA, alcanca, mudar
from .segredos import ocultar


STACKS_LAB = "/opt/atena/stacks/lab"
PROJETOS_LAB = "/srv/lab/projetos"
LIXEIRA_LAB = "/srv/lab/lixeira"   # app.apagar move o código para cá; o atena-lab-lixeira.timer esvazia
DIAS_LIXEIRA = 30
PARTES_APAGAR = ("docker", "dados", "codigo")
CANCELAR = set()   # projetos cuja publicação o dono mandou parar
# Uma publicação por projeto: projeto → pedido do app.publicar que está construindo. A segunda recebe
# 409 em vez de esperar numa fila escondida: construiria de novo a mesma pasta, seguraria uma thread por
# até 15 min e escaparia do app.cancelar (CANCELAR e PROCESSOS valem para uma construção por projeto).
PUBLICANDO = {}
TRAVA_PUBLICAR = threading.Lock()
PORTAS_LAB = range(8000, 9000)

# Mesmo padrão das outras stacks: zona lab, sem capacidades, disco só de leitura (escreve em /data) e
# saúde do app ({saude}: a SAUDE_LAB ou nada).
COMPOSE_LAB = """\
# Gerado pelo executor (app.publicar) a partir de {pasta}.
# Não edite: publicar de novo regrava. Para tirar do ar: app.parar.
name: {nome}
services:
  app:
    build: {pasta}
    image: atena-lab/{projeto}:latest
    container_name: {nome}
    restart: unless-stopped
    cgroup_parent: atena-lab.slice
    read_only: true
    tmpfs: [/tmp]
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 256
{saude}    environment:
      PORT: "{porta}"
      DATA_DIR: /data
    ports:
      - "{ip}:{porta}:{porta}"     # rede de casa
      - "127.0.0.1:{porta}:{porta}"     # só no servidor (Tailscale Serve, se um dia quiser)
    volumes:
      - dados:/data
    networks: [zone-lab]
    labels:
      atena.origem: claude-code
volumes:
  dados: {{}}
networks:
  zone-lab:
    external: true
"""

# Saúde do app: só confere se ele atende na porta TCP, sem depender de uma rota HTTP. A imagem é a do
# projeto, então tenta python3, node e wget, nessa ordem; o wget conta qualquer resposta HTTP (até um 404)
# e a falta dos três dá 1 (doente). Escapes: \\" no Python vira \" no YAML, que vira " no sh; e nada de $
# no comando (o compose trocaria pelo valor de uma variável; lá, seria $$).
SAUDE_LAB = """\
    healthcheck:   # porta TCP; um HEALTHCHECK no Dockerfile do projeto tira este (o do compose passaria por cima)
      test: ["CMD-SHELL", "python3 -c \\"import socket; socket.create_connection(('127.0.0.1', {porta}), 3)\\" 2>/dev/null || node -e \\"require('net').connect({porta}, '127.0.0.1').on('connect', () => process.exit(0)).on('error', () => process.exit(1))\\" 2>/dev/null || wget -S -T 3 -t 1 -O /dev/null http://127.0.0.1:{porta}/ 2>&1 | grep -q HTTP/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
"""


def tailscale_ligado():
    return ler_conf().get("ATENA_TAILSCALE") == "sim"


def tailscale_host():
    """Nome do servidor no Tailscale (ex.: atena.exemplo.ts.net), ou None."""
    try:
        r = subprocess.run(["tailscale", "status", "--json", "--peers=false"], capture_output=True, text=True, timeout=10)
        return json.loads(r.stdout)["Self"]["DNSName"].rstrip(".") or None
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired):
        return None


def portas_no_tailscale():
    """Portas que o tailscale serve publica agora."""
    try:
        r = subprocess.run(["tailscale", "serve", "status", "--json"], capture_output=True, text=True, timeout=10)
        return {int(p) for p in (json.loads(r.stdout or "{}").get("TCP") or {}) if str(p).isdigit()}
    except (OSError, ValueError, AttributeError, subprocess.TimeoutExpired):
        return set()


def link_tailscale(porta, ligar):
    """Liga ou desliga o acesso de fora de casa (tailscale serve + regra do ufw na tailscale0) pela
    unidade atena-lab-tailscale-<on|off>@<porta>, a única que o polkit libera ao executor.
    Devolve (link ou None, erro ou None). Sem Tailscale (ATENA_TAILSCALE=nao), não faz nada."""
    if not tailscale_ligado():
        return None, None
    unidade = f"atena-lab-tailscale-{'on' if ligar else 'off'}@{porta}.service"
    codigo, texto = rodar(["systemctl", "start", "--no-ask-password", unidade], 60)
    if codigo != 0:
        log(evento="tailscale: falhou", unidade=unidade, erro=texto.strip()[-300:])
        return None, texto.strip()[-300:] or "falhou"
    host = tailscale_host() if ligar else None
    return (f"https://{host}:{porta}" if host else None), None


def lab_no_ar(cliente):
    if not os.path.isdir(PROJETOS_LAB):
        raise Erro(503, "o lab não está instalado neste servidor (sudo ./install.sh --lab)")
    if "lab" not in cliente["zonas"]:
        raise Erro(403, "a zona lab está fora do alcance deste cliente")


def projeto_lab(cliente, params):
    lab_no_ar(cliente)
    projeto = params.get("projeto")
    if not isinstance(projeto, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", projeto):
        raise Erro(400, "projeto deve ser o nome de uma pasta de /srv/lab/projetos (minúsculas, números e hífen)")
    return projeto, f"lab-{projeto}", f"{PROJETOS_LAB}/{projeto}", f"{STACKS_LAB}/lab-{projeto}/compose.yaml"


def porta_do_compose(compose):
    try:
        with open(compose) as f:
            m = re.search(r'"[0-9.]+:(\d+):\d+"', f.read())   # a primeira porta: a da rede de casa
    except OSError:
        return None
    return int(m.group(1)) if m else None


def portas_ocupadas():
    ocupadas = {porta_do_compose(c) for c in glob.glob(f"{STACKS_LAB}/*/compose.yaml")}
    _, saida = rodar(["ss", "-H", "-tln"])
    for linha in saida.splitlines():
        campos = linha.split()
        if len(campos) >= 4 and campos[3].rsplit(":", 1)[-1].isdigit():
            ocupadas.add(int(campos[3].rsplit(":", 1)[-1]))
    return ocupadas - {None}


def preparar_app_publicar(cliente, params):
    projeto, nome, pasta, compose = projeto_lab(cliente, params)
    if not os.path.isdir(pasta):
        raise Erro(404, f"não existe {pasta}")
    if not os.path.isfile(f"{pasta}/Dockerfile"):
        raise Erro(409, "o projeto ainda não tem Dockerfile: peça ao Claude Code para deixá-lo pronto "
                        "para publicar (regras do lab: Dockerfile, PORT e DATA_DIR)")
    with TRAVA:
        rodando = [p["id"] for p in ESTADO["pedidos"].values() if p["acao"] == "claude.tarefa"
                   and p["estado"] in ("planejando", "executando") and p["params"].get("projeto") == projeto]
    if rodando:
        raise Erro(409, f"o Claude Code ainda está trabalhando nesse projeto ({rodando[0]}); publique quando terminar")
    with TRAVA_PUBLICAR:
        publicando = PUBLICANDO.get(projeto)
    if publicando:
        raise Erro(409, publicacao_em_andamento(projeto, publicando))
    atual = porta_do_compose(compose)   # publicar de novo mantém a porta
    ocupadas = portas_ocupadas() - {atual}
    porta = params.get("porta", atual)
    if porta is None:
        porta = next((n for n in PORTAS_LAB if n not in ocupadas), None)
        if porta is None:
            raise Erro(507, "não há porta livre entre 8000 e 8999")
    elif not isinstance(porta, int) or porta not in PORTAS_LAB:
        raise Erro(400, "porta deve ser um número de 8000 a 8999")
    elif porta in ocupadas:
        raise Erro(409, f"a porta {porta} já está em uso")
    params["porta"] = porta
    return (f"publicar {projeto} em http://{ip_casa()}:{porta}",
            f"Constrói a imagem pelo Dockerfile de {pasta} e deixa o app no ar na rede de casa, na zona lab "
            "(sem acesso ao resto do servidor). Fica ligado até alguém pedir app.parar.")


def healthcheck_proprio(pasta):
    """O Dockerfile do projeto tem HEALTHCHECK (ou HEALTHCHECK NONE)? Só conta o do último estágio (depois
    do último FROM): é o que vai para a imagem."""
    try:
        with open(f"{pasta}/Dockerfile", errors="replace") as f:
            final = re.split(r"^\s*FROM\b", f.read(), flags=re.M | re.I)[-1]
    except OSError:
        return False
    return bool(re.search(r"^\s*HEALTHCHECK\b", final, re.M | re.I))


def atende(porta, projeto, segundos=20):
    """Espera o app atender na porta; para antes se o dono cancelar."""
    for _ in range(segundos):
        time.sleep(1)
        if projeto in CANCELAR:
            raise Cancelado("cancelado pelo dono enquanto o app subia; confira com app.lista o que ficou no ar")
        try:
            socket.create_connection(("127.0.0.1", porta), timeout=1).close()
            return True
        except OSError:
            pass
    return False


def publicacao_em_andamento(projeto, pedido):
    return (f"já há uma publicação de {projeto} em andamento (pedido {pedido}); espere ela terminar (o celular "
            "avisa) e publique de novo se ainda precisar, ou pare a construção com app.cancelar")


def acao_app_publicar(p):
    projeto, nome, pasta, compose = projeto_lab({"zonas": p["zonas"]}, p["params"])
    with TRAVA_PUBLICAR:   # dois pedidos aprovados juntos: só um constrói
        if projeto in PUBLICANDO:
            raise Erro(409, publicacao_em_andamento(projeto, PUBLICANDO[projeto]))
        PUBLICANDO[projeto] = p["id"]
    CANCELAR.discard(projeto)
    try:
        return publicar(projeto, nome, pasta, compose, p["params"]["porta"])
    finally:
        CANCELAR.discard(projeto)
        with TRAVA_PUBLICAR:
            PUBLICANDO.pop(projeto, None)


def publicar(projeto, nome, pasta, compose, porta):
    os.makedirs(os.path.dirname(compose), mode=0o755, exist_ok=True)
    temporario = os.path.join(os.path.dirname(compose), ".compose.yaml.novo")
    with open(os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644), "w") as f:
        saude = "" if healthcheck_proprio(pasta) else SAUDE_LAB.format(porta=porta)
        f.write(COMPOSE_LAB.format(pasta=pasta, nome=nome, projeto=projeto, porta=porta, ip=ip_casa(), saude=saude))
    os.replace(temporario, compose)
    base = ["docker", "compose", "-f", compose, "-p", nome]
    codigo, texto = rodar([*base, "up", "-d", "--build", "--remove-orphans"], 900, cancelavel=projeto)
    if projeto in CANCELAR:   # a construção parou no meio: o que já estava no ar continua como estava
        raise Cancelado("cancelado pelo dono durante a construção; a versão que estava no ar (se havia) continua")
    if codigo != 0:
        raise Erro(502, "a construção ou a subida falhou. Fim do registro:\n" + texto.strip()[-1500:])
    if atende(porta, projeto):
        log(evento="app publicado", projeto=projeto, porta=porta)
        resultado = {"endereco": f"http://{ip_casa()}:{porta}", "stack": nome}
        if tailscale_ligado():
            link, erro = link_tailscale(porta, True)
            resultado["fora_de_casa"] = link or f"não consegui ligar o link do Tailscale: {erro}"
        return resultado
    _, registro = rodar(["docker", "logs", "--tail", "40", nome])
    rodar([*base, "down"], 120)   # não deixa um container quebrado reiniciando sem parar
    raise Erro(502, f"o container subiu, mas o app não respondeu na porta {porta} em 20 s (ele precisa ouvir "
                    f"em 0.0.0.0, na porta da variável PORT). Tirei do ar. Fim do log:\n{registro.strip()[-1200:]}")


def acao_app_parar(cliente, params):
    projeto, nome, pasta, compose = projeto_lab(cliente, params)
    if not os.path.isfile(compose):
        raise Erro(404, f"{projeto} não está publicado")
    codigo, texto = rodar(["docker", "compose", "-f", compose, "-p", nome, "down"], 120)
    if codigo != 0:
        raise Erro(500, texto.strip()[-500:] or "falha ao parar")
    porta = porta_do_compose(compose)
    if porta:
        link_tailscale(porta, False)   # sem app, o link de fora de casa só daria erro
    return {"parado": nome, "dica": "dados e imagem ficam; app.reiniciar religa, app.publicar reconstrói"}


def acao_app_reiniciar(cliente, params):
    projeto, nome, pasta, compose = projeto_lab(cliente, params)
    if not os.path.isfile(compose):
        raise Erro(404, f"{projeto} não está publicado (app.publicar põe no ar)")
    base = ["docker", "compose", "-f", compose, "-p", nome]
    parado = not existe_no_docker("container", nome)   # app.parar remove o container
    codigo, texto = rodar([*base, "up", "-d", "--no-build"] if parado else [*base, "restart"], 120)
    if codigo != 0:
        raise Erro(500, (texto.strip()[-500:] or "falha ao reiniciar")
                   + ("\nSe a imagem não existe mais, use app.publicar." if parado else ""))
    porta = porta_do_compose(compose)
    if porta and not atende(porta, projeto):
        raise Erro(502, f"reiniciou, mas o app não respondeu na porta {porta} em 20 s; veja servico.logs {nome}")
    resultado = {"reiniciado": nome, "endereco": f"http://{ip_casa()}:{porta}" if porta else None}
    if parado:
        resultado["obs"] = "estava parado: subiu de novo com a imagem que já existia"
    if not tailscale_ligado():
        pass
    elif porta and (parado or porta not in portas_no_tailscale()):
        link, erro = link_tailscale(porta, True)
        resultado["fora_de_casa"] = link or f"não consegui ligar o link do Tailscale: {erro}"
    elif porta:
        host = tailscale_host()
        resultado["fora_de_casa"] = f"https://{host}:{porta}" if host else None
    return resultado


def acao_app_comando(cliente, params):
    """Roda um comando dentro do container de um app do lab, como o usuário do próprio app."""
    projeto, nome, pasta, compose = projeto_lab(cliente, params)
    comando = params.get("comando")
    if isinstance(comando, str) and comando.strip():
        argv = ["sh", "-c", comando]
    elif isinstance(comando, list) and comando and all(isinstance(x, str) for x in comando):
        argv = comando
    else:
        raise Erro(400, "comando deve ser um texto (roda com sh -c) ou uma lista de argumentos")
    if sum(len(x) for x in argv) > 4000:
        raise Erro(400, "comando grande demais (até 4000 letras)")
    segundos = params.get("segundos", 30)
    if not isinstance(segundos, int) or not 1 <= segundos <= 120:
        raise Erro(400, "segundos deve ser um número de 1 a 120")
    doks = [c for c in containers() if c["container"] == nome]
    if not doks or doks[0]["stack"] != nome or doks[0]["zona"] != "lab":
        raise Erro(404, f"{projeto} não está publicado (app.lista mostra os apps)")
    if doks[0]["estado"] != "running":
        raise Erro(409, f"o app {projeto} não está rodando ({doks[0]['estado']}); app.reiniciar sobe de novo")
    try:
        codigo, texto = rodar(["docker", "exec", nome, *argv], segundos)
    except subprocess.TimeoutExpired:
        raise Erro(504, f"o comando passou de {segundos} s; ele pode continuar rodando dentro do app "
                        "(app.reiniciar zera)")
    log(evento="comando no app", projeto=projeto, codigo=codigo)
    resultado = {"codigo": codigo, "saida": ocultar(texto)}
    if codigo in (126, 127) and argv[0] == "sh":
        resultado["dica"] = "o app pode não ter sh; mande o comando como lista, ex.: [\"ls\", \"/data\"]"
    return resultado


def em_andamento():
    """projeto → id do trabalho do Claude Code ou da publicação que está rodando nele."""
    with TRAVA:
        return {p["params"].get("projeto"): p["id"] for p in ESTADO["pedidos"].values()
                if (p["acao"] == "claude.tarefa" and p["estado"] in ("planejando", "executando"))
                or (p["acao"] == "app.publicar" and p["estado"] == "executando")}


def acao_app_cancelar(cliente, params):
    """Para o que estiver em andamento num projeto: Claude Code, construção e pedidos no celular."""
    from .claude import cancelar_claude  # aqui: o claude usa este módulo
    projeto = projeto_lab(cliente, params)[0]
    feito = []
    with TRAVA:
        for p in list(ESTADO["pedidos"].values()):
            if not alcanca(cliente, p) or p["params"].get("projeto") != projeto:
                continue
            if p["acao"] == "claude.tarefa" and p["estado"] in ("planejando", "executando"):
                cancelar_claude(p)
                feito.append(f"trabalho do Claude Code {p['id']} (o resumo chega quando ele parar)")
            elif p["estado"] == "aguardando":
                mudar(p, estado="cancelado", segredo=None)
                feito.append(f"pedido {p['id']} que esperava o celular ({p['titulo']})")
            elif p["acao"] in ("app.publicar", "receita.estudar") and p["estado"] == "executando":
                CANCELAR.add(projeto)
                processo = PROCESSOS.get(projeto)
                if processo:
                    processo.terminate()
                o_que = "publicação" if p["acao"] == "app.publicar" else "coleta da receita"
                feito.append(f"{o_que} {p['id']} (o celular avisa quando parar)")
    if not feito:
        raise Erro(404, f"não há nada em andamento no projeto {projeto}")
    log(evento="projeto cancelado", projeto=projeto, cancelado=feito)
    return {"cancelado": feito}


def existe_no_docker(tipo, alvo):
    return rodar(["docker", tipo, "inspect", alvo], 15)[0] == 0


def quando(carimbo, dias=0):
    instante = time.mktime(time.strptime(carimbo, "%Y%m%d-%H%M%S")) + dias * 86400
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(instante))


def lixeira(projeto=None):
    """Projetos apagados, do mais novo para o mais velho: (projeto, pasta, carimbo)."""
    itens = []
    for caminho in glob.glob(f"{LIXEIRA_LAB}/*"):
        m = re.fullmatch(r"([a-z0-9][a-z0-9-]{0,39})\.(\d{8}-\d{6})", os.path.basename(caminho))
        if m and projeto in (None, m.group(1)) and os.path.isdir(caminho) and not os.path.islink(caminho):
            itens.append((m.group(1), caminho, m.group(2)))
    return sorted(itens, key=lambda i: i[2], reverse=True)


def preparar_app_apagar(cliente, params):
    projeto, nome, pasta, compose = projeto_lab(cliente, params)
    partes = params.get("partes")
    if (not isinstance(partes, list) or not partes
            or any(not isinstance(x, str) or x not in PARTES_APAGAR for x in partes)):
        raise Erro(400, "partes deve ser uma lista com docker, dados e/ou codigo")
    if "dados" in partes:
        partes = [*partes, "docker"]   # o volume só sai depois do container
    params["partes"] = [x for x in PARTES_APAGAR if x in partes]
    rodando = em_andamento().get(projeto)
    if rodando:
        raise Erro(409, f"há algo em andamento no projeto ({rodando}); use app.cancelar antes")
    no_docker = (os.path.isfile(compose) or existe_no_docker("container", nome)
                 or existe_no_docker("image", f"atena-lab/{projeto}:latest"))
    apaga, fica = [], []
    if no_docker:
        if "docker" in partes:
            apaga.append(f"tira do ar e apaga do Docker o container {nome} e a imagem atena-lab/{projeto}")
        else:
            fica.append("o app no Docker")
    if existe_no_docker("volume", f"{nome}_dados"):
        if "dados" in partes:
            apaga.append(f"⚠ apaga os dados do app (volume {nome}_dados): NÃO TEM VOLTA")
        else:
            fica.append(f"os dados (volume {nome}_dados; publicar de novo volta com eles)")
    if os.path.isdir(pasta):
        if "codigo" in partes:
            apaga.append(f"manda o código ({pasta}) para a lixeira; dá para restaurar por {DIAS_LIXEIRA} dias")
        else:
            fica.append(f"o código ({pasta})")
    if not apaga:
        raise Erro(404, f"não há nada para apagar em {projeto} com essas partes")
    texto = "\n".join(f"• {a}" for a in apaga)
    if fica:
        texto += "\n\nFica: " + "; ".join(fica)
    return f"apagar {projeto} ({', '.join(params['partes'])})", texto


def acao_app_apagar(p):
    projeto, nome, pasta, compose = projeto_lab({"zonas": p["zonas"]}, p["params"])
    partes = p["params"]["partes"]
    rodando = em_andamento().get(projeto)   # pode ter começado algo enquanto o pedido esperava o celular
    if rodando:
        raise Erro(409, f"começou algo no projeto enquanto o pedido esperava ({rodando}); nada foi apagado")
    feito = []
    if "docker" in partes:
        if os.path.isfile(compose):
            porta = porta_do_compose(compose)
            codigo, texto = rodar(["docker", "compose", "-f", compose, "-p", nome, "down", "--rmi", "all",
                                   "--remove-orphans"], 180)
            if codigo != 0:
                raise Erro(500, "não consegui tirar do Docker: " + texto.strip()[-500:])
            if porta:
                link_tailscale(porta, False)
            shutil.rmtree(os.path.dirname(compose))
            feito.append(f"container {nome} e imagem atena-lab/{projeto}")
        elif existe_no_docker("image", f"atena-lab/{projeto}:latest"):
            codigo, texto = rodar(["docker", "image", "rm", f"atena-lab/{projeto}:latest"], 60)
            if codigo != 0:
                raise Erro(500, "não consegui apagar a imagem: " + texto.strip()[-500:])
            feito.append(f"imagem atena-lab/{projeto}")
    if "dados" in partes and existe_no_docker("volume", f"{nome}_dados"):
        codigo, texto = rodar(["docker", "volume", "rm", f"{nome}_dados"], 60)
        if codigo != 0:
            raise Erro(500, f"{'; '.join(feito) or 'nada'} saiu, mas os dados não: " + texto.strip()[-500:])
        feito.append(f"dados (volume {nome}_dados)")
    if "codigo" in partes and os.path.isdir(pasta):
        carimbo = time.strftime("%Y%m%d-%H%M%S")
        try:
            os.rename(pasta, f"{LIXEIRA_LAB}/{projeto}.{carimbo}")
        except OSError as e:
            raise Erro(500, f"{'; '.join(feito) or 'nada'} saiu, mas o código não foi para a lixeira: {e}")
        feito.append(f"código (na lixeira até {quando(carimbo, DIAS_LIXEIRA)}; app.restaurar traz de volta)")
    log(evento="app apagado", projeto=projeto, partes=partes, feito=feito)
    return {"apagado": feito or ["nada: já não existia"]}


def acao_app_restaurar(cliente, params):
    projeto, nome, pasta, compose = projeto_lab(cliente, params)
    itens = lixeira(projeto)
    if not itens:
        raise Erro(404, f"{projeto} não está na lixeira")
    if os.path.lexists(pasta):
        raise Erro(409, f"já existe {pasta}; apague ou escolha outro nome antes de restaurar")
    _, caminho, carimbo = itens[0]   # o mais novo, se foi apagado mais de uma vez
    os.rename(caminho, pasta)
    log(evento="projeto restaurado", projeto=projeto, de=caminho)
    return {"restaurado": pasta, "apagado_em": quando(carimbo),
            "dica": "app.publicar põe no ar de novo (com os dados, se eles ficaram)"}


def acao_app_lista(cliente, params):
    lab_no_ar(cliente)
    estados = {c["container"]: c["status"] for c in containers()}
    _, saida = rodar(["docker", "volume", "ls", "-q", "--filter", "name=lab-"])
    com_dados = {m.group(1) for m in re.finditer(r"^lab-([a-z0-9-]+)_dados$", saida, re.M)}
    portas = {os.path.basename(os.path.dirname(c))[4:]: porta_do_compose(c)
              for c in glob.glob(f"{STACKS_LAB}/lab-*/compose.yaml")}
    pastas = {os.path.basename(d) for d in glob.glob(f"{PROJETOS_LAB}/*") if os.path.isdir(d)}
    andamento = em_andamento()
    servidas = portas_no_tailscale() if tailscale_ligado() else set()
    host = tailscale_host() if servidas else None
    projetos = []
    for projeto in sorted(pastas | set(portas) | com_dados):
        porta = portas.get(projeto)
        item = {"projeto": projeto,
                "app": estados.get(f"lab-{projeto}", "parado") if projeto in portas else "não publicado",
                "endereco": f"http://{ip_casa()}:{porta}" if porta else None,
                "fora_de_casa": f"https://{host}:{porta}" if host and porta in servidas else None,
                "codigo": projeto in pastas, "dados_guardados": projeto in com_dados}
        if projeto in andamento:
            item["em_andamento"] = andamento[projeto]
        projetos.append(item)
    return {"projetos": projetos,
            "lixeira": [{"projeto": p, "apagado_em": quando(c), "some_de_vez_em": quando(c, DIAS_LIXEIRA)}
                        for p, _, c in lixeira()]}
