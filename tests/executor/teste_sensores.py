"""Temperaturas e ventoinhas: sistema.sensores e status.recursos, com um /sys/class/hwmon falso."""
import os
import shutil

from comum import carregar, confere, fim

ex, tmp = carregar()
c = {"cliente": "hermes", "zonas": ["apps"], "acoes": []}
confere("ação registrada, sem aprovação", ex.ACOES["sistema.sensores"][2] is None)


def hwmon(chips):
    """chips: [(nome, {arquivo: valor})] → pasta no formato do /sys/class/hwmon."""
    pasta = f"{tmp}/hwmon-{len(os.listdir(tmp))}"
    for n, (nome, arquivos) in enumerate(chips):
        os.makedirs(f"{pasta}/hwmon{n}")
        for arquivo, valor in {"name": nome, **arquivos}.items():
            with open(f"{pasta}/hwmon{n}/{arquivo}", "w") as f:
                f.write(valor + "\n")
    ex.HWMON = pasta
    return pasta


GPU = {"saida": "41, 30, 7.52, 3\n"}


def rodar_falso(argv, tempo=30):
    if argv[0] == "nvidia-smi":
        if "fan.speed" in argv[1]:
            return 0, GPU["saida"]
        return 0, "NVIDIA GeForce GTX 1060 6GB, 100, 6144, 41, 3\n"
    return 1, "sem docker no teste"


ex.rodar = rodar_falso

# --- AMD: k10temp, NVMe e o chip da placa ---
amd = hwmon([
    ("nvme", {"temp1_input": "28850", "temp1_label": "Composite", "temp1_max": "82850"}),
    ("k10temp", {"temp1_input": "86125", "temp1_label": "Tctl", "temp3_input": "40000", "temp3_label": "Tccd1"}),
    ("nct6687", {"temp1_input": "34000", "temp1_label": "AMD TSI Addr 98h", "temp9_input": "-55000",
                 "fan1_input": "1220", "fan2_input": "0"})])
s = ex.acao_sistema_sensores(c, {})
confere("CPU pelo Tctl do k10temp", s["cpu"]["temperatura_c"] == 86.1, s["cpu"])
confere("núcleos pelo Tccd", s["cpu"]["nucleos_c"] == {"Tccd1": 40.0}, s["cpu"])
confere("NVMe com o alerta do próprio disco", s["nvme"] == {"temperatura_c": 28.9, "alerta_c": 82.85}, s["nvme"])
confere("GPU pelo nvidia-smi", s["gpu"]["temperatura_c"] == 41.0 and s["gpu"]["consumo_w"] == 7.52, s["gpu"])
confere("placa: só a ventoinha girando aparece", s["placa"]["ventoinhas_rpm"] == {"fan1": 1220}, s["placa"])
confere("placa: leitura impossível (-55 °C) fica de fora", list(s["placa"]["temperaturas_c"]) == ["AMD TSI Addr 98h"], s["placa"])
confere("avaliação aponta a CPU quente", s["avaliacao"].startswith("quente") and "CPU" in s["avaliacao"], s["avaliacao"])
r = ex.acao_status_recursos(c, {})
confere("status.recursos traz as temperaturas", r["temperaturas"] == {"cpu_c": 86.1, "nvme_c": 28.9}, r.get("temperaturas"))
GPU["saida"] = "41, [N/A], [N/A], 3\n"
s = ex.acao_sistema_sensores(c, {})
confere("GPU sem ventoinha nem consumo ([N/A]) vira None", s["gpu"]["ventoinha_pct"] is None and s["gpu"]["consumo_w"] is None, s["gpu"])
with open(f"{amd}/hwmon1/temp1_input", "w") as f:
    f.write("45000\n")
shutil.rmtree(f"{amd}/hwmon2")
s = ex.acao_sistema_sensores(c, {})
confere("sem o chip da placa: explica o módulo e segue", "ATENA_SENSORES_MODULO" in s["placa"]["obs"] and s["avaliacao"] == "normal", s)

# --- Intel: coretemp e chip it87 ---
hwmon([
    ("acpitz", {"temp1_input": "27800"}),
    ("coretemp", {"temp1_input": "52000", "temp1_label": "Package id 0", "temp2_input": "49000", "temp2_label": "Core 0",
                  "temp3_input": "51000", "temp3_label": "Core 1"}),
    ("it8686", {"temp1_input": "33000", "fan1_input": "900"})])
s = ex.acao_sistema_sensores(c, {})
confere("Intel: CPU pelo Package id 0 do coretemp", s["cpu"]["temperatura_c"] == 52.0, s["cpu"])
confere("Intel: núcleos pelo Core N", s["cpu"]["nucleos_c"] == {"Core 0": 49.0, "Core 1": 51.0}, s["cpu"])
confere("Intel: chip it87 vale como placa", s["placa"]["ventoinhas_rpm"] == {"fan1": 900}, s["placa"])
confere("sem NVMe: temperatura None, sem quebrar", s["nvme"]["temperatura_c"] is None and s["avaliacao"] == "normal", s)

# --- máquina sem sensores (VM) e sem GPU ---
hwmon([])
ex.rodar = lambda argv, tempo=30: (_ for _ in ()).throw(FileNotFoundError(argv[0]))
s = ex.acao_sistema_sensores(c, {})
confere("VM sem sensores nem GPU: tudo None, avaliação normal",
        s["cpu"]["temperatura_c"] is None and s["gpu"] is None and s["avaliacao"] == "normal", s)
r = ex.acao_status_recursos(c, {})
confere("status.recursos numa VM: temperaturas None", r["temperaturas"] == {"cpu_c": None, "nvme_c": None}, r["temperaturas"])

fim()
