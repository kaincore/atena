"""O guarda de escopo do lab interativo (hook PreToolUse do Claude Code) e as duas configurações do lab."""
import json
import os
import subprocess
import sys

from comum import RAIZ, confere, fim

GUARDA = os.path.join(RAIZ, "host", "lab", "guarda_escopo.py")
PROJETO = "/srv/lab/projetos/loja"


def decide(comando, cwd=PROJETO):
    r = subprocess.run([sys.executable, "-I", GUARDA], input=json.dumps({"tool_input": {"command": comando}, "cwd": cwd}),
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return f"erro {r.returncode}"
    if not r.stdout.strip():
        return "segue"
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]


SEGUE = ["ls", "git status", "python3 -m pytest -q", "cat ./README.md", "npm install", "cat app.log > /dev/null",
         "cat <<EOF > notas.txt\nsudo e docker aqui são só texto\nEOF", "rm build/cache.txt", "npm test && git add -A && git commit -m teste"]
PERGUNTA = ["sudo ls", "docker ps", "systemctl restart x", "cat /etc/passwd", "ls ../../../etc", "rm -rf build",
            "echo $(whoami)", "echo `id`", "bash -c 'ls /'", "cd", "cd ~", "ls $HOME", "npm install -g x",
            "pip install --user x", "env FOO=1 apt install x", "timeout 5 kill 1", 'echo "aspas abertas']
for comando in SEGUE:
    confere(f"segue: {comando.splitlines()[0]}", decide(comando) == "segue", decide(comando))
for comando in PERGUNTA:
    confere(f"pergunta: {comando}", decide(comando) == "ask", decide(comando))
confere("sessão fora do lab: pergunta", decide("ls", cwd="/home/dono") == "ask")
confere("entrada ilegível: pergunta", subprocess.run([sys.executable, "-I", GUARDA], input="{", capture_output=True,
                                                     text=True).stdout.count('"ask"') == 1)

# --- as configurações do lab ---
with open(os.path.join(RAIZ, "host", "lab", "lab.json")) as f:
    trabalhador = json.load(f)
s = trabalhador["sandbox"]
confere("trabalhador: sandbox obrigatório e sem saída do sandbox", s["enabled"] and s["failIfUnavailable"]
        and s["allowUnsandboxedCommands"] is False)
confere("trabalhador: sem hooks do projeto", trabalhador.get("disableAllHooks") is True)
nega = s["filesystem"]["denyRead"]
confere("trabalhador: Docker, executor e as outras zonas escondidos", all(p in nega for p in (
    "/run/docker.sock", "/run/atena-executor", "/srv/agents", "/srv/apps", "/srv/prod", "/etc/atena")))
confere("trabalhador: a fila e os registros escondidos", "/var/lib/atena-claude/fila" in nega
        and "/var/lib/atena-claude/registros" in nega)
confere("trabalhador: git push e páginas web pedem o celular", "Bash(git push *)" in trabalhador["permissions"]["ask"]
        and "WebFetch" in trabalhador["permissions"]["ask"])
with open(os.path.join(RAIZ, "host", "lab", "lab-interativo.json")) as f:
    interativo = json.load(f)
confere("interativo: o guarda está ligado", interativo["hooks"]["PreToolUse"][0]["hooks"][0]["command"].endswith("guarda_escopo.py"))
confere("interativo: sandbox ligado, o trabalhador escondido", interativo["sandbox"]["enabled"]
        and "/var/lib/atena-claude" in interativo["sandbox"]["filesystem"]["denyRead"])

fim()
