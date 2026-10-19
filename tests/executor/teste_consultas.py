"""Consultas do executor: uso dos containers, systemd e gasto de API (comandos simulados)."""
import json

from comum import carregar, confere, erro, fim

ex, tmp = carregar()
DOCKER_PS = "\n".join("\t".join(c) for c in [
    ("arca", "/opt/atena/stacks/apps/arca", "arca", "running", "Up", "zone-apps"),
    ("cliente1", "/opt/atena/stacks/prod/cliente1", "cliente1", "running", "Up", "zone-prod"),
])
CONFIG_LITELLM = """
model_list:
  - model_name: haiku
    litellm_params: {model: anthropic/claude-haiku, max_budget: 5}
  - model_name: local
    litellm_params: {model: ollama/qwen3}
"""
RESPOSTAS = {}


def rodar_falso(argv, tempo=30):
    if argv[:2] == ["docker", "ps"]:
        return 0, DOCKER_PS
    if argv[:2] == ["docker", "stats"]:
        return 0, "arca\t1.5%\t120MiB / 1GiB\t11.7%\ncliente1\t3%\t300MiB / 2GiB\t15%\n"
    if argv[:2] == ["systemctl", "list-units"] and "--state=failed" in argv:
        return 0, json.dumps([{"unit": "algo.service"}])
    if argv[:2] == ["systemctl", "list-units"]:
        return 0, json.dumps([{"unit": "atena-executor.service", "active": "active", "sub": "running"},
                              {"unit": "atena-apps.slice", "active": "active", "sub": "active"}])
    if argv[:2] == ["systemctl", "list-timers"]:
        return 0, json.dumps([{"unit": "atena-vigia.timer", "next": 1_790_000_000_000_000, "last": None}])
    if argv[:3] == ["docker", "exec", "litellm"]:
        return RESPOSTAS.get("config", (0, CONFIG_LITELLM))
    if argv[:3] == ["docker", "exec", "litellm-db"]:
        sql = argv[-1]
        if "SpendLogs" in sql:
            return 0, "haiku|1.2345|40\nlocal|0|12\nmodelo-apagado|9|1\n"
        return 0, "hermes|1.2345|10|2026-11-01 00:00:00\nopen-webui|0||\n"
    return 1, "inesperado"


ex.rodar = rodar_falso
c = {"cliente": "hermes", "zonas": ["apps", "ai"], "acoes": []}

r = ex.acao_status_containers(c, {})
confere("status.containers só mostra as zonas do cliente", [x["container"] for x in r] == ["arca"], r)
confere("status.containers separa a RAM usada do limite", r[0]["ram"] == "120MiB" and r[0]["cpu"] == "1.5%", r)

r = ex.acao_status_sistema(c, {})
confere("status.sistema lista as unidades atena-* sem as slices",
        [u["nome"] for u in r["unidades"]] == ["atena-executor.service"], r)
confere("status.sistema mostra timers com a próxima data legível", r["timers"][0]["proxima"].startswith("20"), r)
confere("status.sistema mostra as falhas do sistema todo", r["falhas"] == ["algo.service"], r)

r = ex.acao_gasto_api(c, {})
confere("gasto.api soma o mês só dos modelos que existem no config", r["total_usd"] == 1.2345, r)
confere("gasto.api traz o teto de cada modelo", {m["modelo"]: m["teto_usd"] for m in r["por_modelo"]} == {"haiku": 5, "local": None}, r)
confere("gasto.api por chave, com teto e data de renovação",
        r["por_chave"][0] == {"chave": "hermes", "gasto_usd": 1.2345, "teto_usd": 10.0, "renova": "2026-11-01"}
        and r["por_chave"][1]["teto_usd"] is None, r)
RESPOSTAS["config"] = (1, "Error: No such container: litellm")
confere("LiteLLM fora do ar: 500 com motivo", erro(ex.acao_gasto_api, c, {})[0] == 500)

fim()
