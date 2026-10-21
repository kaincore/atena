"""O estado do servidor: serviços, recursos, containers, registros, processos, rede, gasto da API e
reiniciar um serviço.

Sensores: sistema.sensores lê /sys/class/hwmon (CPU, NVMe e o chip da placa, com as ventoinhas) e a
GPU pelo nvidia-smi."""

import glob
import json
import os
import re
import subprocess
import time

import yaml

from .base import Erro, ler, rodar
from .inventario import containers, stack_permitida
from .segredos import ocultar


def acao_status_servicos(cliente, params):
    return [c for c in containers() if c["zona"] in cliente["zonas"]]


def acao_status_recursos(cliente, params):
    with open("/proc/loadavg") as f:
        carga = [float(x) for x in f.read().split()[:3]]
    mem = {}
    with open("/proc/meminfo") as f:
        for linha in f:
            chave, valor = linha.split(":", 1)
            mem[chave] = int(valor.split()[0]) // 1024
    discos = {}
    for ponto in ("/", "/srv"):
        st = os.statvfs(ponto)
        discos[ponto] = {"total_gb": round(st.f_blocks * st.f_frsize / 1e9, 1),
                         "livre_gb": round(st.f_bavail * st.f_frsize / 1e9, 1)}
    gpu = None
    try:
        codigo, saida = rodar(["nvidia-smi", "--query-gpu=name,memory.used,memory.total,temperature.gpu,utilization.gpu",
                               "--format=csv,noheader,nounits"], 10)
        if codigo == 0:
            nome, usada, total, temp, uso = [x.strip() for x in saida.strip().split(",")]
            gpu = {"nome": nome, "vram_usada_mb": int(usada), "vram_total_mb": int(total),
                   "temperatura_c": int(temp), "uso_pct": int(uso)}
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    sensores = ler_hwmon()
    temperaturas = {"cpu_c": temperatura_cpu(sensores), "nvme_c": temperatura_nvme(sensores)}
    return {"carga": carga, "nucleos": os.cpu_count(),
            "ram_total_mb": mem["MemTotal"], "ram_disponivel_mb": mem["MemAvailable"],
            "discos": discos, "gpu": gpu, "temperaturas": temperaturas}


HWMON = "/sys/class/hwmon"
CPU_QUENTE, NVME_QUENTE, GPU_QUENTE = 85, 70, 85   # CPUs de mesa costumam se proteger perto de 90-100 °C
# chips de temperatura da CPU: AMD (k10temp, zenpower), Intel (coretemp) e placas ARM (cpu_thermal)
CHIPS_CPU = ("k10temp", "zenpower", "coretemp", "cpu_thermal")
ROTULOS_CPU = ("Tctl", "Tdie", "Package id 0")
# chips da placa-mãe (Super I/O), que leem as ventoinhas; costumam precisar de um módulo do kernel
CHIPS_PLACA = ("nct", "it8", "f71", "w83")


def ler_hwmon():
    """{chip: {"temperaturas": {rótulo: (°C, alerta °C ou None)}, "ventoinhas": {fanN: rpm}}}"""
    chips = {}
    for pasta in sorted(glob.glob(f"{HWMON}/hwmon*")):
        try:
            nome = ler(f"{pasta}/name")
        except OSError:
            continue
        chip = chips.setdefault(nome, {"temperaturas": {}, "ventoinhas": {}})
        for entrada in sorted(glob.glob(f"{pasta}/temp*_input")):
            base = entrada[:-len("_input")]
            try:
                valor = int(ler(entrada)) / 1000
            except (OSError, ValueError):
                continue
            if not -20 < valor < 150:   # sensor desligado ou sem nada ligado
                continue
            try:
                rotulo = ler(f"{base}_label")
            except OSError:
                rotulo = os.path.basename(base)
            alerta = None
            for limite in ("_max", "_crit"):
                try:
                    alerta = int(ler(base + limite)) / 1000 or None
                    break
                except (OSError, ValueError):
                    pass
            chip["temperaturas"].setdefault(rotulo, (round(valor, 1), alerta))
        for entrada in sorted(glob.glob(f"{pasta}/fan*_input")):
            try:
                rpm = int(ler(entrada))
            except (OSError, ValueError):
                continue
            if rpm > 0:
                chip["ventoinhas"][os.path.basename(entrada)[:-len("_input")]] = rpm
    return chips


def temperaturas_cpu(sensores):
    return next((sensores[n]["temperaturas"] for n in CHIPS_CPU if sensores.get(n, {}).get("temperaturas")), {})


def temperatura_cpu(sensores):
    temps = temperaturas_cpu(sensores)
    valor = next((temps[r] for r in ROTULOS_CPU if r in temps), None) or next(iter(temps.values()), None)
    return valor[0] if valor else None


def temperatura_nvme(sensores):
    temps = sensores.get("nvme", {}).get("temperaturas", {})
    valor = temps.get("Composite") or next(iter(temps.values()), None)
    return valor[0] if valor else None


def acao_sistema_sensores(cliente, params):
    sensores = ler_hwmon()
    nucleos = {r: v[0] for r, v in temperaturas_cpu(sensores).items() if r.startswith(("Tccd", "Core "))}
    nvme = sensores.get("nvme", {}).get("temperaturas", {})
    resultado = {
        "cpu": {"temperatura_c": temperatura_cpu(sensores), "quente_a_partir_de_c": CPU_QUENTE,
                "nucleos_c": nucleos or None},
        "nvme": {"temperatura_c": temperatura_nvme(sensores),
                 "alerta_c": (nvme.get("Composite") or (None, None))[1] or NVME_QUENTE},
        "gpu": None,
        "placa": None,
    }
    try:
        codigo, saida = rodar(["nvidia-smi", "--query-gpu=temperature.gpu,fan.speed,power.draw,utilization.gpu",
                               "--format=csv,noheader,nounits"], 10)
        if codigo == 0:
            temp, ventoinha, consumo, uso = [x.strip() for x in saida.strip().split(",")]
            numero = lambda x: float(x) if x.replace(".", "", 1).isdigit() else None   # "[N/A]" vira None
            resultado["gpu"] = {"temperatura_c": numero(temp), "ventoinha_pct": numero(ventoinha),
                                "consumo_w": numero(consumo), "uso_pct": numero(uso),
                                "quente_a_partir_de_c": GPU_QUENTE}
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    placa = next((sensores[n] for n in sensores if n.startswith(CHIPS_PLACA)), None)
    if placa:
        resultado["placa"] = {"temperaturas_c": {r: v[0] for r, v in placa["temperaturas"].items()},
                              "ventoinhas_rpm": placa["ventoinhas"],
                              "obs": "fan1 costuma ser o conector CPU_FAN da placa"}
    else:
        resultado["placa"] = {"obs": "chip da placa sem leitura (sem ventoinhas); pode precisar de um módulo do "
                                     "kernel, como nct6683 ou it87 (ATENA_SENSORES_MODULO no atena.conf)"}
    quentes = []
    if (resultado["cpu"]["temperatura_c"] or 0) >= CPU_QUENTE:
        quentes.append(f"CPU a {resultado['cpu']['temperatura_c']} °C")
    if (resultado["nvme"]["temperatura_c"] or 0) >= resultado["nvme"]["alerta_c"]:
        quentes.append(f"NVMe a {resultado['nvme']['temperatura_c']} °C")
    if resultado["gpu"] and (resultado["gpu"]["temperatura_c"] or 0) >= GPU_QUENTE:
        quentes.append(f"GPU a {resultado['gpu']['temperatura_c']} °C")
    resultado["avaliacao"] = "quente: " + ", ".join(quentes) if quentes else "normal"
    return resultado


def acao_status_containers(cliente, params):
    zona = {c["container"]: c["zona"] for c in containers()}
    codigo, saida = rodar(["docker", "stats", "--no-stream", "--format",
                           "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"], 30)
    if codigo != 0:
        raise Erro(500, "não consegui ler o uso dos containers")
    lista = []
    for linha in saida.splitlines():
        partes = linha.split("\t")
        if len(partes) == 4 and zona.get(partes[0]) in cliente["zonas"]:
            lista.append({"container": partes[0], "zona": zona[partes[0]], "cpu": partes[1],
                          "ram": partes[2].split(" / ")[0], "ram_pct": partes[3]})
    return sorted(lista, key=lambda c: c["container"])


def acao_status_sistema(cliente, params):
    """Serviços e timers atena-* do systemd, e as unidades com falha do sistema todo."""
    _, unidades = rodar(["systemctl", "list-units", "atena-*", "--all", "--no-legend", "--plain", "-o", "json"])
    _, timers = rodar(["systemctl", "list-timers", "atena-*", "--all", "--no-legend", "-o", "json"])
    _, falhas = rodar(["systemctl", "list-units", "--state=failed", "--all", "--no-legend", "--plain", "-o", "json"])
    def data(usec):
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(usec / 1e6)) if usec else None
    try:
        return {"unidades": [{"nome": u["unit"], "ativa": u["active"], "estado": u["sub"]}
                             for u in json.loads(unidades or "[]") if not u["unit"].endswith(".slice")],
                "timers": [{"nome": t["unit"], "proxima": data(t.get("next")), "ultima": data(t.get("last"))}
                           for t in json.loads(timers or "[]")],
                "falhas": [u["unit"] for u in json.loads(falhas or "[]")]}
    except (ValueError, KeyError):
        raise Erro(500, "não consegui ler o systemd")


PRIORIDADES = {"emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"}


def acao_servico_journal(cliente, params):
    """Registro do systemd de uma unidade qualquer, ou do sistema todo (sem unidade)."""
    unidade, linhas = params.get("unidade"), params.get("linhas", 50)
    prioridade, desde = params.get("prioridade"), params.get("desde")
    argv = ["journalctl", "--no-pager", "-o", "short-iso"]
    if unidade is not None:
        if not isinstance(unidade, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9@._:\\-]{0,119}", unidade):
            raise Erro(400, "unidade inválida")
        argv += ["-u", unidade]
    if not isinstance(linhas, int) or not 1 <= linhas <= 200:
        raise Erro(400, "linhas deve ser um número de 1 a 200")
    argv += ["-n", str(linhas)]
    if prioridade is not None:
        if prioridade not in PRIORIDADES:
            raise Erro(400, "prioridade deve ser uma de: " + ", ".join(sorted(PRIORIDADES)))
        argv += ["-p", prioridade]
    if desde is not None:
        if not isinstance(desde, str) or not re.fullmatch(r"\d{1,3}(min|h|d)", desde):
            raise Erro(400, 'desde deve ser como "30min", "6h" ou "2d"')
        argv.append("--since=-" + desde)
    _, texto = rodar(argv)
    return ocultar(texto)


def acao_servico_logs(cliente, params):
    nomes = stack_permitida(cliente, params.get("stack"))
    linhas = params.get("linhas", 100)
    if not isinstance(linhas, int) or not 1 <= linhas <= 500:
        raise Erro(400, "linhas deve ser um número de 1 a 500")
    saida = {}
    for nome in nomes:
        _, texto = rodar(["docker", "logs", "--tail", str(linhas), nome])
        saida[nome] = texto
    return saida


def acao_sistema_processos(cliente, params):
    """Processos do servidor que mais usam CPU (ou RAM)."""
    ordem, quantos = params.get("ordem", "cpu"), params.get("quantos", 25)
    if ordem not in ("cpu", "ram"):
        raise Erro(400, 'ordem deve ser "cpu" ou "ram"')
    if not isinstance(quantos, int) or not 1 <= quantos <= 100:
        raise Erro(400, "quantos deve ser um número de 1 a 100")
    r = subprocess.run(["ps", "-ww", "-eo", "pid,user:14,pcpu,pmem,rss,etime,args",
                        "--sort", "-pcpu" if ordem == "cpu" else "-rss"],
                       capture_output=True, text=True, timeout=30)
    return ocultar("\n".join(linha[:250] for linha in r.stdout.splitlines()[:quantos + 1]))


def acao_sistema_rede(cliente, params):
    """Endereços e portas abertas do servidor."""
    _, enderecos = rodar(["ip", "-br", "addr"])
    _, portas = rodar(["ss", "-H", "-tuln"])
    return {"enderecos": enderecos, "portas": portas}


def acao_gasto_api(cliente, params):
    """Gasto de API do mês (LiteLLM), por modelo e por chave, com os tetos."""
    def consulta(sql):
        codigo, saida = rodar(["docker", "exec", "litellm-db", "sh", "-c",
                               'psql -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}" -tA -F "|" -c "$1"',
                               "sh", sql])
        if codigo != 0:
            raise Erro(500, "não consegui ler o banco do LiteLLM")
        return [linha.split("|") for linha in saida.splitlines() if "|" in linha]
    codigo, config = rodar(["docker", "exec", "litellm", "cat", "/app/config.yaml"])   # a pasta da stack é fechada
    if codigo != 0:
        raise Erro(500, "não consegui ler o config do LiteLLM")
    tetos = {m["model_name"]: m.get("litellm_params", {}).get("max_budget")
             for m in yaml.safe_load(config).get("model_list", [])}
    modelos = consulta('SELECT model_group, round(sum(spend)::numeric, 4), count(*) FROM "LiteLLM_SpendLogs" '
                       "WHERE \"startTime\" >= date_trunc('month', now()) AND model_group <> '' "
                       "GROUP BY 1 ORDER BY 2 DESC")
    chaves = consulta('SELECT key_alias, round(spend::numeric, 4), max_budget, budget_reset_at '
                      'FROM "LiteLLM_VerificationToken" WHERE key_alias IS NOT NULL ORDER BY 1')
    por_modelo = [{"modelo": m, "gasto_usd": float(g), "chamadas": int(n), "teto_usd": tetos.get(m)}
                  for m, g, n in modelos if m in tetos]
    return {"mes": time.strftime("%Y-%m"),
            "total_usd": round(sum(m["gasto_usd"] for m in por_modelo), 4),
            "por_modelo": por_modelo,
            "por_chave": [{"chave": a, "gasto_usd": float(g), "teto_usd": float(t) if t else None,
                           "renova": r[:10] or None} for a, g, t, r in chaves],
            "obs": "renova todo dia 1º; modelos locais (local, whisper) não custam nada"}


def preparar_servico_reiniciar(cliente, params):
    nomes = stack_permitida(cliente, params.get("stack"))
    return f"reiniciar {params['stack']}", "Containers: " + ", ".join(nomes)


def acao_servico_reiniciar(p):
    # confere de novo: a stack pode ter mudado de zona enquanto o pedido esperava
    nomes = stack_permitida({"zonas": p["zonas"]}, p["params"].get("stack"))
    codigo, texto = rodar(["docker", "restart", *nomes], 120)
    if codigo != 0:
        raise Erro(500, texto.strip() or "falha ao reiniciar")
    return {"reiniciados": nomes}
